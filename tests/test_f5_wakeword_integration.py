import os
from pathlib import Path

import pytest

from jarvis.integrations.openwakeword_provider import OpenWakeWordProvider


MODEL_ENV = "JARVIS_WAKEWORD_MODEL_PATH"


@pytest.mark.skipif(
    not os.environ.get(MODEL_ENV),
    reason=f"{MODEL_ENV} must point to an explicitly supplied wake-word model",
)
def test_real_openwakeword_model_loads_and_scores_pcm16_silence():
    model_path = Path(os.environ[MODEL_ENV]).expanduser().resolve()
    assert model_path.is_file(), f"wake-word model not found: {model_path}"

    provider = OpenWakeWordProvider(model_path, threshold=0.5)
    detected = provider.detect(b"\x00\x00" * 1280)

    assert isinstance(detected, bool)
