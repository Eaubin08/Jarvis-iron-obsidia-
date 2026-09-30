"""UI-TARS-inspired visual grounding seam.

This module adapts only the donor's action/coordinate contract. It does not
adopt the donor agent loop and never executes generated Python code.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Protocol


IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
MAX_PIXELS = 16384 * 28 * 28
MAX_RATIO = 200


@dataclass(frozen=True)
class GroundedAction:
    action_type: str
    x: int | None = None
    y: int | None = None
    raw: str = ""


class VisualGroundingProvider(Protocol):
    def ground(self, *, screenshot_path: str, instruction: str) -> str: ...


def _round_by_factor(number: int, factor: int) -> int:
    return round(number / factor) * factor


def _ceil_by_factor(number: int, factor: int) -> int:
    return math.ceil(number / factor) * factor


def _floor_by_factor(number: int, factor: int) -> int:
    return math.floor(number / factor) * factor


def smart_resize(
    height: int,
    width: int,
    *,
    factor: int = IMAGE_FACTOR,
    min_pixels: int = MIN_PIXELS,
    max_pixels: int = MAX_PIXELS,
) -> tuple[int, int]:
    if height <= 0 or width <= 0:
        raise ValueError("image dimensions must be positive")
    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError("image aspect ratio is too large")

    h = max(factor, _round_by_factor(height, factor))
    w = max(factor, _round_by_factor(width, factor))
    if h * w > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h = _floor_by_factor(height / beta, factor)
        w = _floor_by_factor(width / beta, factor)
    elif h * w < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h = _ceil_by_factor(height * beta, factor)
        w = _ceil_by_factor(width * beta, factor)
    return h, w


def parse_click_action(
    response: str,
    *,
    image_width: int,
    image_height: int,
) -> GroundedAction:
    """Parse one UI-TARS click and reproject it to original screenshot pixels."""

    if not isinstance(response, str) or not response.strip():
        raise ValueError("empty grounding response")

    action_match = re.search(r"Action:\s*click\(", response)
    if not action_match:
        raise ValueError("grounding response is not a click action")

    # UI-TARS coordinate payloads can contain their own parentheses, e.g.
    # click(start_box='(483,273)'). Slice from the opening click instead of
    # using a non-greedy regex that stops at the coordinate's closing ')'.
    body = response[action_match.end():].strip()
    if body.endswith(")"):
        body = body[:-1].rstrip()
    point_match = re.search(r"<point>\s*(\d+)\s+(\d+)\s*</point>", body)
    box_match = re.search(
        r"(?:start_box|point)\s*=\s*['\"]\(\s*(\d+)\s*,\s*(\d+)\s*\)['\"]",
        body,
    )
    if point_match:
        model_x, model_y = map(int, point_match.groups())
    elif box_match:
        model_x, model_y = map(int, box_match.groups())
    else:
        raise ValueError("click action has no supported point coordinates")

    resized_h, resized_w = smart_resize(image_height, image_width)
    if not (0 <= model_x < resized_w and 0 <= model_y < resized_h):
        raise ValueError("grounded coordinates are outside resized image bounds")

    x = int(model_x / resized_w * image_width)
    y = int(model_y / resized_h * image_height)
    x = min(max(x, 0), image_width - 1)
    y = min(max(y, 0), image_height - 1)
    return GroundedAction("click", x=x, y=y, raw=response)
