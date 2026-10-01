from jarvis.obsidia_port.router_core.unified_ir import build_ir
from jarvis.obsidia_port.semantic_query_roles_v0 import build_semantic_query_roles


def test_memory_is_focus_and_obsidia_is_scope():
    text = "Est-ce que tu sais en mémoire sur Obsidia, détaille et explique."
    roles = build_semantic_query_roles(user_message=text)
    assert roles["focus"] == "MEMORY"
    assert roles["scope"] == ["OBSIDIA"]
    assert roles["operations"] == ["RETRIEVE_KNOWLEDGE", "EXPLAIN"]
    assert roles["qualifiers"] == ["DETAILED"]
    assert roles["confidence"] == "HIGH"
    assert roles["governance"]["decision_authority"] == "KX108_ONLY"
    assert roles["governance"]["emits_act"] is False


def test_obsidia_alone_is_not_rewritten_as_memory_focus():
    roles = build_semantic_query_roles(
        user_message="Explique-moi simplement comment Brody et X108 travaillent dans Obsidia."
    )
    assert roles["focus"] == "OBSIDIA"
    assert roles["scope"] == []


def test_memory_without_scope_does_not_invent_obsidia():
    roles = build_semantic_query_roles(
        user_message="Qu'est-ce que tu sais en mémoire ?"
    )
    assert roles["focus"] == "MEMORY"
    assert roles["scope"] == []


def test_explicit_ir_projection_has_descriptive_intent():
    ir = build_ir("Structure ma demande en IR.")
    assert ir["intent_type"] == "structure_request"
    assert ir["target_layer"] == "terminal"
    assert ir["action_type"] == "project"
    assert ir["risk_level"] == "low"
    assert "intent" not in ir["missing"]


def test_ambiguous_34_trees_does_not_invent_obsidia_scope():
    roles = build_semantic_query_roles(
        user_message="Que représentent les 34 arbres ?"
    )
    assert roles["focus"] == "UNKNOWN"
    assert roles["scope"] == []
