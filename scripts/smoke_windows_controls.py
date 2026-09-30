"""Physical smoke for Jarjar Windows controls.

Safe policy:
- network radios: read real state only; toggles are checked at permission gate,
  never executed by this smoke.
- window actions: open an empty Notepad instance, manipulate only that window,
  then close it.
"""
from __future__ import annotations

import json
import time

from jarvis.contracts import ActionRequest, ContextSnapshot, RiskClass
from jarvis.fast_intent import FastIntentRouter
from jarvis.integrations.win32_driver import Win32Driver
from jarvis.local_actions import LocalPermissionPolicy


def _dump(label: str, value: object) -> None:
    print(f"{label}: {json.dumps(value, ensure_ascii=False, default=str)}")


def _title_for_pid(pid: int, timeout: float = 8.0) -> str:
    import win32gui
    import win32process

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        matches = []

        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                _, current_pid = win32process.GetWindowThreadProcessId(hwnd)
                title = win32gui.GetWindowText(hwnd).strip()
                if current_pid == pid and title:
                    matches.append(title)
            return True

        win32gui.EnumWindows(collect, None)
        if matches:
            return matches[0]
        time.sleep(0.2)
    raise RuntimeError(f"no visible window found for pid={pid}")


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

        opened = driver.open_app("bloc notes")
        _dump("APP_OPEN", opened)
        pid = opened.get("pid")
        if not isinstance(pid, int):
            raise RuntimeError("Notepad launch returned no process id")
        title = _title_for_pid(pid)
        print(f"WINDOW_TARGET: {title}")

        _dump("WINDOW_MAXIMIZE", driver.window_state(title, "maximize"))
        time.sleep(0.4)
        _dump("WINDOW_RESTORE", driver.window_state(title, "restore"))
        time.sleep(0.4)

        try:
            moved = driver.move_window_to_monitor(title, 2)
            _dump("WINDOW_MONITOR_2", moved)
            print("WINDOW_MULTI_MONITOR: PASS")
        except ValueError as exc:
            if "detected 1" in str(exc):
                print(f"WINDOW_MULTI_MONITOR: SKIP {exc}")
            else:
                raise

        _dump("WINDOW_CLOSE", driver.close_window(title))

    except Exception as exc:
        print(f"WINDOWS_CONTROLS_PHYSICAL: FAIL {type(exc).__name__}: {exc}")
        return 2

    print("WINDOWS_CONTROLS_PHYSICAL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
