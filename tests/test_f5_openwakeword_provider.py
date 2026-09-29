import sys
import types

import pytest

from jarvis.integrations.openwakeword_provider import OpenWakeWordProvider


class FakeArray:
    dtype = "<i2"


class FakeNumpy(types.ModuleType):
    def __init__(self):
        super().__init__("numpy")
        self.calls = []

    def frombuffer(self, audio, dtype):
        self.calls.append((audio, dtype))
        return FakeArray()


class FakeModel:
    created = []
    next_scores = {"custom_model": 0.0}

    def __init__(self, *, wakeword_models, inference_framework):
        self.created.append((wakeword_models, inference_framework))

    def predict(self, pcm):
        assert isinstance(pcm, FakeArray)
        return dict(self.next_scores)


def install_fakes(monkeypatch):
    numpy_module = FakeNumpy()
    monkeypatch.setitem(sys.modules, "numpy", numpy_module)

    package = types.ModuleType("openwakeword")
    model_module = types.ModuleType("openwakeword.model")
    model_module.Model = FakeModel
    package.model = model_module
    monkeypatch.setitem(sys.modules, "openwakeword", package)
    monkeypatch.setitem(sys.modules, "openwakeword.model", model_module)
    return numpy_module


def test_provider_requires_explicit_existing_model_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        OpenWakeWordProvider(tmp_path / "missing.onnx")


def test_provider_is_lazy_and_detects_over_threshold(monkeypatch, tmp_path):
    numpy_module = install_fakes(monkeypatch)
    model_path = tmp_path / "jarvis.onnx"
    model_path.write_bytes(b"model")

    FakeModel.created.clear()
    FakeModel.next_scores = {"jarvis": 0.72}

    provider = OpenWakeWordProvider(model_path, threshold=0.5)
    assert FakeModel.created == []

    audio = b"\x00\x00" * 128
    assert provider.detect(audio) is True
    assert numpy_module.calls == [(audio, "<i2")]
    assert FakeModel.created == [([str(model_path.resolve())], "onnx")]


def test_provider_does_not_detect_below_threshold(monkeypatch, tmp_path):
    install_fakes(monkeypatch)
    model_path = tmp_path / "jarvis.onnx"
    model_path.write_bytes(b"model")
    FakeModel.next_scores = {"jarvis": 0.49}

    provider = OpenWakeWordProvider(model_path, threshold=0.5)
    assert provider.detect(b"\x00\x00" * 128) is False


def test_provider_rejects_invalid_audio_before_optional_imports(tmp_path):
    model_path = tmp_path / "jarvis.onnx"
    model_path.write_bytes(b"model")
    provider = OpenWakeWordProvider(model_path)

    with pytest.raises(ValueError):
        provider.detect(b"")
    with pytest.raises(ValueError):
        provider.detect(b"\x00")
