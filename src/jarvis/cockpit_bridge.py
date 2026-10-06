"""Local cockpit bridge for the canonical Jarjar live runtime.

This is a control/projection surface only:
- it delegates text/voice turns to HUDController;
- it never grants action authority;
- physical observation is explicit and readonly;
- KX108 remains the only decision authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .hud_controller import HUDController
from .monitor_layout import WindowsMonitorProvider
from .physical_probe import run_physical_probe
from .runtime_profile import run_canonical_preflight


COCKPIT_HOST = os.getenv("JARJAR_COCKPIT_HOST", "127.0.0.1")
COCKPIT_PORT = int(os.getenv("JARJAR_COCKPIT_PORT", "47822"))

LIVE_CAPABILITIES = {
    "APP": ("app.open",),
    "WINDOW": (
        "window.list", "window.focus", "window.close", "window.minimize",
        "window.maximize", "window.restore", "window.move_monitor",
    ),
    "AUDIO": (
        "audio.volume_up", "audio.volume_down", "audio.mute_toggle",
        "audio.status", "audio.set_volume", "audio.adjust_volume", "audio.set_mute",
    ),
    "MEDIA": ("media.play_pause", "media.next", "media.previous"),
    "CONNECTIVITY": (
        "wifi.status", "wifi.enable", "wifi.disable",
        "bluetooth.status", "bluetooth.enable", "bluetooth.disable",
    ),
    "FILESYSTEM": (
        "file.open", "file.reveal", "folder.create",
        "file.copy", "file.move", "file.delete",
    ),
    "SYSTEM": ("system.status", "system.battery"),
}
AUXILIARY_SURFACES = {
    "VOICE": {"wired": True, "authority": "NONE"},
    "VISION": {"wired": True, "authority": "NONE"},
    "PERCEPTION": {"wired": True, "authority": "NONE"},
    "BROWSER": {"wired": False, "authority": "NONE", "note": "backend present; not registered in canonical live ActionRouter"},
    "UIA": {"wired": False, "authority": "NONE", "note": "integration present; canonical live controller currently uses Win32Driver"},
    "OPENJARVIS": {"wired": False, "authority": "NONE", "note": "external capability donor / later fusion"},
}


def _verdict(snapshot: dict[str, Any]) -> str:
    phase = str(snapshot.get("governance_phase") or "").upper()
    if phase == "BLOCKED" or snapshot.get("state") == "error":
        return "BLOCK"
    if phase in {"EXECUTE", "ROLLBACK_EXECUTE"}:
        return "ACT"
    if snapshot.get("governance_active") or snapshot.get("human_confirmation_required"):
        return "HOLD"
    return "NONE"


def _last_message(snapshot: dict[str, Any], speaker_prefix: str) -> str:
    for row in reversed(snapshot.get("messages") or []):
        if str(row.get("speaker") or "").startswith(speaker_prefix):
            return str(row.get("text") or "")
    return ""


def _obsidia_health() -> dict[str, Any]:
    candidates = (
        "http://127.0.0.1:8012/api/status",
        "http://127.0.0.1:8000/api/status",
    )
    for url in candidates:
        try:
            request = Request(url, method="GET")
            with urlopen(request, timeout=0.45) as response:
                return {"reachable": True, "url": url, "http_status": response.status}
        except Exception:
            continue
    return {"reachable": False, "url": None, "http_status": None}


def _screen_health() -> dict[str, Any]:
    try:
        layout = WindowsMonitorProvider().layout()
        return {
            "ready": True,
            "count": len(layout.monitors),
            "monitors": [
                {
                    "id": m.monitor_id, "width": m.width, "height": m.height,
                    "left": m.left, "top": m.top, "primary": m.primary,
                }
                for m in layout.monitors
            ],
        }
    except Exception as exc:
        return {"ready": False, "count": 0, "error": f"{type(exc).__name__}:{exc}"}


@dataclass
class CockpitRuntime:
    controller: HUDController
    turn_lock: threading.Lock = field(default_factory=threading.Lock)
    _preflight_cache: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _preflight_at: float = field(default=0.0, init=False, repr=False)

    def _canonical_environment(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._preflight_cache is None or now - self._preflight_at > 15.0:
            self._preflight_cache = run_canonical_preflight(require_qwen=False).as_dict()
            self._preflight_at = now
        return self._preflight_cache

    def status(self) -> dict[str, Any]:
        snap = self.controller.model.snapshot()
        source = ""
        if self.controller.response_source is not None:
            try:
                source = self.controller.response_source().strip()
            except Exception:
                source = ""
        return {
            "schema": "JARJAR_COCKPIT_STATUS_V0",
            "runtime": "RUNNING" if snap.get("state") != "error" else "DEGRADED",
            "pid": os.getpid(),
            "authority": "NONE",
            "decision_authority": "KX108_ONLY",
            "hud": snap,
            "last_transcript": _last_message(snap, "YOU"),
            "last_response": _last_message(snap, "JARJAR"),
            "response_source": source,
            "action_verdict": _verdict(snap),
        }

    def health(self) -> dict[str, Any]:
        snap = self.controller.model.snapshot()
        return {
            "schema": "JARJAR_COCKPIT_HEALTH_V0",
            "jarjar_alive": True,
            "pid": os.getpid(),
            "authority": "NONE",
            "decision_authority": "KX108_ONLY",
            "voice_ready": bool(snap.get("voice_enabled")),
            "micro_ready": bool(snap.get("voice_enabled")),
            "obsidia": _obsidia_health(),
            "kx108_ready": True if snap.get("decision_authority") == "KX108_ONLY" else None,
            "kx108_note": "confirmed by active governed surface" if snap.get("decision_authority") == "KX108_ONLY" else "no canonical standalone KX108 health endpoint exposed",
            "screens": _screen_health(),
            "canonical_environment": self._canonical_environment(),
        }

    def capabilities(self) -> dict[str, Any]:
        return {
            "schema": "JARJAR_COCKPIT_CAPABILITIES_V0",
            "authority": "NONE",
            "decision_authority": "KX108_ONLY",
            "families": [
                {"family": family, "wired": True, "capabilities": list(values), "authority": "NONE"}
                for family, values in LIVE_CAPABILITIES.items()
            ] + [
                {"family": family, **data, "capabilities": []}
                for family, data in AUXILIARY_SURFACES.items()
            ],
        }

    def submit_text(self, text: str) -> dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise ValueError("empty cockpit text input")
        with self.turn_lock:
            reply = self.controller.submit_text(clean)
        return {"ok": True, "reply": reply, "status": self.status()}

    def toggle_voice(self) -> dict[str, Any]:
        with self.turn_lock:
            enabled = self.controller.toggle_voice()
        return {"ok": True, "voice_enabled": enabled, "status": self.status()}

    def listen_once(self) -> dict[str, Any]:
        with self.turn_lock:
            result = self.controller.run_voice_turn()
            if result is not None:
                self.controller.voice_finished()
        return {"ok": True, "turn": result, "status": self.status()}

    def observe(self) -> dict[str, Any]:
        # Explicit readonly probe. It may capture screen/camera evidence files,
        # but it cannot mutate Windows state or authorize actions.
        result = run_physical_probe()
        return {"ok": True, "observation": result}


class _Handler(BaseHTTPRequestHandler):
    runtime: CockpitRuntime

    def log_message(self, *_args) -> None:
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0") or 0)
        if size > 16384:
            raise ValueError("request too large")
        raw = self.rfile.read(size) if size else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def do_GET(self) -> None:
        try:
            if self.path == "/status":
                self._send(200, self.runtime.status())
            elif self.path == "/health":
                self._send(200, self.runtime.health())
            elif self.path == "/capabilities":
                self._send(200, self.runtime.capabilities())
            else:
                self._send(404, {"error": "route not found"})
        except Exception as exc:
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

    def do_POST(self) -> None:
        try:
            if self.path == "/text":
                body = self._body()
                self._send(200, self.runtime.submit_text(str(body.get("text") or "")))
            elif self.path == "/voice/toggle":
                self._send(200, self.runtime.toggle_voice())
            elif self.path == "/voice/listen":
                self._send(200, self.runtime.listen_once())
            elif self.path == "/observe":
                self._send(200, self.runtime.observe())
            else:
                self._send(404, {"error": "route not found"})
        except ValueError as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": f"{type(exc).__name__}: {exc}"})


def start_cockpit_server(controller: HUDController, host: str = COCKPIT_HOST, port: int = COCKPIT_PORT) -> ThreadingHTTPServer:
    runtime = CockpitRuntime(controller)

    class BoundHandler(_Handler):
        pass

    BoundHandler.runtime = runtime
    server = ThreadingHTTPServer((host, port), BoundHandler)
    thread = threading.Thread(target=server.serve_forever, name="jarjar-cockpit-http", daemon=True)
    thread.start()
    print(f"JARJAR_COCKPIT: READY http://{host}:{port}")
    return server
