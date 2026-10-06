"""Structured Windows action backend.

OS-specific implementation is injected. No raw coordinates or visual control
belong in this backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import ActionRequest, ActionResult, Capability


class WindowsDriver(Protocol):
    def open_app(self, app: str) -> dict: ...
    def list_windows(self) -> dict: ...
    def focus_window(self, title: str) -> dict: ...
    def close_window(self, title: str) -> dict: ...
    def media_key(self, key: str) -> dict: ...
    def audio_status(self) -> dict: ...
    def audio_set_volume(self, percent: int) -> dict: ...
    def audio_set_mute(self, muted: bool) -> dict: ...
    def battery_status(self) -> dict: ...
    def wifi_status(self) -> dict: ...
    def wifi_set_enabled(self, enabled: bool) -> dict: ...
    def bluetooth_status(self) -> dict: ...
    def bluetooth_set_enabled(self, enabled: bool) -> dict: ...
    def window_state(self, title: str, state: str) -> dict: ...
    def move_window_to_monitor(self, title: str, monitor_index: int) -> dict: ...


@dataclass
class NativeWindowsBackend:
    driver: WindowsDriver
    name: str = "windows.structured"
    priority: int = 10

    _supported = frozenset({
        "app.open",
        "window.list",
        "window.focus",
        "window.close",
        "audio.volume_up",
        "audio.volume_down",
        "audio.mute_toggle",
        "audio.status",
        "audio.set_volume",
        "audio.adjust_volume",
        "audio.set_mute",
        "media.play_pause",
        "media.next",
        "media.previous",
        "system.battery",
        "wifi.status",
        "wifi.enable",
        "wifi.disable",
        "bluetooth.status",
        "bluetooth.enable",
        "bluetooth.disable",
        "window.minimize",
        "window.maximize",
        "window.restore",
        "window.move_monitor",
    })

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "windows" and request.capability in self._supported

    def execute(self, request: ActionRequest) -> ActionResult:
        try:
            if request.capability == "app.open":
                data = self.driver.open_app(self._required(request, "app"))
            elif request.capability == "window.list":
                data = self.driver.list_windows()
            elif request.capability == "window.focus":
                data = self.driver.focus_window(self._required(request, "title"))
            elif request.capability == "window.close":
                data = self.driver.close_window(self._required(request, "title"))
            elif request.capability == "audio.volume_up":
                data = self.driver.media_key("volume_up")
            elif request.capability == "audio.volume_down":
                data = self.driver.media_key("volume_down")
            elif request.capability == "audio.mute_toggle":
                data = self.driver.media_key("volume_mute")
            elif request.capability == "audio.status":
                data = self.driver.audio_status()
            elif request.capability == "audio.set_volume":
                raw = request.arguments.get("percent")
                if not isinstance(raw, int):
                    raise ValueError("missing or invalid Windows argument: percent")
                data = self.driver.audio_set_volume(raw)
            elif request.capability == "audio.adjust_volume":
                raw = request.arguments.get("delta")
                if not isinstance(raw, int):
                    raise ValueError("missing or invalid Windows argument: delta")
                status = self.driver.audio_status()
                current = status.get("volume_percent")
                if not isinstance(current, int):
                    raise ValueError("Windows audio status did not return volume_percent")
                target = max(0, min(100, current + raw))
                data = self.driver.audio_set_volume(target)
                data["requested_delta"] = raw
                data["previous_volume_percent"] = current
            elif request.capability == "audio.set_mute":
                raw = request.arguments.get("muted")
                if not isinstance(raw, bool):
                    raise ValueError("missing or invalid Windows argument: muted")
                data = self.driver.audio_set_mute(raw)
            elif request.capability == "media.play_pause":
                data = self.driver.media_key("media_play_pause")
            elif request.capability == "media.next":
                data = self.driver.media_key("media_next")
            elif request.capability == "media.previous":
                data = self.driver.media_key("media_previous")
            elif request.capability == "system.battery":
                data = self.driver.battery_status()
            elif request.capability == "wifi.status":
                data = self.driver.wifi_status()
            elif request.capability == "wifi.enable":
                data = self.driver.wifi_set_enabled(True)
            elif request.capability == "wifi.disable":
                data = self.driver.wifi_set_enabled(False)
            elif request.capability == "bluetooth.status":
                data = self.driver.bluetooth_status()
            elif request.capability == "bluetooth.enable":
                data = self.driver.bluetooth_set_enabled(True)
            elif request.capability == "bluetooth.disable":
                data = self.driver.bluetooth_set_enabled(False)
            elif request.capability == "window.minimize":
                data = self.driver.window_state(self._required(request, "title"), "minimize")
            elif request.capability == "window.maximize":
                data = self.driver.window_state(self._required(request, "title"), "maximize")
            elif request.capability == "window.restore":
                data = self.driver.window_state(self._required(request, "title"), "restore")
            elif request.capability == "window.move_monitor":
                raw = request.arguments.get("monitor_index")
                if not isinstance(raw, int) or raw < 1:
                    raise ValueError("missing or invalid Windows argument: monitor_index")
                data = self.driver.move_window_to_monitor(
                    self._required(request, "title"),
                    raw,
                )
            else:
                return ActionResult(False, "unsupported Windows capability", backend=self.name)
        except (KeyError, ValueError) as exc:
            return ActionResult(False, str(exc), backend=self.name)
        except Exception as exc:
            return ActionResult(
                False,
                f"Windows driver failure: {type(exc).__name__}: {exc}",
                backend=self.name,
            )
        message = self._format_success_message(request.capability, data)
        return ActionResult(True, message, data=data, backend=self.name)

    @staticmethod
    def _format_success_message(capability: str, data: dict) -> str:
        if capability == "audio.status":
            percent = data.get("volume_percent")
            muted = data.get("muted")
            if isinstance(percent, int):
                mute_text = "oui" if muted is True else "non" if muted is False else "inconnu"
                return f"Volume actuel : {percent} %. Muet : {mute_text}."

        if capability == "system.battery":
            percent = data.get("battery_percent")
            ac_online = data.get("ac_online")
            if isinstance(percent, int):
                power_text = "branché sur secteur" if ac_online is True else "sur batterie" if ac_online is False else "alimentation inconnue"
                return f"Batterie : {percent} %. État : {power_text}."

        if capability == "wifi.status":
            adapters = data.get("adapters") or []
            if not adapters:
                return "Wi-Fi : aucun adaptateur détecté."
            states = []
            for adapter in adapters:
                name = adapter.get("Name") or adapter.get("InterfaceDescription") or "adaptateur"
                status = adapter.get("Status") or "inconnu"
                states.append(f"{name}={status}")
            return "Wi-Fi : " + "; ".join(states) + "."

        if capability == "bluetooth.status":
            devices = data.get("devices") or []
            if not devices:
                return "Bluetooth : aucun périphérique radio détecté."
            states = []
            for device in devices:
                name = device.get("FriendlyName") or "périphérique"
                status = device.get("Status") or "inconnu"
                states.append(f"{name}={status}")
            return "Bluetooth : " + "; ".join(states) + "."

        if capability == "window.list":
            windows = data.get("windows") or []
            return f"Fenêtres visibles détectées : {len(windows)}."

        return "Windows action completed"

    @staticmethod
    def _required(request: ActionRequest, key: str) -> str:
        value = request.arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing Windows argument: {key}")
        return value.strip()
