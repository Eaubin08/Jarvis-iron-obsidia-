from jarvis.contracts import ActionRequest, ContextSnapshot, RiskClass
from jarvis.local_actions import KX108OnlyLivePermissionPolicy


def test_g13_live_policy_allows_readonly_only():
    policy = KX108OnlyLivePermissionPolicy()
    context = ContextSnapshot(summary="")

    assert policy.evaluate(
        ActionRequest("wifi.status", risk=RiskClass.READ_ONLY),
        context,
    ).value == "allow"

    for capability in (
        "audio.volume_up",
        "window.minimize",
        "app.open",
        "media.play_pause",
    ):
        assert policy.evaluate(
            ActionRequest(capability, risk=RiskClass.LOW),
            context,
        ).value == "deny"


from jarvis.actions import ActionRouter
from jarvis.capabilities import LocalCapabilityRegistry
from jarvis.contracts import Capability


class _NeverBackend:
    name = "never"
    priority = 0

    def can_execute(self, request, capability):
        raise AssertionError("backend must not be reached for denied mutation")

    def execute(self, request):
        raise AssertionError("backend must not execute")


def test_g13_denied_mutation_surfaces_world_action_dry_run_reason():
    registry = LocalCapabilityRegistry()
    registry.register(Capability("audio.volume_up", "windows"))
    router = ActionRouter(
        registry=registry,
        permission_policy=KX108OnlyLivePermissionPolicy(),
        backends=[_NeverBackend()],
    )
    result = router.execute(
        ActionRequest("audio.volume_up", risk=RiskClass.LOW),
        ContextSnapshot(summary=""),
    )
    assert result.ok is False
    assert result.message == "WORLD_ACTION_DRY_RUN_ONLY"


from jarvis.fast_intent import FastIntentRouter


def test_g13_volume_status_is_readonly_and_not_guarded():
    router = FastIntentRouter()
    match = router.route("Quel est le niveau de volume ?")
    assert match is not None
    assert match.request.capability == "audio.status"
    assert match.request.risk is RiskClass.READ_ONLY
    assert router.local_guard_response("Quel est le niveau de volume ?") is None


def test_g13_volume_status_accepts_natural_followup_phrasing():
    router = FastIntentRouter()
    for utterance in (
        "C'est le niveau de volume.",
        "Et le niveau de volume.",
        "Quel est le niveau de volume de l'ordinateur ?",
        "Le volume est à combien ?",
    ):
        match = router.route(utterance)
        assert match is not None, utterance
        assert match.request.capability == "audio.status", utterance
        assert match.request.risk is RiskClass.READ_ONLY
        assert router.local_guard_response(utterance) is None

    assert router.route("Baisse le volume de 15.").request.capability == "audio.adjust_volume"


from jarvis.windows import NativeWindowsBackend


def test_g13_windows_readonly_reply_surfaces_observed_volume():
    message = NativeWindowsBackend._format_success_message(
        "audio.status",
        {"volume_percent": 37, "muted": False},
    )
    assert message == "Volume actuel : 37 %. Muet : non."
