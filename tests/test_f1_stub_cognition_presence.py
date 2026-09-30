from jarvis.providers.local_stub import StubCognition, StubMemory


def context():
    return StubMemory().context()


def test_presence_responses_are_short_and_human():
    cognition = StubCognition()
    assert cognition.respond("Bonjour", context()) == "Salut."
    assert cognition.respond("Tu m'entends ?", context()) == "Oui, je t'entends."
    assert cognition.respond("Merci", context()) == "Avec plaisir."
    assert cognition.respond("Au revoir", context()) == "À plus."


def test_wake_prefix_can_be_ignored_for_simple_presence_phrase():
    cognition = StubCognition()
    assert cognition.respond("Hey Jarvis bonjour", context()) == "Salut."
    assert cognition.respond("Hey Jarvis", context()) == "Oui ?"


def test_unknown_input_gets_presence_ack_not_echo():
    cognition = StubCognition()
    assert cognition.respond("Explique-moi quelque chose de compliqué", context()) == "Oui, je t'écoute."
