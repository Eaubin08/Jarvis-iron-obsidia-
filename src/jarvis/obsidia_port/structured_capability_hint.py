from __future__ import annotations

from typing import Any


_ACTION_INTENTS = {
    "world_action",
    "action_request",
    "act_request",
}

_ACTION_TYPES = {
    "act_request",
    "commands",
}

_TOPIC_CAPABILITIES = {
    "OBSIDIA_BRODY_ROLE": ("BRODY_CHAT_ENTRYPOINT", "HIGH"),
    "MEMORY_QUERY": ("MEMORY_REINTEGRATION_CONTEXT", "HIGH"),
    "PROOF_QUERY": ("PROOF_AUDIT_CONTEXT", "HIGH"),
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_bool(value: Any) -> bool:
    return bool(value is True or str(value).lower() == "true")


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _primary_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def build_structured_capability_hint(
    *,
    ir: dict,
    semantic: dict,
    memzum: dict | None = None,
) -> dict[str, Any]:
    """Build a Jarjar-owned shadow capability hint from structured inputs.

    This function intentionally does not accept raw user text. It observes
    already-produced IR, semantic topic and MEMZUM state, then emits an
    advisory capability prediction in the existing P36 vocabulary.
    """

    ir = _as_dict(ir)
    semantic = _as_dict(semantic)
    memzum = _as_dict(memzum)

    intent_type = str(ir.get("intent_type") or "").strip()
    target_layer = str(ir.get("target_layer") or "").strip()
    action_type = str(ir.get("action_type") or "").strip()
    risk_level = str(ir.get("risk_level") or "").strip()
    semantic_topic = str(semantic.get("topic") or "").strip()
    needs = _as_dict(ir.get("needs"))
    missing = ir.get("missing") if isinstance(ir.get("missing"), list) else []
    memory_required = _as_bool(memzum.get("memory_required")) or _as_bool(
        needs.get("memory")
    )

    hints: list[str] = []
    confidence = "NONE"

    def add(capability: str, level: str) -> None:
        nonlocal confidence
        _append_unique(hints, capability)
        confidence = _max_confidence(confidence, level)

    if (
        intent_type in _ACTION_INTENTS
        or action_type in _ACTION_TYPES
        or target_layer == "world"
        or risk_level == "high"
    ):
        add("ACTION_REQUEST_BLOCKED", "HIGH")

    topic_capability = _TOPIC_CAPABILITIES.get(semantic_topic)
    if topic_capability:
        add(*topic_capability)

    if target_layer == "memory" or intent_type == "memory_query":
        add("MEMORY_REINTEGRATION_CONTEXT", "HIGH")
    elif memory_required:
        add("MEMORY_REINTEGRATION_CONTEXT", "MEDIUM")

    if target_layer == "proof":
        add("PROOF_AUDIT_CONTEXT", "HIGH")
    elif intent_type in {"audit", "proof_query"}:
        add("PROOF_AUDIT_CONTEXT", "MEDIUM")

    if target_layer == "terminal":
        add("IR_ALPHABET_MAPPING", "MEDIUM")
        add("REVERSE_OS_INTERLANGUAGE", "MEDIUM")
        add("OS_TRAD_TRANSLATION", "LOW")

    if not hints and semantic_topic in {"OBSIDIA_PROJECT", "CURRENT_STATE"}:
        add("SOURCE_CONTEXT", "LOW")

    if not hints and (intent_type or target_layer) and "intent" not in missing:
        add("SOURCE_CONTEXT", "LOW")

    return {
        "status": "STRUCTURED_CAPABILITY_HINT_READY",
        "hint_version": "V0",
        "structured_capability_hints": hints,
        "primary_capability_hint": _primary_or_none(hints),
        "signals_used": {
            "intent_type": intent_type,
            "target_layer": target_layer,
            "action_type": action_type,
            "risk_level": risk_level,
            "semantic_topic": semantic_topic,
            "memory_required": memory_required,
        },
        "confidence_class": confidence if hints else "NONE",
        "readonly": True,
        "advisory_only": True,
        "memory_write": False,
        "emits_act": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "decision_authority": "KX108_ONLY",
    }


def _max_confidence(left: str, right: str) -> str:
    order = {
        "NONE": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
    }
    return right if order.get(right, 0) > order.get(left, 0) else left


def compare_structured_hint_with_p36(
    *,
    structured_capability_hints: Any,
    p36_required_capabilities: Any,
) -> dict[str, Any]:
    hints = _normalize_capabilities(structured_capability_hints)
    p36 = _normalize_capabilities(p36_required_capabilities)
    hint_set = set(hints)
    p36_set = set(p36)
    overlap = [capability for capability in hints if capability in p36_set]

    if not hints:
        agreement = "INSUFFICIENT_STRUCTURED_SIGNAL"
    elif not p36:
        agreement = "INSUFFICIENT_P36_SIGNAL"
    elif overlap:
        agreement = "AGREE"
    else:
        agreement = "DIVERGE"

    return {
        "capability_route_agreement": agreement,
        "capability_route_divergence": {
            "structured_only": [
                capability for capability in hints if capability not in p36_set
            ],
            "p36_only": [
                capability for capability in p36 if capability not in hint_set
            ],
            "overlap": overlap,
        },
        "readonly": True,
        "advisory_only": True,
        "memory_write": False,
        "emits_act": False,
        "kernel_mutation": False,
        "x108_mutation": False,
        "decision_authority": "KX108_ONLY",
    }


def _normalize_capabilities(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    capabilities: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in capabilities:
            capabilities.append(text)
    return capabilities


__all__ = [
    "build_structured_capability_hint",
    "compare_structured_hint_with_p36",
]
