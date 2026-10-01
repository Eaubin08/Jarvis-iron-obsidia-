from __future__ import annotations

from typing import Any


ADMISSIBLE = "ADMISSIBLE"
INSUFFICIENT = "INSUFFICIENT_PROVENANCE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"

_GOVERNANCE = {
    "readonly": True,
    "shadow_only": True,
    "advisory_only": True,
    "emits_act": False,
    "memory_write": False,
    "kernel_mutation": False,
    "x108_mutation": False,
    "decision_authority": "KX108_ONLY",
    "selects_runtime_path": False,
    "modifies_p36_selection": False,
    "authorizes_capability": False,
}


def build_capability_admissibility_shadow(
    *,
    structured_capability_snapshot: Any,
    p36_snapshot: Any,
    comparator_snapshot: Any,
    unified_ir_snapshot: Any | None = None,
    semantic_snapshot: Any | None = None,
    memzum_snapshot: Any | None = None,
) -> dict[str, Any]:
    """Classify detected capability candidates by provenance, in shadow only.

    The function consumes only existing snapshots. It does not accept raw text,
    call P36, retrieve memory, inspect a corpus, hydrate source material, select
    a runtime path or authorize any capability.
    """

    structured = _as_dict(structured_capability_snapshot)
    p36 = _as_dict(p36_snapshot)
    comparator = _as_dict(comparator_snapshot)
    ir = _as_dict(unified_ir_snapshot)
    semantic = _as_dict(semantic_snapshot)
    memzum = _as_dict(memzum_snapshot)

    structured_caps = _normalize_strings(
        comparator.get("structured_capabilities")
        or structured.get("structured_capability_hints")
    )
    legacy_caps = _normalize_strings(
        comparator.get("legacy_capabilities")
        or p36.get("required_capabilities")
    )
    candidate_caps = _normalize_strings(
        comparator.get("union_capabilities")
    ) or _append_unique(legacy_caps, structured_caps)

    shared = set(_normalize_strings(comparator.get("shared")))
    legacy_only = set(_normalize_strings(comparator.get("legacy_only")))
    structured_only = set(_normalize_strings(comparator.get("structured_only")))
    signals = _as_dict(structured.get("signals_used"))
    detected_intents = set(_normalize_strings(p36.get("detected_intents")))
    selected_path = _as_dict(p36.get("selected_runtime_path"))
    selected_chain = set(_normalize_strings(selected_path.get("capability_chain")))

    candidates = [
        _candidate(
            capability=capability,
            shared=capability in shared,
            structured_only=capability in structured_only,
            legacy_only=capability in legacy_only,
            signals=signals,
            ir=ir,
            semantic=semantic,
            memzum=memzum,
            detected_intents=detected_intents,
            selected_chain=selected_chain,
        )
        for capability in candidate_caps
    ]

    return {
        "status": "CAPABILITY_ADMISSIBILITY_SHADOW_READY",
        "admissibility_version": "V0",
        "candidates": candidates,
        "admissible_capabilities": [
            c["capability"] for c in candidates if c["admissibility"] == ADMISSIBLE
        ],
        "review_required_capabilities": [
            c["capability"] for c in candidates if c["admissibility"] == REVIEW_REQUIRED
        ],
        "insufficient_provenance_capabilities": [
            c["capability"] for c in candidates if c["admissibility"] == INSUFFICIENT
        ],
        "contract": {
            "detection_not_admissibility": True,
            "admissibility_not_selection": True,
            "selection_not_authorization": True,
        },
        "governance": dict(_GOVERNANCE),
    }


def _candidate(
    *,
    capability: str,
    shared: bool,
    structured_only: bool,
    legacy_only: bool,
    signals: dict[str, Any],
    ir: dict[str, Any],
    semantic: dict[str, Any],
    memzum: dict[str, Any],
    detected_intents: set[str],
    selected_chain: set[str],
) -> dict[str, Any]:
    detected_by = []
    if shared or structured_only:
        detected_by.append("STRUCTURED")
    if shared or legacy_only:
        detected_by.append("P36_LEGACY")

    if shared:
        return _record(
            capability,
            detected_by,
            ["SHARED_STRUCTURED_P36"],
            ADMISSIBLE,
            "SHARED_STRUCTURED_P36",
        )

    if structured_only:
        provenance = _structured_provenance(capability, signals, ir, semantic, memzum)
        if provenance:
            return _record(
                capability,
                detected_by,
                provenance,
                ADMISSIBLE,
                "+".join(provenance),
            )
        return _record(
            capability,
            detected_by,
            [],
            INSUFFICIENT,
            "STRUCTURED_SIGNAL_WITHOUT_MATCHING_PROVENANCE",
        )

    if legacy_only:
        provenance = _p36_provenance(capability, detected_intents, selected_chain)
        if provenance == "P36_SPECIALIST":
            return _record(
                capability,
                detected_by,
                [provenance],
                ADMISSIBLE,
                _p36_reason(capability),
            )
        if provenance == "P36_BUNDLED_REVIEW":
            return _record(
                capability,
                detected_by,
                ["P36_SPECIALIST"],
                REVIEW_REQUIRED,
                "P36_BUNDLED_CAPABILITY_REQUIRES_INDIVIDUAL_PROVENANCE",
            )
        return _record(
            capability,
            detected_by,
            [],
            INSUFFICIENT,
            "P36_LEGACY_SIGNAL_WITHOUT_SPECIALIST_PROVENANCE",
        )

    return _record(
        capability,
        detected_by,
        [],
        INSUFFICIENT,
        "CAPABILITY_NOT_IN_COMPARATOR_PARTITIONS",
    )


