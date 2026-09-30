"""Windows application inventory and bounded name resolution.

Donor-inspired pattern: keep an inventory separate from action execution.
Jarjar owns the implementation and only returns structured candidates.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import time


def _norm(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


@dataclass(frozen=True)
class AppEntry:
    name: str
    target: str
    source: str


class WindowsAppInventory:
    def __init__(self, *, refresh_seconds: float = 300.0) -> None:
        self.refresh_seconds = refresh_seconds
        self._entries: tuple[AppEntry, ...] = ()
        self._refreshed_at = 0.0

    def snapshot(self, *, force: bool = False) -> tuple[AppEntry, ...]:
        now = time.monotonic()
        if force or not self._entries or now - self._refreshed_at >= self.refresh_seconds:
            self._entries = self._discover()
            self._refreshed_at = now
        return self._entries

    def resolve(self, query: str) -> AppEntry | None:
        wanted = _norm(query)
        if not wanted:
            return None

        entries = self.snapshot()
        exact = [entry for entry in entries if _norm(entry.name) == wanted]
        if exact:
            return exact[0]

        prefix = [entry for entry in entries if _norm(entry.name).startswith(wanted)]
        if len(prefix) == 1:
            return prefix[0]

        contains = [entry for entry in entries if wanted in _norm(entry.name)]
        if len(contains) == 1:
            return contains[0]
        return None

    def _discover(self) -> tuple[AppEntry, ...]:
        found: dict[tuple[str, str], AppEntry] = {}

        aliases = {
            "bloc notes": "notepad.exe",
            "notepad": "notepad.exe",
            "calculatrice": "calc.exe",
            "calculator": "calc.exe",
            "explorateur": "explorer.exe",
            "explorateur de fichiers": "explorer.exe",
        }
        for name, target in aliases.items():
            found[(_norm(name), target.casefold())] = AppEntry(name, target, "builtin")

        start_roots = [
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        ]
        for root in start_roots:
            if not str(root) or not root.exists():
                continue
            try:
                paths = root.rglob("*.lnk")
                for path in paths:
                    name = path.stem.strip()
                    if name:
                        entry = AppEntry(name, str(path), "start_menu")
                        found[(_norm(name), str(path).casefold())] = entry
            except OSError:
                pass

        try:
            import winreg

            hives = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
            keys = (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
            )
            for hive in hives:
                for key_path in keys:
                    try:
                        with winreg.OpenKey(hive, key_path) as key:
                            index = 0
                            while True:
                                try:
                                    subname = winreg.EnumKey(key, index)
                                except OSError:
                                    break
                                index += 1
                                try:
                                    with winreg.OpenKey(key, subname) as sub:
                                        target, _ = winreg.QueryValueEx(sub, None)
                                except OSError:
                                    continue
                                if isinstance(target, str) and target.strip():
                                    name = Path(subname).stem
                                    entry = AppEntry(name, target.strip(), "app_paths")
                                    found[(_norm(name), target.casefold())] = entry
                    except OSError:
                        continue
        except ImportError:
            pass

        return tuple(sorted(found.values(), key=lambda item: (_norm(item.name), item.target.casefold())))
