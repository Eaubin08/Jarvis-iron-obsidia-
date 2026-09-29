from jarvis.capabilities import LocalCapabilityRegistry
from jarvis.contracts import ActionRequest, Capability
from jarvis.fast_intent import FastIntentRouter


def test_exact_status_command_routes_without_cognition():
    match = FastIntentRouter().route("  JARVIS   STATUS ", session_id="s2")
    assert match is not None
    assert match.rule == "status"
    assert match.request.capability == "system.status"
    assert match.request.source == "fast_intent"
    assert match.request.session_id == "s2"


def test_ambiguous_free_text_does_not_fake_confidence():
    assert FastIntentRouter().route("what is the status of my project?") is None


def test_empty_input_does_not_route():
    assert FastIntentRouter().route("   ") is None


def test_registry_resolves_only_registered_capability():
    registry = LocalCapabilityRegistry()
    registry.register(Capability("system.status", "native"))
    assert registry.resolve(ActionRequest("system.status")).backend_family == "native"
    assert registry.resolve(ActionRequest("unknown")) is None


def test_duplicate_capability_registration_is_rejected():
    registry = LocalCapabilityRegistry()
    registry.register(Capability("system.status", "native"))
    try:
        registry.register(Capability("system.status", "visual"))
    except ValueError:
        pass
    else:
        raise AssertionError("expected duplicate registration to fail")
