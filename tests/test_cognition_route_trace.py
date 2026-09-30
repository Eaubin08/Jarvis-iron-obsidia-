from jarvis.cognition_bridge import CostAwareCognitionRouter
from jarvis.contracts import ContextSnapshot
from jarvis.providers.local_stub import StubCognition


class Provider:
    def __init__(self, answer):
        self.answer = answer

    def respond(self, text, context):
        return self.answer

    def respond_with_options(self, text, context, *, include_live):
        return self.answer


def ctx():
    return ContextSnapshot("test")


def test_router_records_general_route():
    router = CostAwareCognitionRouter(
        StubCognition(),
        Provider("brody"),
        Provider("qwen"),
        Provider("vision"),
    )
    assert router.respond("Pourquoi le ciel est bleu ?", ctx()) == "qwen"
    assert router.last_route == "qwen"


def test_router_records_project_route():
    router = CostAwareCognitionRouter(
        StubCognition(),
        Provider("brody"),
        Provider("qwen"),
        Provider("vision"),
    )
    assert router.respond("Explique Obsidia", ctx()) == "brody"
    assert router.last_route == "brody"


def test_router_records_visual_route():
    router = CostAwareCognitionRouter(
        StubCognition(),
        Provider("brody"),
        Provider("qwen"),
        Provider("vision"),
    )
    assert router.respond("Décris ce que tu vois sur mon écran", ctx()) == "vision"
    assert router.last_route == "vision"
