"""Win32 implementation of the structured WindowsDriver contract."""
from __future__ import annotations

import ctypes
import os
import subprocess

from .windows_app_inventory import WindowsAppInventory


class Win32Driver:
    def __init__(self, app_inventory: WindowsAppInventory | None = None) -> None:
        self.app_inventory = app_inventory or WindowsAppInventory()
    def _modules(self):
        try:
            import win32con
            import win32gui
            import win32process
        except ImportError as exc:
            raise RuntimeError("pywin32 is not installed; install the windows optional dependency") from exc
        return win32con, win32gui, win32process

    def open_app(self, app: str) -> dict:
        entry = self.app_inventory.resolve(app)
        target = entry.target if entry is not None else app
        if target.casefold().endswith(".lnk"):
            os.startfile(target)
            return {
                "app": app,
                "target": target,
                "source": entry.source if entry else "direct",
                "pid": None,
            }
        process = subprocess.Popen([target])
        return {
            "app": app,
            "target": target,
            "source": entry.source if entry else "direct",
            "pid": process.pid,
        }

    def list_windows(self) -> dict:
        _, win32gui, win32process = self._modules()
        windows = []

        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    windows.append(
                        {
                            "hwnd": int(hwnd),
                            "pid": int(pid),
                            "title": title,
                            "class_name": win32gui.GetClassName(hwnd),
                        }
                    )
            return True

        win32gui.EnumWindows(collect, None)
        return {"windows": windows}

    def focus_window(self, title: str) -> dict:
        win32con, win32gui, _ = self._modules()
        wanted = title.casefold()
        matches = []

        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                current = win32gui.GetWindowText(hwnd).strip()
                if current and wanted in current.casefold():
                    matches.append((hwnd, current))
            return True

        win32gui.EnumWindows(collect, None)
        if not matches:
            raise ValueError(f"window not found: {title}")
        hwnd, current = matches[0]
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return {"hwnd": int(hwnd), "title": current}


    def close_window(self, title: str) -> dict:
        win32con, win32gui, _ = self._modules()
        wanted = title.casefold()
        matches = []

        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                current = win32gui.GetWindowText(hwnd).strip()
                if current and wanted in current.casefold():
                    matches.append((hwnd, current))
            return True

        win32gui.EnumWindows(collect, None)
        if not matches:
            raise ValueError(f"window not found: {title}")
        hwnd, current = matches[0]
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return {"hwnd": int(hwnd), "title": current, "requested": "close"}

    def media_key(self, key: str) -> dict:
        virtual_keys = {
            "volume_mute": 0xAD,
            "volume_down": 0xAE,
            "volume_up": 0xAF,
            "media_next": 0xB0,
            "media_previous": 0xB1,
            "media_play_pause": 0xB3,
        }
        vk = virtual_keys.get(key)
        if vk is None:
            raise ValueError(f"unsupported media key: {key}")
        user32 = ctypes.windll.user32
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 0x0002, 0)
        return {"key": key, "virtual_key": vk}

    def battery_status(self) -> dict:
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_ubyte),
                ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte),
                ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", ctypes.c_uint32),
                ("BatteryFullLifeTime", ctypes.c_uint32),
            ]

        status = SYSTEM_POWER_STATUS()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            raise RuntimeError("GetSystemPowerStatus failed")
        percent = None if status.BatteryLifePercent == 255 else int(status.BatteryLifePercent)
        return {
            "ac_online": status.ACLineStatus == 1,
            "battery_percent": percent,
            "battery_flag": int(status.BatteryFlag),
            "battery_life_seconds": None
            if status.BatteryLifeTime == 0xFFFFFFFF
            else int(status.BatteryLifeTime),
        }
