import sys
from pathlib import Path

from jarvis.obsidia_port.router_core.unified_ir import build_ir
from jarvis.obsidia_port.structured_capability_hint import (
    build_structured_capability_hint,
    compare_structured_hint_with_p36,
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

from apps.obsidia_api.brody_semantic_query_router import (  # noqa: E402
    build_semantic_query,
)
from runtime_wiring.source_runtime.brody_source_context_bridge import (  # noqa: E402
    build_brody_context_from_source_packs,
)
from jarvis.obsidia_port.local_brody_runtime_adapter import (  # noqa: E402
    LocalBrodyRuntimeAdapter,
)


def _hint(
    text,
    *,
    semantic=None,
    memzum=None,
):
    return build_structured_capability_hint(
        ir=build_ir(text),
        semantic=semantic or build_semantic_query(text),
        memzum=memzum or {},
    )


def test_jarjar_role_maps_to_brody_chat_entrypoint():
    hint = _hint(
        "Quel est ton rôle en tant que Jarjar ?",
        semantic={
            "topic": "OBSIDIA_BRODY_ROLE",
            "is_canonical": True,
            "primary_query": "brody",
        },
    )

    assert hint["structured_capability_hints"] == ["BRODY_CHAT_ENTRYPOINT"]
    assert hint["primary_capability_hint"] == "BRODY_CHAT_ENTRYPOINT"
    assert hint["decision_authority"] == "KX108_ONLY"
    assert hint["readonly"] is True
    assert hint["emits_act"] is False


def test_explicit_memory_maps_to_memory_reintegration_context():
    hint = _hint(
        "Que sais-tu en mémoire sur Obsidia ?",
        memzum={"memory_required": True},
    )

    assert "MEMORY_REINTEGRATION_CONTEXT" in hint[
        "structured_capability_hints"
    ]
    assert hint["signals_used"]["memory_required"] is True


def test_proof_maps_to_proof_audit_context():
    hint = _hint("Quelles preuves Lean avons-nous ?")

    assert "PROOF_AUDIT_CONTEXT" in hint["structured_capability_hints"]
    assert hint["primary_capability_hint"] == "PROOF_AUDIT_CONTEXT"


def test_action_request_predicts_blocked_capability_without_acting():
    hint = _hint("Push ce commit")

    assert hint["structured_capability_hints"] == ["ACTION_REQUEST_BLOCKED"]
    assert hint["signals_used"]["intent_type"] == "world_action"
    assert hint["signals_used"]["action_type"] == "act_request"
    assert hint["emits_act"] is False
    assert hint["advisory_only"] is True


def test_ordinary_world_query_does_not_force_project_capability():
    hint = _hint("Capitale du Japon.")

    assert "MEMORY_REINTEGRATION_CONTEXT" not in hint[
        "structured_capability_hints"
    ]
    assert "AGENT_TREE_LOOKUP" not in hint["structured_capability_hints"]
    assert "OS_TRAD_TRANSLATION" not in hint["structured_capability_hints"]


def test_obsidia_sizes_does_not_infer_agent_tree_lookup():
    hint = _hint(
        "Tu peux me dire quoi sur Obsidia ? Des tailles ?",
        memzum={"memory_required": True},
    )

    assert "AGENT_TREE_LOOKUP" not in hint["structured_capability_hints"]


def test_shadow_comparison_reports_agreement_or_divergence_stably():
    hint = _hint(
        "Que sais-tu en mémoire sur Obsidia ?",
        memzum={"memory_required": True},
    )
    source_pack = build_brody_context_from_source_packs(
        query="Que sais-tu en mémoire sur Obsidia ?",
        limit=5,
    )

    comparison = compare_structured_hint_with_p36(
        structured_capability_hints=hint["structured_capability_hints"],
        p36_required_capabilities=source_pack.get("required_capabilities"),
    )

    assert comparison["capability_route_agreement"] in {
        "AGREE",
        "DIVERGE",
        "INSUFFICIENT_P36_SIGNAL",
    }
    assert comparison["decision_authority"] == "KX108_ONLY"


def test_structured_hint_does_not_change_p36_selected_path():
    query = "Que sais-tu en mémoire sur Obsidia ?"
    source_pack_before = build_brody_context_from_source_packs(
        query=query,
        limit=5,
    )

    result = LocalBrodyRuntimeAdapter().respond(
        query,
        session_id="structured-capability-noninterference",
        language="fr",
    )

    assert result["status"] == "LOCAL_BRODY_RUNTIME_PASS"
    assert result["selected_runtime_path"] == source_pack_before.get(
        "selected_runtime_path"
    )
    assert result["selected_source_families"] == source_pack_before.get(
        "selected_source_families"
    )
    assert result["hydration_plan"] == source_pack_before.get(
        "hydration_plan"
    )
    assert result["structured_capability_hints"]
