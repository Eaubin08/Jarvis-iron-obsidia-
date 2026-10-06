from jarvis.core import _local_capabilities_reply
from jarvis.governed_move import _looks_like_audit_question


def test_g12_capability_query_is_answered_locally():
    reply = _local_capabilities_reply("Qu'est-ce que tu peux faire actuellement ?")
    assert reply is not None
    assert "KX108" in reply
    assert "actions gouvernées" in reply


def test_g12_readonly_audit_accepts_bounded_stt_variant():
    assert _looks_like_audit_question("audicule la derniere action") is True
    assert _looks_like_audit_question("bonjour derniere action") is False


from jarvis.cognition_bridge import is_known_obsidia_domain_query


def test_g12_known_obsidia_domains_are_detected_before_generic_qwen():
    assert is_known_obsidia_domain_query("Explique-moi le spoofing GPS") is True
    assert is_known_obsidia_domain_query("Analyse GNSS aviation") is True
    assert is_known_obsidia_domain_query("Explique-moi les volcans") is False


from jarvis.cognition_bridge import _known_domain_answer


def test_g12_spoofing_gps_uses_readonly_domain_bridge():
    routed = _known_domain_answer("Explique-moi simplement ce qu'est une attaque par spoofing GPS.")
    assert routed is not None
    route, answer = routed
    assert route == "obsidia_gps"
    assert "GPS_SPOOFING" in answer
    assert "HOLD" in answer
    assert "entièrement validée" in answer


from jarvis.integrations.obsidia_stack_cognition import (
    _is_runtime_state_query,
    _looks_like_generic_runtime_state_answer,
)


def test_g12_generic_brody_runtime_answer_is_only_valid_for_runtime_questions():
    generic = (
        "État système readonly : Brody observe le runtime sans écrire. "
        "Autorité : KX108_ONLY. Aucune décision, aucune écriture."
    )
    assert _looks_like_generic_runtime_state_answer(generic) is True
    assert _is_runtime_state_query("Quel est l'état système readonly ?") is True
    assert _is_runtime_state_query("Explique-moi le domaine trading") is False
