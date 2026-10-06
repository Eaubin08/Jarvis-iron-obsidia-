"""Launch canonical Jarjar HUD plus the local cockpit bridge.

The cockpit is additive: it must not change or block the proven live runtime.
"""
from __future__ import annotations

from jarvis.cockpit_bridge import start_cockpit_server
from jarvis.hud_app import run_hud
from jarvis.live_runtime import build_live_controller
from jarvis.runtime_profile import apply_canonical_environment


def main() -> None:
    # Restore the proven launch flags, but do not invent a new startup gate.
    apply_canonical_environment()
    print("JARJAR_BOOT: using canonical environment flags")
    print("JARJAR_BOOT: building live controller")
    controller = build_live_controller()
    server = start_cockpit_server(controller)
    print("JARJAR_BOOT: controller ready, launching HUD with cockpit bridge")
    try:
        run_hud(controller)
    finally:
        server.shutdown()
        server.server_close()
        print("JARJAR_COCKPIT: STOPPED")


if __name__ == "__main__":
    main()
