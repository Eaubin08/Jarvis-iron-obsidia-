from jarvis.runtime_profile import apply_canonical_environment, run_canonical_preflight


def test_canonical_environment_restores_proven_flags(monkeypatch):
    monkeypatch.delenv("JARJAR_BOUNDED_STRUCTURED_ROUTING_V0", raising=False)
    monkeypatch.delenv("JARJAR_LOCAL_BRODY", raising=False)
    values = apply_canonical_environment()
    assert values["JARJAR_BOUNDED_STRUCTURED_ROUTING_V0"] == "1"
    assert values["JARJAR_LOCAL_BRODY"] == "1"
    assert values["JARJAR_QWEN_URL"].endswith(":8080/v1/chat/completions")
    assert values["JARJAR_VISION_URL"].endswith(":8081/v1/chat/completions")


def test_preflight_fails_closed_when_brody_is_not_canonical(monkeypatch):
    monkeypatch.setattr(
        "jarvis.runtime_profile._probe_local_brody",
        lambda: {
            "ready": False,
            "memory_source_mode": "LOCAL_GRAPHITI_INDEX_FALLBACK",
            "decision_authority": "KX108_ONLY",
            "readonly": True,
        },
    )
    monkeypatch.setattr(
        "jarvis.runtime_profile._probe_openai_models",
        lambda *_args, **_kwargs: {"ready": True},
    )
    result = run_canonical_preflight(require_qwen=False)
    assert result.ok is False
    assert result.brody["memory_source_mode"] == "LOCAL_GRAPHITI_INDEX_FALLBACK"


def test_qwen_can_be_health_signal_without_blocking_canonical_brody(monkeypatch):
    monkeypatch.setattr(
        "jarvis.runtime_profile._probe_local_brody",
        lambda: {
            "ready": True,
            "memory_source_mode": "OBSIDIA_NATIVE_MEMORY",
            "decision_authority": "KX108_ONLY",
            "readonly": True,
        },
    )
    monkeypatch.setattr(
        "jarvis.runtime_profile._probe_openai_models",
        lambda *_args, **_kwargs: {"ready": False},
    )
    assert run_canonical_preflight(require_qwen=False).ok is True
    assert run_canonical_preflight(require_qwen=True).ok is False
