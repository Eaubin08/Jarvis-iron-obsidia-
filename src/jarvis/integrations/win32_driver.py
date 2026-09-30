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
        hwnd, _ = self._find_window(title)
        return self._close_window_hwnd(int(hwnd))

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


    def _run_powershell_json(self, script: str) -> object:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "& {\n" + script + "\n} | ConvertTo-Json -Compress -Depth 4",
            ],
            capture_output=True,
            text=True,
            timeout=12,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "PowerShell command failed").strip()
            raise RuntimeError(message[:1000])
        raw = result.stdout.strip()
        if not raw:
            return None
        import json
        return json.loads(raw)

    def wifi_status(self) -> dict:
        script = r"""
$items = Get-NetAdapter -Physical -ErrorAction SilentlyContinue |
  Where-Object {
    $_.Name -match 'Wi-Fi|Wireless|WLAN' -or
    $_.InterfaceDescription -match 'Wi-Fi|Wireless|802\.11|WLAN'
  } |
  Select-Object Name, InterfaceDescription, Status, MacAddress, LinkSpeed
$items
"""
        data = self._run_powershell_json(script)
        if data is None:
            adapters = []
        elif isinstance(data, list):
            adapters = data
        else:
            adapters = [data]
        return {"adapters": adapters, "available": bool(adapters)}

    def wifi_set_enabled(self, enabled: bool) -> dict:
        status = self.wifi_status()
        adapters = status["adapters"]
        if not adapters:
            raise ValueError("Wi-Fi adapter not found")
        if len(adapters) != 1:
            raise ValueError("multiple Wi-Fi adapters found; explicit adapter selection required")
        name = adapters[0].get("Name")
        if not isinstance(name, str) or not name:
            raise ValueError("Wi-Fi adapter has no usable name")
        escaped = name.replace("'", "''")
        verb = "Enable-NetAdapter" if enabled else "Disable-NetAdapter"
        script = (
            f"Get-NetAdapter -Name '{escaped}' -ErrorAction Stop | "
            f"{verb} -Confirm:$false -PassThru | "
            "Select-Object Name, Status, InterfaceDescription"
        )
        data = self._run_powershell_json(script)
        return {"enabled": enabled, "adapter": data}

    def bluetooth_status(self) -> dict:
        script = r"""
$items = Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue |
  Where-Object {
    $_.FriendlyName -match 'adapter|radio|bluetooth' -and
    $_.InstanceId -notmatch '^BTHENUM'
  } |
  Select-Object FriendlyName, Status, InstanceId, Class
$items
"""
        data = self._run_powershell_json(script)
        if data is None:
            devices = []
        elif isinstance(data, list):
            devices = data
        else:
            devices = [data]
        return {"devices": devices, "available": bool(devices)}

    def bluetooth_set_enabled(self, enabled: bool) -> dict:
        status = self.bluetooth_status()
        devices = status["devices"]
        candidates = [
            device for device in devices
            if isinstance(device.get("FriendlyName"), str)
            and any(
                token in device["FriendlyName"].casefold()
                for token in ("adapter", "radio")
            )
        ]
        if len(candidates) != 1:
            raise ValueError(
                "Bluetooth radio identity is ambiguous; explicit physical validation required"
            )
        instance_id = candidates[0].get("InstanceId")
        if not isinstance(instance_id, str) or not instance_id:
            raise ValueError("Bluetooth radio has no usable InstanceId")
        escaped = instance_id.replace("'", "''")
        verb = "Enable-PnpDevice" if enabled else "Disable-PnpDevice"
        script = (
            f"Get-PnpDevice -InstanceId '{escaped}' -ErrorAction Stop | "
            f"{verb} -Confirm:$false -PassThru | "
            "Select-Object FriendlyName, Status, InstanceId"
        )
        data = self._run_powershell_json(script)
        return {"enabled": enabled, "device": data}

    def _find_window(self, title: str):
        _, win32gui, _ = self._modules()
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
        if len(matches) > 1:
            exact = [item for item in matches if item[1].casefold() == wanted]
            if len(exact) == 1:
                return exact[0]
            raise ValueError(f"ambiguous window title: {title}")
        return matches[0]

    def _window_state_hwnd(self, hwnd: int, state: str) -> dict:
        win32con, win32gui, _ = self._modules()
        if not win32gui.IsWindow(hwnd):
            raise ValueError(f"window handle not found: {hwnd}")
        current = win32gui.GetWindowText(hwnd).strip()
        commands = {
            "minimize": win32con.SW_MINIMIZE,
            "maximize": win32con.SW_MAXIMIZE,
            "restore": win32con.SW_RESTORE,
        }
        command = commands.get(state)
        if command is None:
            raise ValueError(f"unsupported window state: {state}")
        win32gui.ShowWindow(hwnd, command)
        return {"hwnd": int(hwnd), "title": current, "state": state}

    def window_state(self, title: str, state: str) -> dict:
        hwnd, _ = self._find_window(title)
        return self._window_state_hwnd(int(hwnd), state)

    def _move_window_to_monitor_hwnd(self, hwnd: int, monitor_index: int) -> dict:
        _, win32gui, _ = self._modules()
        if not win32gui.IsWindow(hwnd):
            raise ValueError(f"window handle not found: {hwnd}")
        current = win32gui.GetWindowText(hwnd).strip()
        monitors = []

        def collect(monitor, _hdc, _rect):
            info = win32gui.GetMonitorInfo(monitor)
            monitors.append(info)
            return True

        win32gui.EnumDisplayMonitors(None, None, collect)
        if monitor_index > len(monitors):
            raise ValueError(
                f"monitor {monitor_index} unavailable; detected {len(monitors)}"
            )

        target = monitors[monitor_index - 1]["Work"]
        left, top, right, bottom = target
        win_left, win_top, win_right, win_bottom = win32gui.GetWindowRect(hwnd)
        width = max(320, win_right - win_left)
        height = max(200, win_bottom - win_top)
        width = min(width, right - left)
        height = min(height, bottom - top)

        if win32gui.IsIconic(hwnd):
            import win32con
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        win32gui.MoveWindow(hwnd, left, top, width, height, True)
        return {
            "hwnd": int(hwnd),
            "title": current,
            "monitor_index": monitor_index,
            "bounds": {
                "left": int(left),
                "top": int(top),
                "width": int(width),
                "height": int(height),
            },
            "monitor_count": len(monitors),
        }

    def move_window_to_monitor(self, title: str, monitor_index: int) -> dict:
        hwnd, _ = self._find_window(title)
        return self._move_window_to_monitor_hwnd(int(hwnd), monitor_index)

    def _close_window_hwnd(self, hwnd: int) -> dict:
        win32con, win32gui, _ = self._modules()
        if not win32gui.IsWindow(hwnd):
            raise ValueError(f"window handle not found: {hwnd}")
        current = win32gui.GetWindowText(hwnd).strip()
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return {"hwnd": int(hwnd), "title": current, "requested": "close"}
