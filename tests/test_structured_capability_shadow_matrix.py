import sys
from collections import Counter
from pathlib import Path

import pytest

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


CORPUS = [
    {
        "case_id": "A01",
        "family": "BRODY_ROLE",
        "query": "Quel est ton rôle en tant que Jarjar ?",
        "semantic_override": {"topic": "OBSIDIA_BRODY_ROLE"},
        "must_have_hint": "BRODY_CHAT_ENTRYPOINT",
    },
    {
        "case_id": "A02",
        "family": "BRODY_ROLE",
        "query": "Qui est Brody dans Obsidia ?",
        "semantic_override": {"topic": "OBSIDIA_BRODY_ROLE"},
        "must_have_hint": "BRODY_CHAT_ENTRYPOINT",
    },
    {
        "case_id": "A03",
        "family": "BRODY_ROLE",
        "query": "À quoi sert Jarjar ?",
        "semantic_override": {"topic": "OBSIDIA_BRODY_ROLE"},
        "must_have_hint": "BRODY_CHAT_ENTRYPOINT",
    },
    {
        "case_id": "B04",
        "family": "MEMORY",
        "query": "Que sais-tu en mémoire sur Obsidia ?",
        "memzum": {"memory_required": True},
        "must_have_hint": "MEMORY_REINTEGRATION_CONTEXT",
    },
    {
        "case_id": "B05",
        "family": "MEMORY",
        "query": "Retrouve ce que tu sais sur X108.",
        "memzum": {"memory_required": True},
        "must_have_hint": "MEMORY_REINTEGRATION_CONTEXT",
    },
    {
        "case_id": "B06",
        "family": "MEMORY",
        "query": "Est-ce que tu te souviens de Brody ?",
        "memzum": {"memory_required": True},
        "must_have_hint": "MEMORY_REINTEGRATION_CONTEXT",
    },
    {
        "case_id": "C07",
        "family": "PROOF_AUDIT",
        "query": "Quelles preuves Lean avons-nous ?",
        "must_have_hint": "PROOF_AUDIT_CONTEXT",
    },
    {
        "case_id": "C08",
        "family": "PROOF_AUDIT",
        "query": "Audit les invariants de cette architecture.",
        "must_have_hint": "PROOF_AUDIT_CONTEXT",
    },
    {
        "case_id": "C09",
        "family": "PROOF_AUDIT",
        "query": "Quelles preuves existent pour X108 ?",
    },
    {
        "case_id": "D10",
        "family": "IR_OS_TRAD",
        "query": "Structure ma demande en IR.",
        "any_hint": {
            "IR_ALPHABET_MAPPING",
            "REVERSE_OS_INTERLANGUAGE",
            "OS_TRAD_TRANSLATION",
        },
    },
    {
        "case_id": "D11",
        "family": "IR_OS_TRAD",
        "query": "Traduis cette demande avec OS Trad.",
    },
    {
        "case_id": "D12",
        "family": "IR_OS_TRAD",
        "query": "Montre-moi le mapping IR.",
        "any_hint": {
            "IR_ALPHABET_MAPPING",
            "REVERSE_OS_INTERLANGUAGE",
            "OS_TRAD_TRANSLATION",
        },
    },
    {
        "case_id": "E13",
        "family": "ACTION_BOUNDARY",
        "query": "Push ce commit.",
        "must_have_hint": "ACTION_REQUEST_BLOCKED",
    },
    {
        "case_id": "E14",
        "family": "ACTION_BOUNDARY",
        "query": "Supprime ce fichier.",
        "must_have_hint": "ACTION_REQUEST_BLOCKED",
    },
    {
        "case_id": "E15",
        "family": "ACTION_BOUNDARY",
        "query": "Déploie cette version.",
        "must_have_hint": "ACTION_REQUEST_BLOCKED",
    },
    {
        "case_id": "F16",
        "family": "GENERIC_OBSIDIA",
        "query": "Explique-moi Obsidia.",
        "forbidden_structured": {"AGENT_TREE_LOOKUP"},
    },
    {
        "case_id": "F17",
        "family": "GENERIC_OBSIDIA",
        "query": "Quelle est l'architecture d'Obsidia ?",
        "forbidden_structured": {"AGENT_TREE_LOOKUP"},
    },
    {
        "case_id": "F18",
        "family": "GENERIC_OBSIDIA",
        "query": "Tu peux me dire quoi sur Obsidia ? Des tailles ?",
        "memzum": {"memory_required": True},
        "forbidden_structured": {"AGENT_TREE_LOOKUP"},
    },
    {
        "case_id": "G19",
        "family": "EXPLICIT_TREE_AGENT",
        "query": "Que représentent les 34 arbres ?",
    },
    {
        "case_id": "G20",
        "family": "EXPLICIT_TREE_AGENT",
        "query": "Parle-moi des 52 agents.",
    },
    {
        "case_id": "G21",
        "family": "EXPLICIT_TREE_AGENT",
        "query": "Quelle est la structure des arbres et agents ?",
    },
    {
        "case_id": "H22",
        "family": "ORDINARY_WORLD",
        "query": "Capitale du Japon.",
        "forbidden_structured": {
            "MEMORY_REINTEGRATION_CONTEXT",
            "AGENT_TREE_LOOKUP",
            "BRODY_CHAT_ENTRYPOINT",
            "PROOF_AUDIT_CONTEXT",
            "OS_TRAD_TRANSLATION",
        },
    },
    {
        "case_id": "H23",
        "family": "ORDINARY_WORLD",
        "query": "Pourquoi le ciel est bleu ?",
        "forbidden_structured": {
            "MEMORY_REINTEGRATION_CONTEXT",
            "AGENT_TREE_LOOKUP",
            "BRODY_CHAT_ENTRYPOINT",
            "PROOF_AUDIT_CONTEXT",
            "OS_TRAD_TRANSLATION",
        },
    },
    {
        "case_id": "H24",
        "family": "ORDINARY_WORLD",
        "query": "Combien font 12 multiplié par 8 ?",
        "forbidden_structured": {
            "MEMORY_REINTEGRATION_CONTEXT",
            "AGENT_TREE_LOOKUP",
            "BRODY_CHAT_ENTRYPOINT",
            "PROOF_AUDIT_CONTEXT",
            "OS_TRAD_TRANSLATION",
        },
    },
]

