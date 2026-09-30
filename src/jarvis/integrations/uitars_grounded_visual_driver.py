"""Semantic visual fallback using a UI-TARS-compatible grounding provider."""
from __future__ import annotations

from jarvis.contracts import ActionRequest
from jarvis.visual_grounding import VisualGroundingProvider, parse_click_action


class UITARSGroundedVisualDriver:
    def __init__(self, *, physical_driver, grounding_provider: VisualGroundingProvider):
        self.physical_driver = physical_driver
        self.grounding_provider = grounding_provider

    def snapshot(self) -> dict:
        return self.physical_driver.snapshot()

    def execute(self, request: ActionRequest, state: dict) -> dict:
        if request.capability != "visual.semantic_click":
            raise ValueError(f"unsupported grounded visual capability: {request.capability}")

        instruction = request.arguments.get("description")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("visual.semantic_click requires a description")

        screenshot_path = state.get("screenshot_path")
        width = state.get("width")
        height = state.get("height")
        if not isinstance(screenshot_path, str) or not screenshot_path:
            raise ValueError("fresh screenshot path missing")
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("fresh screenshot dimensions missing")

        raw = self.grounding_provider.ground(
            screenshot_path=screenshot_path,
            instruction=instruction.strip(),
        )
        action = parse_click_action(raw, image_width=width, image_height=height)

        click_request = ActionRequest(
            capability="visual.click",
            arguments={"x": action.x, "y": action.y, "description": instruction.strip()},
            source=request.source,
            session_id=request.session_id,
            task_id=request.task_id,
            risk=request.risk,
            idempotency_key=request.idempotency_key,
        )
        data = self.physical_driver.execute(click_request, state)
        return {
            **data,
            "grounding_action": action.action_type,
            "grounding_raw": raw,
        }
