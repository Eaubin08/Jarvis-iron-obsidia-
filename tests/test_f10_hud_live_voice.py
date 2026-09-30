from jarvis.hud_live_runtime import HUDLiveVoiceBridge


class FakeIngress:
    def __init__(self, *, first="hey jarvis status", follow="continue"):
        self.first = first
        self.follow = follow
        self.calls = []

    def capture_and_begin_turn(self, duration):
        self.calls.append(("wake", duration))
        return self.first

    def capture_follow_up(self, duration):
        self.calls.append(("follow", duration))
        return self.follow


class FakeCore:
    def __init__(self):
        self.inputs = []

    def handle_text(self, text):
        self.inputs.append(text)
        return f"reply:{text}"


class Handle:
    def __init__(self):
        self.waited = False

    def wait(self, timeout):
        self.waited = True


class FakeConversation:
    def __init__(self):
        self.follow_up_open = False
        self.spoken = []
        self.finished = 0

    def speak(self, text, *, open_follow_up=True):
        self.spoken.append(text)
        self.follow_up_open = open_follow_up
        return Handle()

    def speech_finished(self):
        self.finished += 1


def test_first_hud_voice_turn_requires_wake_path():
    ingress = FakeIngress()
    core = FakeCore()
    conversation = FakeConversation()
    bridge = HUDLiveVoiceBridge(ingress, core, conversation, capture_seconds=4.0)

    result = bridge.run_turn()

    assert result == ("hey jarvis status", "reply:hey jarvis status")
    assert ingress.calls == [("wake", 4.0)]
    assert conversation.spoken == ["reply:hey jarvis status"]
    assert conversation.finished == 1


def test_follow_up_uses_wake_free_capture():
    ingress = FakeIngress()
    core = FakeCore()
    conversation = FakeConversation()
    conversation.follow_up_open = True
    bridge = HUDLiveVoiceBridge(ingress, core, conversation)

    result = bridge.run_turn()

    assert result == ("continue", "reply:continue")
    assert ingress.calls == [("follow", 5.0)]


def test_missing_wake_returns_none_without_speaking():
    ingress = FakeIngress(first=None)
    core = FakeCore()
    conversation = FakeConversation()
    bridge = HUDLiveVoiceBridge(ingress, core, conversation)

    assert bridge.run_turn() is None
    assert core.inputs == []
    assert conversation.spoken == []