FORBIDDEN_PROJECT_CAPABILITIES = {
    "MEMORY_REINTEGRATION_CONTEXT",
    "AGENT_TREE_LOOKUP",
    "BRODY_CHAT_ENTRYPOINT",
    "PROOF_AUDIT_CONTEXT",
    "OS_TRAD_TRANSLATION",
}

NON_INTERFERENCE_CASES = {
    "A01",
    "B04",
    "E13",
    "G19",
    "H22",
}


def _semantic_for(case):
    semantic = build_semantic_query(case["query"])
    if "semantic_override" in case:
        semantic = {**semantic, **case["semantic_override"]}
    return semantic


def _snapshot(case):
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
    comparison = compare_structured_hint_with_p36(
        structured_capability_hints=hint["structured_capability_hints"],
        p36_required_capabilities=source_pack.get("required_capabilities"),
    )
    selected_path = source_pack.get("selected_runtime_path") or {}
    p36_selected_capability = None
    if isinstance(selected_path, dict):
        chain = selected_path.get("capability_chain")
        if isinstance(chain, list) and chain:
            p36_selected_capability = chain[0]
    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "query": case["query"],
        "structured_hints": hint["structured_capability_hints"],
        "structured_primary": hint["primary_capability_hint"],
        "structured_confidence": hint["confidence_class"],
        "p36_detected_intents": source_pack.get("detected_intents") or [],
        "p36_required_capabilities": (
            source_pack.get("required_capabilities") or []
        ),
        "p36_selected_capability": p36_selected_capability,
        "p36_selected_source_families": (
            source_pack.get("selected_source_families") or []
        ),
        "selected_runtime_path": source_pack.get("selected_runtime_path"),
        "selected_source_families": source_pack.get(
            "selected_source_families"
        ),
        "hydration_plan": source_pack.get("hydration_plan"),
        "comparison_status": comparison["capability_route_agreement"],
        "capability_route_divergence": comparison[
            "capability_route_divergence"
        ],
        "observation_class": _classify_observation(
            hint["structured_capability_hints"],
            source_pack.get("required_capabilities") or [],
            comparison["capability_route_agreement"],
            case["family"],
        ),
        "governance": {
            "decision_authority": hint["decision_authority"],
            "readonly": hint["readonly"],
            "emits_act": hint["emits_act"],
            "memory_write": hint["memory_write"],
            "kernel_mutation": hint["kernel_mutation"],
            "x108_mutation": hint["x108_mutation"],
        },
    }


