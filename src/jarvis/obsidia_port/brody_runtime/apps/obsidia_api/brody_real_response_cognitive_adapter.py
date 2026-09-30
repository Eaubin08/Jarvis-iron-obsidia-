from __future__ import annotations

from typing import Any

from periphery.brody.brody_response_contract import BRODY_CONTRACT
from periphery.brody.brody_runtime_readonly import BrodyResponse


_PFX = "REAL_BRODY_COGNITIVE_ADAPTER"

_REQUIRED_FALSE = (
    "allowed_to_decide",
    "allowed_to_act",
    "emits_act",
    "emits_verdict",
    "memory_write",
    "kernel_mutation",
    "x108_mutation",
    "real_action",
)


def _require_false(runtime: dict[str, Any], key: str) -> None:
    if runtime.get(key) is not False:
        raise AssertionError(
            f"{_PFX}:{key.upper()}_MUST_BE_FALSE:"
            f"{runtime.get(key)!r}"
        )


def _context_refs(runtime: dict[str, Any]) -> list[str]:
    refs: list[str] = []

    action_id = str(runtime.get("action_id") or "").strip()
    source = str(runtime.get("source") or "").strip()

    if action_id:
        refs.append(f"brody-runtime:{action_id}")

    if source:
        refs.append(f"brody-source:{source}")

    packet = runtime.get("context_packet")
    if isinstance(packet, dict):
        packet_id = str(packet.get("packet_id") or "").strip()
        if packet_id:
            refs.append(packet_id)

    items = runtime.get("selected_items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            ref = str(
                item.get("source_ref")
                or item.get("id")
                or ""
            ).strip()
            if ref and ref not in refs:
                refs.append(ref)

    return refs


def adapt_real_brody_runtime_to_response(
    runtime: dict[str, Any],
    *,
    query: str,
    language: str,
) -> BrodyResponse:
    """
    Adapt the already-executed real Brody runtime dict to the
    canonical readonly BrodyResponse consumed by W3.

    Does NOT call Brody again.
    Does NOT synthesize a response.
    Does NOT give Brody decision/action authority.
    """

    if not isinstance(runtime, dict):
        raise TypeError(
            f"{_PFX}:DICT_REQUIRED:"
            f"{type(runtime).__name__}"
        )

    if runtime.get("readonly") is not True:
        raise AssertionError(f"{_PFX}:READONLY_REQUIRED")

    if runtime.get("decision_authority") != "KX108_ONLY":
        raise AssertionError(
            f"{_PFX}:DECISION_AUTHORITY_VIOLATION:"
            f"{runtime.get('decision_authority')!r}"
        )

    for key in _REQUIRED_FALSE:
        _require_false(runtime, key)

    action_id = str(runtime.get("action_id") or "").strip()
    if not action_id:
        raise ValueError(f"{_PFX}:ACTION_ID_REQUIRED")

    runtime_language = str(
        runtime.get("language") or language
    ).strip()

    if runtime_language != language:
        raise ValueError(
            f"{_PFX}:LANGUAGE_MISMATCH:"
            f"{runtime_language!r}!={language!r}"
        )

    response_text = str(
        runtime.get("response_md")
        or runtime.get("response")
        or ""
    ).strip()

    if not response_text:
        raise ValueError(f"{_PFX}:RESPONSE_TEXT_REQUIRED")

    source = str(runtime.get("source") or "").strip()
    if not source:
        raise ValueError(f"{_PFX}:SOURCE_REQUIRED")

    timestamp = str(runtime.get("timestamp") or "").strip()
    if not timestamp:
        raise ValueError(f"{_PFX}:TIMESTAMP_REQUIRED")

    # Real pipeline currently exposes no confidence measurement.
    # BrodyResponse requires a float; 0.0 is therefore an explicit
    # NOT_AVAILABLE sentinel, never an inferred confidence score.
    raw_confidence = runtime.get("confidence")
    if isinstance(raw_confidence, (int, float)):
        confidence = max(0.0, min(1.0, float(raw_confidence)))
        confidence_status = "RUNTIME_PROVIDED"
    else:
        confidence = 0.0
        confidence_status = "NOT_AVAILABLE_SENTINEL_0_0"

    BRODY_CONTRACT.validate()

    contract = dict(BRODY_CONTRACT.to_dict())
    contract["runtime_adapter"] = {
        "adapter": "REAL_BRODY_COGNITIVE_ADAPTER_V1",
        "runtime_source": source,
        "runtime_action_id": action_id,
        "confidence_status": confidence_status,
        "readonly": True,
        "decision_authority": "KX108_ONLY",
        "emits_act": False,
        "memory_write": False,
    }

    return BrodyResponse(
        response_id=action_id,
        query=query[:500],
        language=language,
        response_text=response_text,
        confidence=confidence,
        context_refs=_context_refs(runtime),
        contract=contract,
        timestamp=timestamp,
        readonly=True,
        emits_act=False,
        memory_write=False,
    )


__all__ = [
    "adapt_real_brody_runtime_to_response",
]
