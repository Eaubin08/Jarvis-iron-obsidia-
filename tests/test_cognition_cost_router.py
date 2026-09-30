from jarvis.cognition_bridge import CostAwareCognitionRouter
from jarvis.contracts import ContextSnapshot
from jarvis.providers.local_stub import StubCognition


class Provider:
    def __init__(self, answer=None, fail=False):
        self.answer = answer
        self.fail = fail
        self.calls = []

    def respond(self, user_input, context):
        self.calls.append((user_input, False))
        if self.fail:
            raise RuntimeError("offline")
        return self.answer

    def respond_with_options(self, user_input, context, *, include_live):
        self.calls.append((user_input, include_live))
        if self.fail:
            raise RuntimeError("offline")
        return self.answer


def ctx():
    return ContextSnapshot("session")


def test_presence_is_zero_cost_and_calls_no_provider():
    brody = Provider("brody")
    qwen = Provider("qwen")
    router = CostAwareCognitionRouter(StubCognition(), brody, qwen)
    assert router.respond("Hey Jarvis", ctx()) == "Oui ?"
    assert brody.calls == []
    assert qwen.calls == []


def test_general_question_prefers_qwen():
    brody = Provider("brody")
    qwen = Provider("qwen")
    router = CostAwareCognitionRouter(StubCognition(), brody, qwen)
    assert router.respond("Pourquoi le ciel est bleu ?", ctx()) == "qwen"
    assert qwen.calls == [("Pourquoi le ciel est bleu ?", False)]
    assert brody.calls == []


def test_project_question_prefers_brody():
    brody = Provider("brody")
    qwen = Provider("qwen")
    router = CostAwareCognitionRouter(StubCognition(), brody, qwen)
    assert router.respond("Explique Obsidia", ctx()) == "brody"
    assert brody.calls
    assert qwen.calls == []


def test_environment_question_prefers_qwen_with_live_context():
    brody = Provider("brody")
    qwen = Provider("qwen")
    router = CostAwareCognitionRouter(StubCognition(), brody, qwen)
    assert router.respond("Combien d'écrans tu vois ?", ctx()) == "qwen"
    assert qwen.calls == [("Combien d'écrans tu vois ?", True)]
    assert brody.calls == []


def test_qwen_failure_falls_back_to_brody():
    brody = Provider("brody")
    qwen = Provider(fail=True)
    router = CostAwareCognitionRouter(StubCognition(), brody, qwen)
    assert router.respond("Pourquoi le ciel est bleu ?", ctx()) == "brody"
