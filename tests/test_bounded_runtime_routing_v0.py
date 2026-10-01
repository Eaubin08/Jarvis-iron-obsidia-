import sys
from pathlib import Path

import pytest

from jarvis.obsidia_port.bounded_runtime_routing_v0 import (
    resolve_bounded_runtime_override,
)


RUNTIME_ROOT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "jarvis"
    / "obsidia_port"
    / "brody_runtime"
)
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from runtime_wiring.source_runtime.brody_source_context_bridge import (  # noqa: E402
    build_brody_context_from_source_packs,
)


def _selection(capability):
    return {
        "status": "SELECTED_SHADOW",
        "selected_capability": capability,
    }


@pytest.mark.parametrize(
    "capability",
    [
        "BRODY_CHAT_ENTRYPOINT",
        "MEMORY_REINTEGRATION_CONTEXT",
        "PROOF_AUDIT_CONTEXT",
        "IR_ALPHABET_MAPPING",
    ],
)
def test_bounded_runtime_override_allowlist(monkeypatch, capability):
    monkeypatch.setenv("JARJAR_BOUNDED_STRUCTURED_ROUTING_V0", "1")
    result = resolve_bounded_runtime_override(
        capability_selection_snapshot=_selection(capability),
    )
    assert result["status"] == "BOUNDED_RUNTIME_OVERRIDE_READY"
    assert result["applied"] is True
    assert result["runtime_path"]["capability_chain"] == [capability]
    assert result["runtime_path"]["decision_authority"] == "KX108_ONLY"
    assert result["runtime_path"]["emits_act"] is False
    assert result["runtime_path"]["runtime_allowed_now"] is False


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("JARJAR_BOUNDED_STRUCTURED_ROUTING_V0", raising=False)
    result = resolve_bounded_runtime_override(
        capability_selection_snapshot=_selection("IR_ALPHABET_MAPPING"),
    )
    assert result["status"] == "DISABLED"
    assert result["applied"] is False
    assert result["fallback_to_legacy_p36"] is True


@pytest.mark.parametrize(
    "capability",
    [
        "OS_TRAD_TRANSLATION",
        "AGENT_TREE_LOOKUP",
        "ACTION_REQUEST_BLOCKED",
        "SOURCE_CONTEXT",
    ],
)
def test_outside_allowlist_fails_closed(monkeypatch, capability):
    monkeypatch.setenv("JARJAR_BOUNDED_STRUCTURED_ROUTING_V0", "1")
    result = resolve_bounded_runtime_override(
        capability_selection_snapshot=_selection(capability),
    )
    assert result["status"] == "CAPABILITY_OUTSIDE_BOUNDED_ALLOWLIST"
    assert result["applied"] is False
    assert result["fallback_to_legacy_p36"] is True


def test_no_selection_falls_back(monkeypatch):
    monkeypatch.setenv("JARJAR_BOUNDED_STRUCTURED_ROUTING_V0", "1")
    result = resolve_bounded_runtime_override(
        capability_selection_snapshot={
            "status": "NO_ADMISSIBLE_CAPABILITY",
            "selected_capability": None,
        },
    )
    assert result["status"] == "NO_ADMISSIBLE_SELECTION"
    assert result["applied"] is False


def test_bridge_accepts_only_guarded_preselected_context_path():
    legacy = build_brody_context_from_source_packs(
        query="Structure ma demande en IR.",
        limit=5,
    )
    override = resolve_bounded_runtime_override(
        capability_selection_snapshot=_selection("IR_ALPHABET_MAPPING"),
    )
    # Resolver is disabled unless explicitly opted in, so build the guarded
    # template in an isolated env-independent way through a temporary opt-in.
    import os
    old = os.environ.get("JARJAR_BOUNDED_STRUCTURED_ROUTING_V0")
    os.environ["JARJAR_BOUNDED_STRUCTURED_ROUTING_V0"] = "1"
    try:
        override = resolve_bounded_runtime_override(
            capability_selection_snapshot=_selection("IR_ALPHABET_MAPPING"),
            available_families=legacy.get("available_families"),
        )
    finally:
        if old is None:
            os.environ.pop("JARJAR_BOUNDED_STRUCTURED_ROUTING_V0", None)
        else:
            os.environ["JARJAR_BOUNDED_STRUCTURED_ROUTING_V0"] = old

    routed = build_brody_context_from_source_packs(
        query="Structure ma demande en IR.",
        limit=5,
        preselected_runtime_path=override["runtime_path"],
    )
    assert routed["preselected_runtime_path_applied"] is True
    assert routed["selected_runtime_path"]["capability_chain"] == [
        "IR_ALPHABET_MAPPING"
    ]
    assert routed["x108_decision"] == "ALLOW_CONTEXT_ONLY"
    assert routed["boundary"]["decision_authority"] == "KX108_ONLY"


def test_bridge_rejects_unsafe_preselected_path():
    routed = build_brody_context_from_source_packs(
        query="Explique-moi Obsidia.",
        limit=5,
        preselected_runtime_path={
            "capability_chain": ["IR_ALPHABET_MAPPING"],
            "source_families": ["OS_TRAD_REVERSE_OS"],
            "decision_authority": "OTHER",
            "emits_act": True,
            "runtime_allowed_now": True,
            "x108_decision": "ACT",
        },
    )
    assert routed.get("preselected_runtime_path_applied") is False
