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


def test_open_app_strips_french_article_before_resolution():
    match = FastIntentRouter().route("ouvre la calculatrice")
    assert match is not None
    assert match.request.capability == "app.open"
    assert match.request.arguments == {"app": "calculatrice"}


def test_open_app_accepts_generic_installed_app_name():
    match = FastIntentRouter().route("lance spotify")
    assert match is not None
    assert match.request.arguments == {"app": "spotify"}


def test_volume_down_never_cross_matches_volume_up():
    match = FastIntentRouter().route("baisse le volume de 15")
    assert match is not None
    assert match.request.capability == "audio.adjust_volume"
    assert match.request.arguments == {"delta": -15}


def test_volume_up_accepts_observed_stt_noise_and_spoken_number():
    match = FastIntentRouter().route("manque le volume de dix")
    assert match is not None
    assert match.request.capability == "audio.adjust_volume"
    assert match.request.arguments == {"delta": 10}


def test_absolute_volume_accepts_spoken_number():
    match = FastIntentRouter().route("mets le volume a trente")
    assert match is not None
    assert match.request.capability == "audio.set_volume"
    assert match.request.arguments == {"percent": 30}


def test_conflicting_volume_directions_fail_closed():
    router = FastIntentRouter()
    assert router.route("monte le volume baisse le volume") is None
    assert router.local_guard_response("monte le volume baisse le volume") is not None


def test_volume_article_does_not_hide_direction_verb():
    up = FastIntentRouter().route("monte le volume de 10")
    down = FastIntentRouter().route("baisse le volume de 15")
    assert up is not None
    assert up.request.capability == "audio.adjust_volume"
    assert up.request.arguments == {"delta": 10}
    assert down is not None
    assert down.request.capability == "audio.adjust_volume"
    assert down.request.arguments == {"delta": -15}
