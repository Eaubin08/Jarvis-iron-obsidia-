"""Readonly physical-device probe for Jarjar G13/F12.

The probe observes hardware/runtime availability only. It never clicks, types,
moves windows, toggles radios, changes volume, or invokes governed actions.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

from jarvis.camera_rig import CameraRig
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.integrations.win32_driver import Win32Driver
from jarvis.monitor_layout import WindowsMonitorProvider


@dataclass(frozen=True)
class ProbeItem:
    name: str
    ok: bool
    data: dict[str, Any]
    error: str | None = None


def _probe(name: str, fn: Callable[[], dict[str, Any]]) -> ProbeItem:
    try:
        data = fn()
        return ProbeItem(name=name, ok=True, data=data)
    except Exception as exc:
        return ProbeItem(
            name=name,
            ok=False,
            data={},
            error=f"{type(exc).__name__}:{exc}",
        )


def run_physical_probe(
    *,
    camera_indices: tuple[int, ...] = (0, 1),
    evidence_dir: str | Path = "runtime_data/g13_physical_probe",
) -> dict[str, Any]:
    root = Path(evidence_dir)
    root.mkdir(parents=True, exist_ok=True)

    monitors = WindowsMonitorProvider()
    windows = Win32Driver()
    visual = PyAutoGUIVisualDriver(
        evidence_dir=root / "screen",
        monitor_provider=monitors,
    )

    items: list[ProbeItem] = []

    def monitor_probe() -> dict[str, Any]:
        layout = monitors.layout()
        return {
            "count": len(layout.monitors),
            "virtual_desktop": {
                "left": layout.left,
                "top": layout.top,
                "right": layout.right,
                "bottom": layout.bottom,
                "width": layout.width,
                "height": layout.height,
            },
            "monitors": [
                {
                    "monitor_id": m.monitor_id,
                    "width": m.width,
                    "height": m.height,
                    "left": m.left,
                    "top": m.top,
                    "primary": m.primary,
                }
                for m in layout.monitors
            ],
        }

    items.append(_probe("monitors", monitor_probe))
    items.append(_probe("screen_snapshot", visual.snapshot))
    items.append(_probe("windows", windows.list_windows))
    items.append(_probe("audio", windows.audio_status))
    items.append(_probe("wifi", windows.wifi_status))
    items.append(_probe("bluetooth", windows.bluetooth_status))

    for index in camera_indices:
        rig = CameraRig.from_device_indices((index,))
        rig.enable_all(permission_granted=True)

        def camera_probe(rig=rig, index=index) -> dict[str, Any]:
            observation = rig.snapshot_all()[f"camera-{index}"]
            return {
                "camera_id": f"camera-{index}",
                "enabled": observation.enabled,
                "provider": observation.provider,
                "text": observation.text,
                "metadata": observation.metadata,
            }

        items.append(_probe(f"camera_{index}", camera_probe))

    result = {
        "schema": "JARJAR_G13_PHYSICAL_PROBE_V1",
        "readonly": True,
        "action_authority": "NONE",
        "decision_authority": "KX108_ONLY",
        "items": [
            {
                "name": item.name,
                "ok": item.ok,
                "data": item.data,
                "error": item.error,
            }
            for item in items
        ],
    }
    result["pass_count"] = sum(1 for item in items if item.ok)
    result["fail_count"] = sum(1 for item in items if not item.ok)
    result["overall_ok"] = result["fail_count"] == 0

    out = root / "g13_physical_probe.json"
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    result["evidence_file"] = str(out)
    return result


def format_probe_summary(result: dict[str, Any]) -> str:
    rows = [
        "G13/F12 PHYSICAL PROBE",
        f"readonly={result.get('readonly')}",
        f"decision_authority={result.get('decision_authority')}",
        f"pass={result.get('pass_count')} fail={result.get('fail_count')}",
    ]
    for item in result.get("items", []):
        state = "PASS" if item.get("ok") else "FAIL"
        detail = ""
        if item.get("name") == "monitors" and item.get("ok"):
            detail = f" count={item.get('data', {}).get('count')}"
        elif item.get("name") == "windows" and item.get("ok"):
            detail = f" count={len(item.get('data', {}).get('windows', []))}"
        elif item.get("name", "").startswith("camera_") and item.get("ok"):
            meta = item.get("data", {}).get("metadata", {})
            detail = f" {meta.get('width')}x{meta.get('height')}"
        elif not item.get("ok"):
            detail = f" {item.get('error')}"
        rows.append(f"{item.get('name')}: {state}{detail}")
    rows.append(f"evidence={result.get('evidence_file')}")
    return "\n".join(rows)
