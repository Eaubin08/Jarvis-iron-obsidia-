"""Physical smoke for Jarjar Windows controls.

Safe policy:
- network radios: read real state only; toggles are checked at permission gate,
  never executed by this smoke.
- window actions: open an empty Notepad instance, manipulate only that window,
  then close it.
"""
from __future__ import annotations

import json
import os
import time

from jarvis.contracts import ActionRequest, ContextSnapshot, RiskClass
from jarvis.fast_intent import FastIntentRouter
from jarvis.integrations.win32_driver import Win32Driver
from jarvis.local_actions import LocalPermissionPolicy


def _dump(label: str, value: object) -> None:
    print(f"{label}: {json.dumps(value, ensure_ascii=False, default=str)}")


def _visible_windows() -> dict[int, str]:
    import win32gui

    windows: dict[int, str] = {}

    def collect(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                windows[int(hwnd)] = title
        return True

    win32gui.EnumWindows(collect, None)
    return windows


def _new_window(before: set[int], timeout: float = 8.0) -> tuple[int, str]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        current = _visible_windows()
        created = [
            (hwnd, title)
            for hwnd, title in current.items()
            if hwnd not in before
        ]
        if created:
            # Prefer the newly created Notepad window when Windows 11 launches
            # it through a transient parent/launcher process.
            preferred = [
                (hwnd, title)
                for hwnd, title in created
                if any(
                    token in title.casefold()
                    for token in ("notepad", "bloc-notes", "bloc notes")
                )
            ]
            return (preferred or created)[0]
        time.sleep(0.2)
    raise RuntimeError("no new visible window appeared after app launch")


def main() -> int:
    driver = Win32Driver()
    policy = LocalPermissionPolicy()
    context = ContextSnapshot("physical windows controls smoke")

    try:
        wifi = driver.wifi_status()
        _dump("WIFI_STATUS", wifi)

        bluetooth = driver.bluetooth_status()
        _dump("BLUETOOTH_STATUS", bluetooth)

        for phrase in ("coupe le wifi", "active le bluetooth"):
            match = FastIntentRouter().route(phrase)
            if match is None:
                raise RuntimeError(f"intent did not match: {phrase}")
            if match.request.risk is not RiskClass.SENSITIVE:
                raise RuntimeError(f"wrong risk for {phrase}: {match.request.risk}")
            decision = policy.evaluate(match.request, context)
            print(f"NETWORK_PERMISSION: {phrase} -> {decision.value}")
            if decision.value != "ask":
                raise RuntimeError(f"network toggle not gated: {phrase}")

        before = set(_visible_windows())
        opened = driver.open_app("bloc notes")
        _dump("APP_OPEN", opened)
        hwnd, title = _new_window(before)
        print(f"WINDOW_TARGET: hwnd={hwnd} title={title}")

        _dump("WINDOW_MAXIMIZE", driver._window_state_hwnd(hwnd, "maximize"))
        time.sleep(0.4)
        _dump("WINDOW_RESTORE", driver._window_state_hwnd(hwnd, "restore"))
        time.sleep(0.4)

        try:
            moved = driver._move_window_to_monitor_hwnd(hwnd, 2)
            _dump("WINDOW_MONITOR_2", moved)
            hold_seconds = float(os.getenv("JARJAR_SMOKE_WINDOW_HOLD_SECONDS", "5"))
            print(
                f"WINDOW_MULTI_MONITOR: moved to screen 2; holding {hold_seconds:.1f}s for visual confirmation"
            )
            time.sleep(max(0.0, hold_seconds))
            print("WINDOW_MULTI_MONITOR: PASS")
        except ValueError as exc:
            if "detected 1" in str(exc):
                print(f"WINDOW_MULTI_MONITOR: SKIP {exc}")
            else:
                raise

        _dump("WINDOW_CLOSE", driver._close_window_hwnd(hwnd))

    except Exception as exc:
        print(f"WINDOWS_CONTROLS_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    print("WINDOWS_CONTROLS_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
