import pytest

from jarvis.contracts import ActionRequest
from jarvis.integrations.uitars_grounded_visual_driver import UITARSGroundedVisualDriver
from jarvis.visual_grounding import parse_click_action, smart_resize


def test_smart_resize_keeps_ui_tars_factor_contract():
    h, w = smart_resize(1080, 1920)
    assert h % 28 == 0
    assert w % 28 == 0


def test_parse_point_click_reprojects_to_original_pixels():
    h, w = smart_resize(1080, 1920)
    response = f"Action: click(point='<point>{w // 2} {h // 2}</point>')"
    action = parse_click_action(response, image_width=1920, image_height=1080)
    assert abs(action.x - 960) <= 2
    assert abs(action.y - 540) <= 2


def test_parse_start_box_click_reprojects_to_original_pixels():
    h, w = smart_resize(1080, 1920)
    response = f"Thought: target found\nAction: click(start_box='({w // 4},{h // 4})')"
    action = parse_click_action(response, image_width=1920, image_height=1080)
    assert abs(action.x - 480) <= 2
    assert abs(action.y - 270) <= 2


def test_non_click_action_fails_closed():
    with pytest.raises(ValueError, match="not a click"):
        parse_click_action("Action: type(content='hello')", image_width=1920, image_height=1080)


class FakePhysical:
    def __init__(self):
        self.calls = []

    def snapshot(self):
        return {
            "observation_id": "fresh-1",
            "width": 1920,
            "height": 1080,
            "screenshot_path": "fresh.png",
        }

    def execute(self, request, state):
        self.calls.append((request.capability, request.arguments, state["observation_id"]))
        return {"ok": True, "x": request.arguments["x"], "y": request.arguments["y"]}


class FakeGrounder:
    def __init__(self):
        self.calls = []

    def ground(self, *, screenshot_path, instruction):
        self.calls.append((screenshot_path, instruction))
        h, w = smart_resize(1080, 1920)
        return f"Action: click(point='<point>{w // 2} {h // 2}</point>')"


def test_grounded_driver_refreshes_then_converts_semantic_target_to_bounded_click():
    physical = FakePhysical()
    grounder = FakeGrounder()
    driver = UITARSGroundedVisualDriver(
        physical_driver=physical,
        grounding_provider=grounder,
    )
    state = driver.snapshot()
    result = driver.execute(
        ActionRequest("visual.semantic_click", {"description": "click Save"}),
        state,
    )

    assert grounder.calls == [("fresh.png", "click Save")]
    assert physical.calls[0][0] == "visual.click"
    assert abs(result["x"] - 960) <= 2
    assert abs(result["y"] - 540) <= 2
    assert result["grounding_action"] == "click"
