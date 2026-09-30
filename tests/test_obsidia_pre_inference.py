from jarvis.obsidia_pre_inference import ObsidiaPreInferenceAdapter


def test_obsidia_question_routes_to_brody():
    d = ObsidiaPreInferenceAdapter().route("Explique-moi le contexte d'Obsidia.")
    assert d.route == "brody"
    assert d.ir["intent_type"] == "question"
    assert d.gate["verdict"] == "ALLOW"


def test_canonical_memory_can_close_without_model():
    d = ObsidiaPreInferenceAdapter().route("Quel est le statut actuel ?")
    assert d.route in {"memory_hit", "no_model_needed", "runtime_state_readonly"}
    if d.route == "memory_hit":
        assert d.direct_answer


def test_unresolved_phrase_does_not_claim_confidence():
    d = ObsidiaPreInferenceAdapter().route("Quel est ton rôle en tant que Jarvis ?")
    assert d.route == "clarification_needed"
    assert d.is_confident is False


def test_world_action_is_governed_before_cognition():
    d = ObsidiaPreInferenceAdapter().route("push force")
    assert d.gate["verdict"] in {"DENY", "HOLD"}
    assert d.direct_answer is not None


def test_jarjar_role_uses_brody_semantic_role_route():
    d = ObsidiaPreInferenceAdapter().route("Quel est ton rôle en tant que Jarjar ?")
    assert d.route == "brody"
    assert d.ir["intent_type"] == "question"
    assert d.ir["target_layer"] == "brody"
