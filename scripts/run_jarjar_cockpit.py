"""Launch canonical Jarjar HUD plus the local cockpit bridge."""
from __future__ import annotations

from jarvis.cockpit_bridge import start_cockpit_server
from jarvis.hud_app import run_hud
from jarvis.live_runtime import build_live_controller
from jarvis.runtime_profile import require_canonical_preflight


def main() -> None:
    preflight = require_canonical_preflight()
    print("JARJAR_BOOT: canonical environment accepted")
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
