import sys
from pathlib import Path

import pytest

from jarvis.obsidia_port.bounded_routing_shadow_experiment import (
    build_bounded_routing_shadow_experiment,
)
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

from apps.obsidia_api.brody_semantic_query_router import build_semantic_query  # noqa: E402
from runtime_wiring.source_runtime.brody_source_context_bridge import (  # noqa: E402
    build_brody_context_from_source_packs,
)


def _experiment(query, *, semantic_override=None, memzum=None):
    ir = build_ir(query)
    semantic = build_semantic_query(query)
    if semantic_override:
        semantic = {**semantic, **semantic_override}
    memzum = dict(memzum or {})
    hint = build_structured_capability_hint(ir=ir, semantic=semantic, memzum=memzum)
    source_pack = build_brody_context_from_source_packs(query=query, limit=5)
    p36 = {
        "detected_intents": source_pack.get("detected_intents"),
        "required_capabilities": source_pack.get("required_capabilities"),
        "selected_runtime_path": source_pack.get("selected_runtime_path"),
        "selected_source_families": source_pack.get("selected_source_families"),
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
    experiment = build_bounded_routing_shadow_experiment(
        capability_selection_snapshot=selection,
        legacy_p36_snapshot=p36,
        available_families=source_pack.get("available_families"),
    )
    return source_pack, selection, experiment


@pytest.mark.parametrize(
    "query, semantic_override, memzum, capability",
    [
        ("Quel est ton rôle en tant que Jarjar ?", {"topic": "OBSIDIA_BRODY_ROLE"}, None, "BRODY_CHAT_ENTRYPOINT"),
        ("Que sais-tu en mémoire sur Obsidia ?", None, {"memory_required": True}, "MEMORY_REINTEGRATION_CONTEXT"),
        ("Quelles preuves Lean avons-nous ?", None, None, "PROOF_AUDIT_CONTEXT"),
        ("Structure ma demande en IR.", None, None, "IR_ALPHABET_MAPPING"),
        ("Traduis cette demande avec OS Trad.", None, None, "OS_TRAD_TRANSLATION"),
        ("Que représentent les 34 arbres ?", None, None, "AGENT_TREE_LOOKUP"),
    ],
)
def test_selected_capability_resolves_existing_p36_template(
    query, semantic_override, memzum, capability
):
    _, selection, experiment = _experiment(
        query, semantic_override=semantic_override, memzum=memzum
    )
    assert selection["selected_capability"] == capability
    assert experiment["status"] == "SHADOW_P36_MAPPING_READY"
    assert experiment["selected_capability"] == capability
    assert experiment["shadow_p36_path"]["capability_chain"] == [capability]
    assert experiment["shadow_p36_path"]["decision_authority"] == "KX108_ONLY"
    assert experiment["shadow_hydration_plan"]["runtime_allowed_now"] is False


def test_proof_x108_extraction_gap_stays_fail_closed():
    _, selection, experiment = _experiment("Quelles preuves existent pour X108 ?")
    assert selection["selected_capability"] is None
    assert experiment["status"] == "NO_SHADOW_SELECTION"
    assert experiment["shadow_p36_path"] == {}


def test_ordinary_world_query_stays_fail_closed():
    _, selection, experiment = _experiment("Capitale du Japon.")
    assert selection["selected_capability"] is None
    assert experiment["status"] == "NO_SHADOW_SELECTION"


def test_action_classification_never_becomes_source_routing():
    _, selection, experiment = _experiment("Push ce commit.")
    assert selection["selected_capability"] == "ACTION_REQUEST_BLOCKED"
    assert experiment["status"] == "AUTHORITY_BOUNDARY_EXCLUDED"
    assert experiment["shadow_p36_path"] == {}


def test_os_trad_and_agent_tree_share_family_but_keep_distinct_capability():
    _, _, os_trad = _experiment("Traduis cette demande avec OS Trad.")
    _, _, trees = _experiment("Que représentent les 34 arbres ?")
    assert os_trad["selected_capability"] == "OS_TRAD_TRANSLATION"
    assert trees["selected_capability"] == "AGENT_TREE_LOOKUP"
    assert os_trad["shadow_p36_path"]["source_families"] == ["OS_TRAD_REVERSE_OS"]
    assert trees["shadow_p36_path"]["source_families"] == ["OS_TRAD_REVERSE_OS"]


def test_governance_remains_counterfactual_only():
    _, _, experiment = _experiment(
        "Quel est ton rôle en tant que Jarjar ?",
        semantic_override={"topic": "OBSIDIA_BRODY_ROLE"},
    )
    assert experiment["governance"] == {
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
        "counterfactual_only": True,
    }
