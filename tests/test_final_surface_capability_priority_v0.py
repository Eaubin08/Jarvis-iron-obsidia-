import sys
from pathlib import Path

import pytest

from jarvis.obsidia_port.local_brody_runtime_adapter import (
    _requires_canonical_surface,
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


@pytest.mark.parametrize(
    ("utterance", "topic"),
    [
        ("Jarjar, quel est ton rôle dans Obsidia ?", "OBSIDIA_BRODY_ROLE"),
        ("Que représentent les 34 arbres dans Obsidia ?", "34_ARBRES"),
        ("Que représentent les 34 armes dans Obsidia ?", "34_ARBRES"),
    ],
)
def test_live_voice_semantic_routes_preserve_specific_topic(utterance, topic):
    assert build_semantic_query(utterance)["topic"] == topic


def test_generic_what_do_you_know_no_longer_forces_role_route():
    routed = build_semantic_query(
        "Jarjar, qu'est-ce que tu sais ? En mémoire sur Obsidia."
    )
    assert routed["topic"] != "OBSIDIA_BRODY_ROLE"


@pytest.mark.parametrize(
    "capability",
    [
        "ACTION_REQUEST_BLOCKED",
        "BRODY_CHAT_ENTRYPOINT",
        "MEMORY_REINTEGRATION_CONTEXT",
        "PROOF_AUDIT_CONTEXT",
        "IR_ALPHABET_MAPPING",
        "AGENT_TREE_LOOKUP",
    ],
)
def test_specific_capability_requires_canonical_surface(capability):
    assert _requires_canonical_surface("GENERAL", capability) is True


def test_role_topic_requires_canonical_surface_even_without_capability():
    assert _requires_canonical_surface("OBSIDIA_BRODY_ROLE", "") is True


@pytest.mark.parametrize(
    "capability",
    [
        "",
        "SOURCE_CONTEXT",
        "OS_TRAD_TRANSLATION",
        "REVERSE_OS_INTERLANGUAGE",
    ],
)
def test_open_capabilities_keep_governed_model_surface_eligible(capability):
    assert _requires_canonical_surface("GENERAL", capability) is False
