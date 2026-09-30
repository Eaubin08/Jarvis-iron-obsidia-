"""Physical smoke for Qwen-VL over the full Windows virtual desktop."""
from __future__ import annotations

from jarvis.contracts import ContextSnapshot
from jarvis.integrations.live_environment_timeline import LiveEnvironmentTimeline
from jarvis.integrations.local_vision_cognition import from_environment
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.monitor_layout import WindowsMonitorProvider


def main() -> int:
    timeline = LiveEnvironmentTimeline(
        monitor_provider=WindowsMonitorProvider(),
        visual_driver=PyAutoGUIVisualDriver(),
    )
    vision = from_environment(live_timeline=timeline)
    vision.max_images = 1
    vision.max_tokens = 48
    vision.screen_max_dimension = 1280

    print(
        "VISION_SCREEN_SMOKE: "
        f"endpoint={vision.endpoint} model={vision.model} "
        f"screen_max_dimension={vision.screen_max_dimension}"
    )
    try:
        answer = vision.respond(
            (
                "En une phrase courte, décris uniquement ce qui est réellement visible "
                "sur mon bureau Windows actuel, en tenant compte des écrans fournis."
            ),
            ContextSnapshot("physical dual-screen vision smoke"),
        )
    except Exception as exc:
        print(f"VISION_SCREEN_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    print("VISION_SCREEN_RESPONSE_BEGIN")
    print(answer)
    print("VISION_SCREEN_RESPONSE_END")
    print("VISION_SCREEN_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
