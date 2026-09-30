from jarvis.cognition_bridge import GovernedCognitionBridge
from jarvis.providers.local_stub import StubCognition, StubMemory


class Stack:
    def __init__(self, answer="stack answer", fail=False):
        self.answer = answer
        self.fail = fail
        self.calls = []

    def respond(self, user_input, context):
        self.calls.append(user_input)
        if self.fail:
            raise RuntimeError("offline")
        return self.answer


def context():
    return StubMemory().context()


def test_presence_stays_local_without_calling_stack():
    stack = Stack()
    bridge = GovernedCognitionBridge(StubCognition(), stack)
    assert bridge.respond("Hey Jarvis", context()) == "Oui ?"
    assert stack.calls == []


def test_unknown_request_goes_to_governed_stack():
    stack = Stack("La réponse vient de la stack.")
    bridge = GovernedCognitionBridge(StubCognition(), stack)
    assert bridge.respond("Explique la gravité", context()) == "La réponse vient de la stack."
    assert stack.calls == ["Explique la gravité"]


def test_stack_failure_degrades_to_local_presence():
    stack = Stack(fail=True)
    bridge = GovernedCognitionBridge(StubCognition(), stack)
    assert bridge.respond("Question inconnue", context()) == "Oui, je t'écoute."