def _structured_provenance(
    capability: str,
    signals: dict[str, Any],
    ir: dict[str, Any],
    semantic: dict[str, Any],
    memzum: dict[str, Any],
) -> list[str]:
    intent_type = str(signals.get("intent_type") or ir.get("intent_type") or "").strip()
    target_layer = str(signals.get("target_layer") or ir.get("target_layer") or "").strip()
    semantic_topic = str(
        signals.get("semantic_topic") or semantic.get("topic") or ""
    ).strip()
    memory_required = bool(
        signals.get("memory_required") is True
        or memzum.get("memory_required") is True
        or _as_dict(ir.get("needs")).get("memory") is True
    )

    if capability == "BRODY_CHAT_ENTRYPOINT" and semantic_topic == "OBSIDIA_BRODY_ROLE":
        return ["SEMANTIC_TOPIC"]
    if capability == "MEMORY_REINTEGRATION_CONTEXT":
        provenance = []
        if target_layer == "memory" or intent_type == "memory_query":
            provenance.append("STRUCTURED_IR")
        if memory_required:
            provenance.append("MEMZUM")
        return provenance
    if capability == "PROOF_AUDIT_CONTEXT" and (
        target_layer == "proof"
        or intent_type in {"audit", "proof_query"}
        or semantic_topic == "PROOF_QUERY"
    ):
        provenance = ["STRUCTURED_IR"]
        if semantic_topic == "PROOF_QUERY":
            provenance.append("SEMANTIC_TOPIC")
        return provenance
    if capability in {"IR_ALPHABET_MAPPING", "REVERSE_OS_INTERLANGUAGE", "OS_TRAD_TRANSLATION"}:
        if target_layer == "terminal":
            return ["STRUCTURED_IR"]
    if capability == "ACTION_REQUEST_BLOCKED" and (
        intent_type in {"world_action", "action_request", "act_request"}
        or target_layer == "world"
    ):
        return ["STRUCTURED_IR"]
    if capability == "SOURCE_CONTEXT" and semantic_topic in {"OBSIDIA_PROJECT", "CURRENT_STATE"}:
        return ["SEMANTIC_TOPIC"]
    return []


def _p36_provenance(
    capability: str,
    detected_intents: set[str],
    selected_chain: set[str],
) -> str | None:
    if capability == "AGENT_TREE_LOOKUP":
        if "OS_TRAD" in detected_intents and "AGENT_TREE" not in detected_intents:
            return "P36_BUNDLED_REVIEW"
        if "AGENT_TREE" in detected_intents or capability in selected_chain:
            return "P36_SPECIALIST"
    if capability == "OS_TRAD_TRANSLATION":
        if "OS_TRAD" in detected_intents:
            return "P36_SPECIALIST"
        if "AGENT_TREE" in detected_intents:
            return "P36_BUNDLED_REVIEW"
    return None


def _p36_reason(capability: str) -> str:
    if capability == "AGENT_TREE_LOOKUP":
        return "P36_SPECIALIST_AGENT_TREE_ROUTE"
    if capability == "OS_TRAD_TRANSLATION":
        return "P36_SPECIALIST_OS_TRAD_ROUTE"
    return "P36_SPECIALIST"


def _record(
    capability: str,
    detected_by: list[str],
    provenance: list[str],
    admissibility: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "capability": capability,
        "detected_by": detected_by,
        "provenance": provenance,
        "admissibility": admissibility,
        "reason": reason,
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _append_unique(*groups: list[str]) -> list[str]:
    out: list[str] = []
    for group in groups:
        for item in group:
            if item not in out:
                out.append(item)
    return out


__all__ = ["build_capability_admissibility_shadow"]
