import sys
from pathlib import Path

import pytest

from jarvis.obsidia_port.capability_admissibility import (
    build_capability_admissibility_shadow,
)
from jarvis.obsidia_port.capability_selection_shadow import (
    build_capability_selection_shadow,
)
from jarvis.obsidia_port.router_core.unified_ir import build_ir
from jarvis.obsidia_port.structured_capability_hint import (
    build_structured_capability_hint,
)
from jarvis.obsidia_port.structured_p36_shadow_comparator import (
    build_structured_p36_shadow_comparison,
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


def _semantic_for(query, override=None):
    semantic = build_semantic_query(query)
    if override:
        semantic = {**semantic, **override}
    return semantic


def _snapshots(query, *, semantic_override=None, memzum=None):
    ir = build_ir(query)
    semantic = _semantic_for(query, semantic_override)
    memzum = dict(memzum or {})
    hint = build_structured_capability_hint(
        ir=ir,
        semantic=semantic,
        memzum=memzum,
    )
    source_pack = build_brody_context_from_source_packs(
        query=query,
        limit=5,
    )
    p36 = {
        "detected_intents": source_pack.get("detected_intents"),
        "required_capabilities": source_pack.get("required_capabilities"),
        "selected_runtime_path": source_pack.get("selected_runtime_path"),
        "selected_source_families": source_pack.get(
            "selected_source_families"
        ),
        "hydration_plan": source_pack.get("hydration_plan"),
    }
    comparator = build_structured_p36_shadow_comparison(
        structured_capability_snapshot=hint,
        p36_snapshot=p36,
        unified_ir_snapshot=ir,
        semantic_snapshot=semantic,
        memzum_snapshot=memzum,
    )
    admissibility = build_capability_admissibility_shadow(
        structured_capability_snapshot=hint,
        p36_snapshot=p36,
        comparator_snapshot=comparator,
        unified_ir_snapshot=ir,
        semantic_snapshot=semantic,
        memzum_snapshot=memzum,
    )
    selection = build_capability_selection_shadow(
        capability_admissibility_snapshot=admissibility,
        comparator_snapshot=comparator,
    )
    return hint, source_pack, admissibility, selection


@pytest.mark.parametrize(
    "query, semantic_override, memzum, expected",
    [
        (
            "Quel est ton rôle en tant que Jarjar ?",
            {"topic": "OBSIDIA_BRODY_ROLE"},
            None,
            "BRODY_CHAT_ENTRYPOINT",
        ),
        (
            "Que sais-tu en mémoire sur Obsidia ?",
            None,
            {"memory_required": True},
            "MEMORY_REINTEGRATION_CONTEXT",
        ),
        ("Quelles preuves Lean avons-nous ?", None, None, "PROOF_AUDIT_CONTEXT"),
        ("Structure ma demande en IR.", None, None, "IR_ALPHABET_MAPPING"),
        ("Traduis cette demande avec OS Trad.", None, None, "OS_TRAD_TRANSLATION"),
        ("Que représentent les 34 arbres ?", None, None, "AGENT_TREE_LOOKUP"),
        ("Parle-moi des 52 agents.", None, None, "AGENT_TREE_LOOKUP"),
        ("Explique-moi Obsidia.", None, None, "SOURCE_CONTEXT"),
        ("Push ce commit.", None, None, "ACTION_REQUEST_BLOCKED"),
    ],
)
def test_selection_shadow_representative_cases(query, semantic_override, memzum, expected):
    _, source_pack, _, selection = _snapshots(
        query,
        semantic_override=semantic_override,
        memzum=memzum,
    )

    assert selection["status"] == "SELECTED_SHADOW"
    assert selection["selected_capability"] == expected
    assert expected in selection["eligible_capabilities"]
    assert selection["legacy_p36_selected_path"] == source_pack.get(
        "selected_runtime_path"
    )
    assert selection["legacy_p36_selected_source_families"] == (
        source_pack.get("selected_source_families")
    )


def test_ir_mapping_keeps_alternative_specific_capabilities_visible():
    _, _, _, selection = _snapshots("Structure ma demande en IR.")

    assert selection["selected_capability"] == "IR_ALPHABET_MAPPING"
    assert set(selection["alternative_admissible_capabilities"]) == {
        "REVERSE_OS_INTERLANGUAGE",
        "OS_TRAD_TRANSLATION",
    }


def test_os_trad_excludes_review_required_agent_tree():
    _, _, admissibility, selection = _snapshots("Traduis cette demande avec OS Trad.")

    assert "AGENT_TREE_LOOKUP" in admissibility["review_required_capabilities"]
    assert "AGENT_TREE_LOOKUP" in selection["excluded_review_required"]
    assert "AGENT_TREE_LOOKUP" not in selection["eligible_capabilities"]
    assert selection["selected_capability"] == "OS_TRAD_TRANSLATION"


def test_tree_query_excludes_review_required_os_trad():
    _, _, admissibility, selection = _snapshots("Que représentent les 34 arbres ?")

    assert "OS_TRAD_TRANSLATION" in admissibility["review_required_capabilities"]
    assert "OS_TRAD_TRANSLATION" in selection["excluded_review_required"]
    assert "OS_TRAD_TRANSLATION" not in selection["eligible_capabilities"]
    assert selection["selected_capability"] == "AGENT_TREE_LOOKUP"


def test_proof_x108_gap_cannot_be_repaired_by_selection():
    hint, _, _, selection = _snapshots("Quelles preuves existent pour X108 ?")

    assert "PROOF_AUDIT_CONTEXT" not in hint["structured_capability_hints"]
    assert "PROOF_AUDIT_CONTEXT" not in selection["eligible_capabilities"]
    assert selection["selected_capability"] is None
    assert selection["status"] == "NO_ADMISSIBLE_CAPABILITY"


def test_ordinary_world_query_has_no_selection_from_insufficient_source_context():
    _, _, admissibility, selection = _snapshots("Capitale du Japon.")

    assert admissibility["insufficient_provenance_capabilities"] == [
        "SOURCE_CONTEXT"
    ]
    assert selection["excluded_insufficient_provenance"] == ["SOURCE_CONTEXT"]
    assert selection["eligible_capabilities"] == []
    assert selection["selected_capability"] is None
    assert selection["status"] == "NO_ADMISSIBLE_CAPABILITY"


def test_review_and_insufficient_candidates_are_never_selected_synthetically():
    selection = build_capability_selection_shadow(
        capability_admissibility_snapshot={
            "candidates": [
                {
                    "capability": "BRODY_CHAT_ENTRYPOINT",
                    "admissibility": "REVIEW_REQUIRED",
                },
                {
                    "capability": "MEMORY_REINTEGRATION_CONTEXT",
                    "admissibility": "INSUFFICIENT_PROVENANCE",
                },
            ]
        }
    )

    assert selection["eligible_capabilities"] == []
    assert selection["excluded_review_required"] == ["BRODY_CHAT_ENTRYPOINT"]
    assert selection["excluded_insufficient_provenance"] == [
        "MEMORY_REINTEGRATION_CONTEXT"
    ]
    assert selection["selected_capability"] is None
    assert selection["status"] == "NO_ADMISSIBLE_CAPABILITY"


def test_unknown_admissible_capability_is_unranked_not_selected():
    selection = build_capability_selection_shadow(
        capability_admissibility_snapshot={
            "candidates": [
                {
                    "capability": "UNLISTED_CAPABILITY",
                    "admissibility": "ADMISSIBLE",
                }
            ]
        }
    )

    assert selection["eligible_capabilities"] == ["UNLISTED_CAPABILITY"]
    assert selection["unranked_admissible_capabilities"] == [
        "UNLISTED_CAPABILITY"
    ]
    assert selection["selected_capability"] is None
    assert selection["status"] == "UNRANKED_ADMISSIBLE"


def test_multiple_admissible_capabilities_follow_explicit_precedence():
    selection = build_capability_selection_shadow(
        capability_admissibility_snapshot={
            "candidates": [
                {"capability": "SOURCE_CONTEXT", "admissibility": "ADMISSIBLE"},
                {
                    "capability": "BRODY_CHAT_ENTRYPOINT",
                    "admissibility": "ADMISSIBLE",
                },
                {
                    "capability": "MEMORY_REINTEGRATION_CONTEXT",
                    "admissibility": "ADMISSIBLE",
                },
            ]
        }
    )

    assert selection["selected_capability"] == "BRODY_CHAT_ENTRYPOINT"
    assert selection["alternative_admissible_capabilities"] == [
        "SOURCE_CONTEXT",
        "MEMORY_REINTEGRATION_CONTEXT",
    ]


def test_source_context_is_generic_fallback_only():
    selection = build_capability_selection_shadow(
        capability_admissibility_snapshot={
            "candidates": [
                {"capability": "SOURCE_CONTEXT", "admissibility": "ADMISSIBLE"},
                {
                    "capability": "PROOF_AUDIT_CONTEXT",
                    "admissibility": "ADMISSIBLE",
                },
            ]
        }
    )

    assert selection["selected_capability"] == "PROOF_AUDIT_CONTEXT"
    assert "SOURCE_CONTEXT" in selection["alternative_admissible_capabilities"]


def test_selection_shadow_governance_is_diagnostic_only():
    _, _, _, selection = _snapshots(
        "Quel est ton rôle en tant que Jarjar ?",
        semantic_override={"topic": "OBSIDIA_BRODY_ROLE"},
    )

    assert selection["contract"] == {
        "detection_not_admissibility": True,
        "admissibility_not_selection": True,
        "selection_not_authorization": True,
    }
    assert selection["governance"] == {
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
        "authorizes_action": False,
        "selection_is_diagnostic_only": True,
    }


@pytest.mark.parametrize(
    "query, semantic_override, memzum",
    [
        (
            "Quel est ton rôle en tant que Jarjar ?",
            {"topic": "OBSIDIA_BRODY_ROLE"},
            None,
        ),
        ("Que sais-tu en mémoire sur Obsidia ?", None, {"memory_required": True}),
        ("Traduis cette demande avec OS Trad.", None, None),
        ("Push ce commit.", None, None),
    ],
)
def test_selection_shadow_does_not_change_runtime_outputs(query, semantic_override, memzum):
    _, source_pack_before, _, _ = _snapshots(
        query,
        semantic_override=semantic_override,
        memzum=memzum,
    )
    adapter = LocalBrodyRuntimeAdapter()
    before = adapter.respond(
        query,
        session_id=f"selection-before-{query}",
        language="fr",
    )
    after = adapter.respond(
        query,
        session_id=f"selection-after-{query}",
        language="fr",
    )

    assert after["final_answer"] == before["final_answer"]
    assert after["selected_runtime_path"] == source_pack_before.get(
        "selected_runtime_path"
    )
    assert after["selected_source_families"] == source_pack_before.get(
        "selected_source_families"
    )
    assert after["hydration_plan"] == source_pack_before.get("hydration_plan")
    assert after["qwen_quality_gate_reason"] == before["qwen_quality_gate_reason"]
    assert after["governed_model_projection_status"] == before[
        "governed_model_projection_status"
    ]
    assert after["true_voice_status"] == before["true_voice_status"]
    assert after["capability_selection_shadow"]["governance"][
        "selection_is_diagnostic_only"
    ] is True
