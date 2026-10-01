from types import SimpleNamespace

import pytest

from jarvis.cognition_bridge import (
    _requires_brody_semantic_route,
    _requires_brody_structured_ir_route,
)


@pytest.mark.parametrize(
    "topic",
    [
        "OBSIDIA_BRODY_ROLE",
        "OBSIDIA_PROJECT",
        "MEMORY_QUERY",
        "PROOF_QUERY",
        "34_ARBRES",
        "TREE_POLICY",
        "ACTION_BOUNDARY",
        "RIGHTS_ACTION",
        "CURRENT_STATE",
    ],
)
def test_known_semantic_capability_stays_on_brody_when_generic_ir_is_unsure(topic):
    decision = SimpleNamespace(topic={"topic": topic})
    assert _requires_brody_semantic_route(decision) is True


@pytest.mark.parametrize(
    "utterance",
    [
        "Structure ma demande en IR.",
        "Structure, ma demande en IR.",
        "La demande en IR.",
    ],
)
def test_explicit_ir_projection_stays_on_brody(utterance):
    decision = SimpleNamespace(topic={"topic": "GENERAL"})
    assert _requires_brody_structured_ir_route(utterance, decision) is True


@pytest.mark.parametrize(
    "utterance",
    [
        "Parle-moi du projet.",
        "Explique-moi simplement.",
        "Regarde mon écran.",
    ],
)
def test_open_requests_do_not_force_structured_brody_route(utterance):
    decision = SimpleNamespace(topic={"topic": "GENERAL"})
    assert _requires_brody_semantic_route(decision) is False
    assert _requires_brody_structured_ir_route(utterance, decision) is False
