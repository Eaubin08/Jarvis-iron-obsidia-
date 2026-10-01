import sys
from pathlib import Path

import pytest

from jarvis.obsidia_port.capability_admissibility import (
    build_capability_admissibility_shadow,
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
    return hint, source_pack, comparator, admissibility


def _candidate(snapshot, capability):
    return next(
        candidate
        for candidate in snapshot["candidates"]
        if candidate["capability"] == capability
    )


@pytest.mark.parametrize(
    "query, semantic_override, memzum, capability, provenance",
    [
        (
            "Quel est ton rôle en tant que Jarjar ?",
            {"topic": "OBSIDIA_BRODY_ROLE"},
            None,
            "BRODY_CHAT_ENTRYPOINT",
            {"SEMANTIC_TOPIC"},
        ),
        (
            "Que sais-tu en mémoire sur Obsidia ?",
            None,
            {"memory_required": True},
            "MEMORY_REINTEGRATION_CONTEXT",
            {"SHARED_STRUCTURED_P36"},
        ),
        (
            "Quelles preuves Lean avons-nous ?",
            None,
            None,
            "PROOF_AUDIT_CONTEXT",
            {"STRUCTURED_IR", "SEMANTIC_TOPIC"},
        ),
        (
            "Structure ma demande en IR.",
            None,
            None,
            "IR_ALPHABET_MAPPING",
            {"STRUCTURED_IR"},
        ),
        (
            "Push ce commit.",
            None,
            None,
            "ACTION_REQUEST_BLOCKED",
            {"SHARED_STRUCTURED_P36"},
        ),
    ],
)
def test_admissible_structured_and_shared_capabilities(query, semantic_override, memzum, capability, provenance):
    _, _, _, snapshot = _snapshots(
        query,
        semantic_override=semantic_override,
        memzum=memzum,
    )
    candidate = _candidate(snapshot, capability)

    assert candidate["admissibility"] == "ADMISSIBLE"
    assert set(candidate["provenance"]) == provenance
    assert capability in snapshot["admissible_capabilities"]


@pytest.mark.parametrize(
    "query",
    [
        "Que représentent les 34 arbres ?",
        "Parle-moi des 52 agents.",
    ],
)
def test_tree_agent_lookup_is_p36_specialist_admissible_and_os_trad_bundle_needs_review(query):
    _, _, _, snapshot = _snapshots(query)

    tree = _candidate(snapshot, "AGENT_TREE_LOOKUP")
    os_trad = _candidate(snapshot, "OS_TRAD_TRANSLATION")

    assert tree["admissibility"] == "ADMISSIBLE"
    assert tree["provenance"] == ["P36_SPECIALIST"]
    assert tree["reason"] == "P36_SPECIALIST_AGENT_TREE_ROUTE"
    assert os_trad["admissibility"] == "REVIEW_REQUIRED"
    assert os_trad["reason"] == "P36_BUNDLED_CAPABILITY_REQUIRES_INDIVIDUAL_PROVENANCE"


def test_os_trad_specialist_is_admissible_but_agent_tree_bundle_needs_review():
    _, _, _, snapshot = _snapshots("Traduis cette demande avec OS Trad.")

    os_trad = _candidate(snapshot, "OS_TRAD_TRANSLATION")
    tree = _candidate(snapshot, "AGENT_TREE_LOOKUP")
    structured_source = _candidate(snapshot, "SOURCE_CONTEXT")

    assert os_trad["admissibility"] == "ADMISSIBLE"
    assert os_trad["provenance"] == ["P36_SPECIALIST"]
    assert os_trad["reason"] == "P36_SPECIALIST_OS_TRAD_ROUTE"
    assert tree["admissibility"] == "REVIEW_REQUIRED"
    assert structured_source["admissibility"] == "INSUFFICIENT_PROVENANCE"


def test_proof_x108_extraction_gap_is_preserved():
    hint, _, _, snapshot = _snapshots("Quelles preuves existent pour X108 ?")

    assert "PROOF_AUDIT_CONTEXT" not in hint["structured_capability_hints"]
    assert "PROOF_AUDIT_CONTEXT" not in [
        candidate["capability"] for candidate in snapshot["candidates"]
    ]
    assert "SOURCE_CONTEXT" in snapshot["insufficient_provenance_capabilities"]


def test_generic_obsidia_shared_source_context_is_admissible():
    _, _, _, snapshot = _snapshots("Explique-moi Obsidia.")
    source = _candidate(snapshot, "SOURCE_CONTEXT")

    assert source["admissibility"] == "ADMISSIBLE"
    assert source["provenance"] == ["SHARED_STRUCTURED_P36"]


def test_ordinary_world_knowledge_does_not_gain_project_capability():
    _, _, _, snapshot = _snapshots("Capitale du Japon.")

    capabilities = {candidate["capability"] for candidate in snapshot["candidates"]}
    assert not capabilities & {
        "BRODY_CHAT_ENTRYPOINT",
        "MEMORY_REINTEGRATION_CONTEXT",
        "PROOF_AUDIT_CONTEXT",
        "AGENT_TREE_LOOKUP",
        "OS_TRAD_TRANSLATION",
    }
    assert snapshot["admissible_capabilities"] == []
    assert snapshot["insufficient_provenance_capabilities"] == ["SOURCE_CONTEXT"]


def test_governance_and_contract_are_shadow_only():
    _, _, _, snapshot = _snapshots(
        "Quel est ton rôle en tant que Jarjar ?",
        semantic_override={"topic": "OBSIDIA_BRODY_ROLE"},
    )

    assert snapshot["contract"] == {
        "detection_not_admissibility": True,
        "admissibility_not_selection": True,
        "selection_not_authorization": True,
    }
    assert snapshot["governance"] == {
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


@pytest.mark.parametrize(
    "query, semantic_override, memzum",
    [
        (
            "Quel est ton rôle en tant que Jarjar ?",
            {"topic": "OBSIDIA_BRODY_ROLE"},
            None,
        ),
        ("Que sais-tu en mémoire sur Obsidia ?", None, {"memory_required": True}),
        ("Que représentent les 34 arbres ?", None, None),
        ("Push ce commit.", None, None),
    ],
)
def test_adapter_exposes_admissibility_without_changing_runtime_outputs(query, semantic_override, memzum):
    _, source_pack_before, _, _ = _snapshots(
        query,
        semantic_override=semantic_override,
        memzum=memzum,
    )

    adapter = LocalBrodyRuntimeAdapter()
    before = adapter.respond(
        query,
        session_id=f"admissibility-before-{query}",
        language="fr",
    )
    after = adapter.respond(
        query,
        session_id=f"admissibility-after-{query}",
        language="fr",
    )

    assert after["selected_runtime_path"] == source_pack_before.get(
        "selected_runtime_path"
    )
    assert after["selected_source_families"] == source_pack_before.get(
        "selected_source_families"
    )
    assert after["hydration_plan"] == source_pack_before.get("hydration_plan")
    assert after["selected_runtime_path"] == before["selected_runtime_path"]
    assert after["selected_source_families"] == before["selected_source_families"]
    assert after["hydration_plan"] == before["hydration_plan"]
    assert after["final_answer"] == before["final_answer"]
    assert after["capability_admissibility_shadow"]["governance"][
        "selects_runtime_path"
    ] is False
