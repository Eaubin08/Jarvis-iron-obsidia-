"""Win32 implementation of the structured WindowsDriver contract."""
from __future__ import annotations

import subprocess


class Win32Driver:
    def _modules(self):
        try:
            import win32con
            import win32gui
            import win32process
        except ImportError as exc:
            raise RuntimeError("pywin32 is not installed; install the windows optional dependency") from exc
        return win32con, win32gui, win32process

    def open_app(self, app: str) -> dict:
        process = subprocess.Popen([app])
        return {"app": app, "pid": process.pid}

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
