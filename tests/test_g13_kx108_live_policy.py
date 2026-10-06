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
