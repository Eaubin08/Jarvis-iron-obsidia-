"""Physical end-to-end route smoke for Jarjar cognition/action boundaries."""
from __future__ import annotations

from jarvis.actions import ActionRouter
from jarvis.capabilities import LocalCapabilityRegistry
from jarvis.camera_rig import CameraRig
from jarvis.cognition_bridge import CostAwareCognitionRouter
from jarvis.contracts import Capability
from jarvis.fast_intent import FastIntentRouter
from jarvis.integrations.live_environment_timeline import LiveEnvironmentTimeline
from jarvis.integrations.local_qwen_cognition import from_environment as qwen_from_environment
from jarvis.integrations.local_vision_cognition import from_environment as vision_from_environment
from jarvis.integrations.obsidia_stack_cognition import from_environment as brody_from_environment
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.local_actions import LocalPermissionPolicy, SystemBackend
from jarvis.monitor_layout import WindowsMonitorProvider
from jarvis.providers.local_stub import StubCognition, StubMemory
from jarvis.runtime import TextRuntime


def _assert_route(router, expected: str, label: str) -> None:
    actual = router.last_route
    print(f"ROUTE_{label}: {actual}")
    if actual != expected:
        raise RuntimeError(f"{label} expected route={expected}, got {actual}")


def main() -> int:
    camera_rig = CameraRig.from_device_indices((0, 1))
    camera_rig.enable_all(permission_granted=True)

    timeline = LiveEnvironmentTimeline(
        monitor_provider=WindowsMonitorProvider(),
        camera_rig=camera_rig,
        visual_driver=PyAutoGUIVisualDriver(),
    )

    qwen = qwen_from_environment(live_timeline=timeline)
    vision = vision_from_environment(live_timeline=timeline)
    vision.max_images = 1
    vision.max_tokens = 48

    brody = brody_from_environment()
    router = CostAwareCognitionRouter(
        local_presence=StubCognition(),
        governed_stack=brody,
        qwen=qwen,
        vision=vision,
    )

    try:
        general = router.respond(
            "Pourquoi le ciel paraît-il bleu ?",
            StubMemory().context(),
        )
        _assert_route(router, "qwen", "GENERAL")
        print("GENERAL_RESPONSE:", general[:220].replace("\n", " "))

        visual = router.respond(
            "Décris en une phrase courte ce que tu vois sur mon écran.",
            StubMemory().context(),
        )
        _assert_route(router, "vision", "VISUAL")
        print("VISUAL_RESPONSE:", visual[:220].replace("\n", " "))

        project = router.respond(
            "Explique brièvement ce qu'est Obsidia dans ce projet.",
            StubMemory().context(),
        )
        _assert_route(router, "brody", "OBSIDIA")
        print("OBSIDIA_RESPONSE:", project[:220].replace("\n", " "))

        registry = LocalCapabilityRegistry()
        registry.register(
            Capability(
                name="system.status",
                backend_family="system",
                description="read-only Jarvis status",
            )
        )
        actions = ActionRouter(
            registry=registry,
            permission_policy=LocalPermissionPolicy(),
            backends=[SystemBackend()],
        )
        runtime = TextRuntime(
            cognition=router,
            memory=StubMemory(),
            fast_intent=FastIntentRouter(),
            actions=actions,
        )
        command = runtime.handle("Jarvis status")
        print("ROUTE_ACTION: action_router")
        print("ACTION_RESPONSE:", command)
        if command != "JARVIS_IRON_STATUS: READY":
            raise RuntimeError(f"unexpected action result: {command}")

    except Exception as exc:
        print(f"JARJAR_ROUTE_E2E: FAIL {type(exc).__name__}: {exc}")
        return 2

    print("JARJAR_ROUTE_E2E: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
