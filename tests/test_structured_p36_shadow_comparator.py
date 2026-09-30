import inspect
import sys
from copy import deepcopy
from pathlib import Path

import pytest

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


CASES = [
    {
        "case_id": "jarjar_role",
        "query": "Quel est ton rôle en tant que Jarjar ?",
        "semantic_override": {"topic": "OBSIDIA_BRODY_ROLE"},
        "structured_only": {"BRODY_CHAT_ENTRYPOINT"},
        "legacy_capabilities": {"SOURCE_CONTEXT"},
        "status": "COMPLEMENTARY_SIGNALS",
    },
    {
        "case_id": "explicit_memory",
        "query": "Que sais-tu en mémoire sur Obsidia ?",
        "memzum": {"memory_required": True},
        "shared": {"MEMORY_REINTEGRATION_CONTEXT"},
        "status": "NO_CHANGE",
    },
    {
        "case_id": "lean_proof",
        "query": "Quelles preuves Lean avons-nous ?",
        "structured_only": {"PROOF_AUDIT_CONTEXT"},
        "legacy_capabilities": {"SOURCE_CONTEXT"},
        "status": "COMPLEMENTARY_SIGNALS",
    },
    {
        "case_id": "ir_mapping",
        "query": "Structure ma demande en IR.",
        "structured_only": {
            "IR_ALPHABET_MAPPING",
            "REVERSE_OS_INTERLANGUAGE",
            "OS_TRAD_TRANSLATION",
        },
        "legacy_capabilities": {"SOURCE_CONTEXT"},
        "status": "COMPLEMENTARY_SIGNALS",
    },
    {
        "case_id": "os_trad",
        "query": "Traduis cette demande avec OS Trad.",
        "structured_only": {"SOURCE_CONTEXT"},
        "legacy_only": {"AGENT_TREE_LOOKUP", "OS_TRAD_TRANSLATION"},
        "status": "COMPLEMENTARY_SIGNALS",
    },
    {
        "case_id": "trees_34",
        "query": "Que représentent les 34 arbres ?",
        "legacy_only": {"AGENT_TREE_LOOKUP", "OS_TRAD_TRANSLATION"},
        "status": "P36_ADDS_SPECIALIST_SIGNAL",
    },
    {
        "case_id": "agents_52",
        "query": "Parle-moi des 52 agents.",
        "legacy_only": {"AGENT_TREE_LOOKUP", "OS_TRAD_TRANSLATION"},
        "status": "P36_ADDS_SPECIALIST_SIGNAL",
    },
    {
        "case_id": "generic_obsidia",
        "query": "Explique-moi Obsidia.",
        "shared": {"SOURCE_CONTEXT"},
        "status": "NO_CHANGE",
    },
    {
        "case_id": "ordinary_world",
        "query": "Capitale du Japon.",
        "legacy_only": {"SOURCE_CONTEXT"},
        "status": "NO_STRUCTURED_SIGNAL",
    },
    {
        "case_id": "action_request",
        "query": "Push ce commit.",
        "shared": {"ACTION_REQUEST_BLOCKED"},
        "status": "NO_CHANGE",
    },
]


def _semantic_for(case):
    semantic = build_semantic_query(case["query"])
    if "semantic_override" in case:
        semantic = {**semantic, **case["semantic_override"]}
    return semantic


def _hint_and_source_pack(case):
    ir = build_ir(case["query"])
    semantic = _semantic_for(case)
    memzum = dict(case.get("memzum") or {})
    hint = build_structured_capability_hint(
        ir=ir,
        semantic=semantic,
        memzum=memzum,
    )
    source_pack = build_brody_context_from_source_packs(
        query=case["query"],
        limit=5,
    )
    return ir, semantic, memzum, hint, source_pack


