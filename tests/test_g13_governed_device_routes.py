from jarvis.actions import ActionRouter
from jarvis.capabilities import LocalCapabilityRegistry
from jarvis.contracts import Capability, ContextSnapshot
from jarvis.core import JarvisCore
from jarvis.fast_intent import FastIntentRouter
from jarvis.local_actions import KX108OnlyLivePermissionPolicy
from jarvis.providers.local_stub import StubCognition, StubMemory


class _NeverBackend:
    name = "never"
    priority = 0

    def can_execute(self, request, capability):
        raise AssertionError("local mutating backend must not be reached")

    def execute(self, request):
        raise AssertionError("local mutating backend must not execute")


class _Handler:
    def __init__(self, capability, reply):
        self.capability = capability
        self.reply = reply
        self.seen = []

    def handle_request(self, request, *, session_id, original_text):
        self.seen.append((request.capability, dict(request.arguments), original_text))
        if request.capability == self.capability:
            return self.reply
        return None


class _MoveHandler:
    def __init__(self):
        self.calls = []

    def handle(self, text, *, session_id):
        self.calls.append(text)
        if text.casefold().startswith("deplace"):
            return "filesystem move intercepted"
        return None


def _core(**handlers):
    registry = LocalCapabilityRegistry()
    for name in (
        "app.open",
        "window.focus",
        "window.minimize",
        "window.maximize",
        "window.restore",
        "window.move_monitor",
        "media.play_pause",
        "media.next",
        "media.previous",
        "wifi.enable",
        "wifi.disable",
        "bluetooth.enable",
        "bluetooth.disable",
    ):
        registry.register(Capability(name, "windows"))

    return JarvisCore(
        StubCognition(),
        StubMemory(),
        fast_intent=FastIntentRouter(),
        actions=ActionRouter(
            registry=registry,
            permission_policy=KX108OnlyLivePermissionPolicy(),
            backends=[_NeverBackend()],
        ),
        **handlers,
    )


def test_g13_fast_intent_canonical_device_phrases():
    router = FastIntentRouter()
    expected = {
        "Ouvre bloc note.": "app.open",
        "Focus bloc note.": "window.focus",
        "Reprends la musique.": "media.play_pause",
        "Musique suivante.": "media.next",
        "Musique précédente.": "media.previous",
        "Active le Wi-Fi.": "wifi.enable",
        "Déactive le Wi-Fi.": "wifi.disable",
        "Active le Bluetooth.": "bluetooth.enable",
        "Minimise bloc note.": "window.minimize",
        "Maximise bloc note.": "window.maximize",
        "Restaure bloc note.": "window.restore",
        "Déplace bloc note sur écran 2.": "window.move_monitor",
    }
    for utterance, capability in expected.items():
        match = router.route(utterance)
        assert match is not None, utterance
        assert match.request.capability == capability, utterance


def test_g13_media_routes_to_governed_handler():
    media = _Handler("media.next", "Piste suivante exécutée. KX108_PRE=ALLOW.")
    core = _core(governed_media=media)

    reply = core.handle_text("Musique suivante.")

    assert reply == "Piste suivante exécutée. KX108_PRE=ALLOW."
    assert core.last_source == "OBSIDIA/GOVERNED_MEDIA"
    assert media.seen[0][0] == "media.next"


def test_g13_connectivity_routes_to_governed_handler():
    conn = _Handler("bluetooth.enable", "BLUETOOTH activé. KX108_PRE=ALLOW.")
    core = _core(governed_connectivity=conn)

    reply = core.handle_text("Active le Bluetooth.")

    assert reply == "BLUETOOTH activé. KX108_PRE=ALLOW."
    assert core.last_source == "OBSIDIA/GOVERNED_CONNECTIVITY"
    assert conn.seen[0][0] == "bluetooth.enable"


def test_g13_window_state_routes_to_governed_handler():
    window = _Handler(
        "window.minimize",
        "Fenêtre minimisée : Bloc-notes. KX108_PRE=ALLOW. État réel vérifié.",
    )
    core = _core(governed_window_control=window)

    reply = core.handle_text("Minimise bloc note.")

    assert "Fenêtre minimisée" in reply
    assert core.last_source == "OBSIDIA/GOVERNED_WINDOW_CONTROL"
    assert window.seen[0][0] == "window.minimize"


def test_g13_monitor_move_preempts_filesystem_move_parser():
    move = _MoveHandler()
    window = _Handler(
        "window.move_monitor",
        "Fenêtre déplacée : Bloc-notes. KX108_PRE=ALLOW. État réel vérifié.",
    )
    core = _core(governed_move=move, governed_window_control=window)

    reply = core.handle_text("Déplace bloc note sur écran 2.")

    assert "Fenêtre déplacée" in reply
    assert core.last_source == "OBSIDIA/GOVERNED_WINDOW_CONTROL"
    assert window.seen[0][0] == "window.move_monitor"
    assert move.calls == []


def test_g13_bluetooth_capabilities_are_local_and_truthful():
    core = _core()

    reply = core.handle_text("Quelles sont tes possibilités avec le Bluetooth ?")

    assert core.last_source == "LOCAL/CAPABILITIES"
    assert "lire son état" in reply
    assert "l'activer et le désactiver" in reply
    assert "transfert de fichiers" in reply
    assert "pas encore" in reply
