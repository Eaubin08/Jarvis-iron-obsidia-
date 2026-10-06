from jarvis.cockpit_bridge import CockpitRuntime, _verdict
from jarvis.hud_controller import HUDController
from jarvis.hud_state import HUDModel


def test_cockpit_status_is_projection_only():
    model = HUDModel()
    controller = HUDController(model, lambda text: f"reply:{text}", response_source=lambda: "LOCAL")
    runtime = CockpitRuntime(controller)

    result = runtime.submit_text("bonjour")
    status = result["status"]

    assert result["reply"] == "reply:bonjour"
    assert status["authority"] == "NONE"
    assert status["decision_authority"] == "KX108_ONLY"
    assert status["last_transcript"] == "bonjour"
    assert status["last_response"] == "reply:bonjour"
    assert status["response_source"] == "LOCAL"
    assert status["action_verdict"] == "NONE"


def test_cockpit_verdict_fails_closed_from_governance_surface():
    assert _verdict({"state": "idle", "governance_active": True, "governance_phase": "PREPARE"}) == "HOLD"
    assert _verdict({"state": "idle", "governance_active": True, "governance_phase": "EXECUTE"}) == "ACT"
    assert _verdict({"state": "idle", "governance_active": True, "governance_phase": "BLOCKED"}) == "BLOCK"
    assert _verdict({"state": "error", "governance_active": False}) == "BLOCK"


def test_capability_surface_never_grants_authority():
    runtime = CockpitRuntime(HUDController(HUDModel(), lambda text: text))
    packet = runtime.capabilities()
    assert packet["authority"] == "NONE"
    assert packet["decision_authority"] == "KX108_ONLY"
    assert all(row["authority"] == "NONE" for row in packet["families"])