def _snapshot(case):
    ir, semantic, memzum, hint, source_pack = _hint_and_source_pack(case)
    return build_structured_p36_shadow_comparison(
        structured_capability_snapshot=hint,
        p36_snapshot={
            "detected_intents": source_pack.get("detected_intents"),
            "required_capabilities": source_pack.get("required_capabilities"),
            "selected_runtime_path": source_pack.get(
                "selected_runtime_path"
            ),
            "selected_source_families": source_pack.get(
                "selected_source_families"
            ),
            "hydration_plan": source_pack.get("hydration_plan"),
        },
        unified_ir_snapshot=ir,
        semantic_snapshot=semantic,
        memzum_snapshot=memzum,
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_structured_p36_shadow_comparator_representative_cases(case):
    snapshot = _snapshot(case)

    assert snapshot["status"] == "STRUCTURED_P36_SHADOW_COMPARATOR_READY"
    assert snapshot["augmentation_status"] == case["status"]
    assert set(case.get("legacy_capabilities", ())) <= set(
        snapshot["legacy_capabilities"]
    )
    assert set(case.get("structured_only", ())) <= set(
        snapshot["structured_only"]
    )
    assert set(case.get("legacy_only", ())) <= set(snapshot["legacy_only"])
    assert set(case.get("shared", ())) <= set(snapshot["shared"])
    assert snapshot["union_semantics"] == "OBSERVATION_SET_ONLY"


def test_union_capabilities_are_observation_only_not_selection_or_authority():
    snapshot = _snapshot(CASES[0])

    assert snapshot["union_capabilities"] == [
        "SOURCE_CONTEXT",
        "BRODY_CHAT_ENTRYPOINT",
    ]
    governance = snapshot["governance"]
    assert governance["selects_runtime_path"] is False
    assert governance["authorizes_capability"] is False
    assert governance["decision_authority"] == "KX108_ONLY"
    assert governance["readonly"] is True
    assert governance["shadow_only"] is True
    assert governance["advisory_only"] is True
    assert governance["emits_act"] is False
    assert governance["memory_write"] is False
    assert governance["kernel_mutation"] is False
    assert governance["x108_mutation"] is False


def test_comparator_does_not_accept_raw_text_or_call_p36():
    signature = inspect.signature(build_structured_p36_shadow_comparison)

    assert "message" not in signature.parameters
    assert "query" not in signature.parameters
    assert "raw_text" not in signature.parameters


@pytest.mark.parametrize("case", [CASES[0], CASES[3], CASES[5], CASES[9]], ids=lambda case: case["case_id"])
def test_comparator_does_not_mutate_legacy_p36_snapshots(case):
    _, _, _, hint, source_pack = _hint_and_source_pack(case)
    selected_path_before = deepcopy(source_pack.get("selected_runtime_path"))
    selected_source_families_before = deepcopy(
        source_pack.get("selected_source_families")
    )
    hydration_plan_before = deepcopy(source_pack.get("hydration_plan"))

    build_structured_p36_shadow_comparison(
        structured_capability_snapshot=hint,
        p36_snapshot={
            "detected_intents": source_pack.get("detected_intents"),
            "required_capabilities": source_pack.get("required_capabilities"),
            "selected_runtime_path": source_pack.get(
                "selected_runtime_path"
            ),
            "selected_source_families": source_pack.get(
                "selected_source_families"
            ),
            "hydration_plan": source_pack.get("hydration_plan"),
        },
    )

    assert source_pack.get("selected_runtime_path") == selected_path_before
    assert source_pack.get("selected_source_families") == (
        selected_source_families_before
    )
    assert source_pack.get("hydration_plan") == hydration_plan_before


@pytest.mark.parametrize("case", [CASES[0], CASES[1], CASES[5], CASES[9]], ids=lambda case: case["case_id"])
def test_adapter_exposes_shadow_snapshot_without_changing_runtime_selection(case):
    _, _, _, _, source_pack_before = _hint_and_source_pack(case)

    result = LocalBrodyRuntimeAdapter().respond(
        case["query"],
        session_id=f"p36-shadow-comparator-{case['case_id']}",
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
    snapshot = result["structured_p36_shadow_comparator"]
    assert snapshot["legacy_selected_path"] == result["selected_runtime_path"]
    assert snapshot["legacy_selected_source_families"] == result[
        "selected_source_families"
    ]
    assert snapshot["legacy_hydration_plan"] == result["hydration_plan"]
    assert snapshot["governance"]["selects_runtime_path"] is False


def test_extraction_gaps_remain_preserved():
    proof_case = {
        "query": "Quelles preuves existent pour X108 ?",
    }
    os_trad_case = {
        "query": "Traduis cette demande avec OS Trad.",
    }

    proof = _snapshot(proof_case)
    os_trad = _snapshot(os_trad_case)

    assert "PROOF_AUDIT_CONTEXT" not in proof["structured_capabilities"]
    assert "OS_TRAD_TRANSLATION" not in os_trad["structured_capabilities"]
    assert "OS_TRAD_TRANSLATION" in os_trad["legacy_capabilities"]
    assert "AGENT_TREE_LOOKUP" in os_trad["legacy_capabilities"]
