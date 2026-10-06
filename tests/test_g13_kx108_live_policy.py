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
