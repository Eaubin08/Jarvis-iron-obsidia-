from jarvis.cognition_bridge import CostAwareCognitionRouter
from jarvis.contracts import ContextSnapshot
from jarvis.providers.local_stub import StubCognition
from jarvis.obsidia_pre_inference import ObsidiaPreInferenceAdapter


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


def test_visual_question_prefers_vision_provider():
    brody = Provider("brody")
    qwen = Provider("qwen")
    vision = Provider("vision")
    router = CostAwareCognitionRouter(StubCognition(), brody, qwen, vision)
    assert router.respond("Qu'est-ce que tu vois sur la caméra ?", ctx()) == "vision"
    assert vision.calls
    assert qwen.calls == []
    assert brody.calls == []


def test_visual_failure_falls_back_to_qwen_live_metadata():
    brody = Provider("brody")
    qwen = Provider("qwen")
    vision = Provider(fail=True)
    router = CostAwareCognitionRouter(StubCognition(), brody, qwen, vision)
    assert router.respond("Décris ce que tu vois sur la caméra", ctx()) == "qwen"
    assert qwen.calls == [("Décris ce que tu vois sur la caméra", True)]


def test_runtime_state_readonly_uses_measured_brody_trace_not_qwen():
    brody = Provider("legacy semantic answer")
    brody.last_trace = {
        "voice_runtime": "BRODY_OBSIDIEN_V1_4_12A",
        "memory_source_mode": "LOCAL_GRAPHITI_INDEX_FALLBACK",
        "memory_status": "BRODY_MEMORY_RESPONSE_CHAIN_PASS",
        "native_memory_active": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
    }
    qwen = Provider("wrong qwen answer")
    router = CostAwareCognitionRouter(
        StubCognition(),
        brody,
        qwen,
        pre_inference=ObsidiaPreInferenceAdapter(),
    )

    answer = router.respond(
        "Analyse si native memory est bien la mémoire active actuellement.",
        ctx(),
    )

    assert "Native Memory n'est pas active" in answer
    assert "LOCAL_GRAPHITI_INDEX_FALLBACK" in answer
    assert "déjà en lecture seule" in answer
    assert qwen.calls == []


def test_readonly_mode_question_does_not_escalate_to_qwen():
    brody = Provider("legacy semantic answer")
    brody.last_trace = {
        "voice_runtime": "BRODY_OBSIDIEN_V1_4_12A",
        "memory_source_mode": "LOCAL_GRAPHITI_INDEX_FALLBACK",
        "memory_status": "LOCAL_INDEX_FALLBACK_PARTIAL",
        "native_memory_active": False,
        "decision_authority": "KX108_ONLY",
        "readonly": True,
    }
    qwen = Provider("wrong qwen answer")
    router = CostAwareCognitionRouter(
        StubCognition(),
        brody,
        qwen,
        pre_inference=ObsidiaPreInferenceAdapter(),
    )

    answer = router.respond("Tu peux pas passer en mode read-only ?", ctx())

    assert "déjà en lecture seule" in answer
    assert qwen.calls == []


def test_jarjar_role_alias_calls_brody_with_canonical_role_query():
    brody = Provider("brody role answer")
    qwen = Provider("qwen")
    router = CostAwareCognitionRouter(
        StubCognition(),
        brody,
        qwen,
        pre_inference=ObsidiaPreInferenceAdapter(),
    )

    answer = router.respond("Quel est ton rôle en tant que Jarjar ?", ctx())

    assert answer == "brody role answer"
    assert brody.calls == [
        ("Qui peut faire quoi entre Brody, X108 et humain mémoire ?", False)
    ]
    assert qwen.calls == []
