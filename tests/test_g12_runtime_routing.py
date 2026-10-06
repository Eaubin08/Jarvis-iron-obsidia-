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
