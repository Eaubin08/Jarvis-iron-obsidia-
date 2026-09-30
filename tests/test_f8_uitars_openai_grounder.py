import base64
from pathlib import Path

import pytest

from jarvis.integrations.uitars_openai_grounder import OpenAICompatibleUITARSGrounder


class FakeGrounder(OpenAICompatibleUITARSGrounder):
    def __init__(self, response):
        super().__init__(base_url="http://127.0.0.1:8000/v1", model="ui-tars")
        self.response = response
        self.calls = []

    def _post_json(self, path, payload):
        self.calls.append((path, payload))
        return self.response


def test_grounder_sends_openai_compatible_multimodal_request(tmp_path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"png-bytes")
    grounder = FakeGrounder({
        "choices": [{"message": {"content": "Action: click(start_box='(100,200)')"}}]
    })

    result = grounder.ground(screenshot_path=str(image), instruction="click Save")

    assert result == "Action: click(start_box='(100,200)')"
    path, payload = grounder.calls[0]
    assert path == "/chat/completions"
    assert payload["model"] == "ui-tars"
    content = payload["messages"][0]["content"]
    assert "click Save" in content[0]["text"]
    encoded = content[1]["image_url"]["url"].split(",", 1)[1]
    assert base64.b64decode(encoded) == b"png-bytes"


def test_grounder_requires_existing_screenshot(tmp_path):
    grounder = FakeGrounder({})
    with pytest.raises(ValueError, match="screenshot not found"):
        grounder.ground(screenshot_path=str(tmp_path / "missing.png"), instruction="click Save")


def test_grounder_fails_closed_on_missing_content(tmp_path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"x")
    grounder = FakeGrounder({"choices": []})
    with pytest.raises(RuntimeError, match="no assistant content"):
        grounder.ground(screenshot_path=str(image), instruction="click Save")


def test_grounder_requires_instruction(tmp_path):
    image = tmp_path / "screen.png"
    image.write_bytes(b"x")
    grounder = FakeGrounder({})
    with pytest.raises(ValueError, match="instruction"):
        grounder.ground(screenshot_path=str(image), instruction=" ")