def _classify_observation(
    structured_hints,
    p36_capabilities,
    comparison_status,
    family,
):
    structured = set(structured_hints)
    p36 = set(p36_capabilities)
    if comparison_status == "AGREE":
        return "EQUIVALENT" if structured == p36 else "REQUIRES_REVIEW"
    if comparison_status == "INSUFFICIENT_STRUCTURED_SIGNAL":
        if p36:
            return "P36_MORE_SPECIFIC"
        return "BOTH_INSUFFICIENT"
    if comparison_status == "INSUFFICIENT_P36_SIGNAL":
        return "STRUCTURED_MORE_SPECIFIC" if structured else "BOTH_INSUFFICIENT"
    if not structured and not p36:
        return "BOTH_INSUFFICIENT"
    if family == "ORDINARY_WORLD" and structured & FORBIDDEN_PROJECT_CAPABILITIES:
        return "POTENTIAL_FALSE_POSITIVE_STRUCTURED"
    if family == "GENERIC_OBSIDIA" and "AGENT_TREE_LOOKUP" in structured:
        return "POTENTIAL_FALSE_POSITIVE_STRUCTURED"
    if family == "GENERIC_OBSIDIA" and "AGENT_TREE_LOOKUP" in p36:
        return "POTENTIAL_FALSE_POSITIVE_P36"
    if family == "EXPLICIT_TREE_AGENT" and "AGENT_TREE_LOOKUP" in p36:
        return "P36_MORE_SPECIFIC"
    if structured and p36:
        return "REQUIRES_REVIEW"
    if structured:
        return "STRUCTURED_MORE_SPECIFIC"
    if p36:
        return "P36_MORE_SPECIFIC"
    return "BOTH_INSUFFICIENT"


MATRIX_SNAPSHOTS = [_snapshot(case) for case in CORPUS]


@pytest.mark.parametrize("snapshot", MATRIX_SNAPSHOTS, ids=lambda s: s["case_id"])
def test_shadow_matrix_governance_and_expected_structured_signals(snapshot):
    governance = snapshot["governance"]
    assert governance["decision_authority"] == "KX108_ONLY"
    assert governance["readonly"] is True
    assert governance["emits_act"] is False
    assert governance["memory_write"] is False
    assert governance["kernel_mutation"] is False
    assert governance["x108_mutation"] is False

    case = next(c for c in CORPUS if c["case_id"] == snapshot["case_id"])
    hints = set(snapshot["structured_hints"])
    if "must_have_hint" in case:
        assert case["must_have_hint"] in hints
    if "any_hint" in case:
        assert hints & set(case["any_hint"])
    if "forbidden_structured" in case:
        assert not hints & set(case["forbidden_structured"])


def test_generic_obsidia_does_not_gain_agent_tree_from_project_context():
    generic = [
        snapshot
        for snapshot in MATRIX_SNAPSHOTS
        if snapshot["family"] == "GENERIC_OBSIDIA"
    ]
    assert generic
    for snapshot in generic:
        assert "AGENT_TREE_LOOKUP" not in snapshot["structured_hints"]


def test_ordinary_world_questions_do_not_force_project_capabilities():
    ordinary = [
        snapshot
        for snapshot in MATRIX_SNAPSHOTS
        if snapshot["family"] == "ORDINARY_WORLD"
    ]
    assert ordinary
    for snapshot in ordinary:
        assert not set(snapshot["structured_hints"]) & FORBIDDEN_PROJECT_CAPABILITIES


def test_explicit_actions_emit_action_request_blocked_hint_only():
    actions = [
        snapshot
        for snapshot in MATRIX_SNAPSHOTS
        if snapshot["family"] == "ACTION_BOUNDARY"
    ]
    assert actions
    for snapshot in actions:
        assert "ACTION_REQUEST_BLOCKED" in snapshot["structured_hints"]
        assert snapshot["governance"]["emits_act"] is False


def test_non_interference_with_p36_selection_for_representative_cases():
    adapter = LocalBrodyRuntimeAdapter()
    for snapshot in MATRIX_SNAPSHOTS:
        if snapshot["case_id"] not in NON_INTERFERENCE_CASES:
            continue
        result = adapter.respond(
            snapshot["query"],
            session_id=f"shadow-matrix-{snapshot['case_id']}",
            language="fr",
        )
        assert result["status"] == "LOCAL_BRODY_RUNTIME_PASS"
        assert result["selected_runtime_path"] == snapshot[
            "selected_runtime_path"
        ]
        assert result["selected_source_families"] == snapshot[
            "selected_source_families"
        ]
        assert result["hydration_plan"] == snapshot["hydration_plan"]


def test_shadow_matrix_summary_counts_are_stable():
    status_counts = Counter(
        snapshot["comparison_status"] for snapshot in MATRIX_SNAPSHOTS
    )
    observation_counts = Counter(
        snapshot["observation_class"] for snapshot in MATRIX_SNAPSHOTS
    )
    assert sum(status_counts.values()) == 24
    assert sum(observation_counts.values()) == 24
    assert set(status_counts) <= {
        "AGREE",
        "DIVERGE",
        "INSUFFICIENT_STRUCTURED_SIGNAL",
        "INSUFFICIENT_P36_SIGNAL",
    }
    assert set(observation_counts) <= {
        "STRUCTURED_MORE_SPECIFIC",
        "P36_MORE_SPECIFIC",
        "EQUIVALENT",
        "BOTH_INSUFFICIENT",
        "POTENTIAL_FALSE_POSITIVE_STRUCTURED",
        "POTENTIAL_FALSE_POSITIVE_P36",
        "REQUIRES_REVIEW",
    }
