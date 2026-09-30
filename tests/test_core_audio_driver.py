from jarvis.integrations.win32_driver import Win32Driver


class Endpoint:
    def __init__(self):
        self.scalar = 0.42
        self.mute = 0

    def GetMasterVolumeLevelScalar(self):
        return self.scalar

    def SetMasterVolumeLevelScalar(self, scalar, _ctx):
        self.scalar = scalar

    def GetMute(self):
        return self.mute

    def SetMute(self, mute, _ctx):
        self.mute = mute


def test_core_audio_status_and_restore(monkeypatch):
    endpoint = Endpoint()
    driver = Win32Driver()
    monkeypatch.setattr(driver, "_endpoint_volume", lambda: endpoint)

    assert driver.audio_status()["volume_percent"] == 42
    assert driver.audio_set_volume(55)["volume_percent"] == 55
    assert driver.audio_set_mute(True)["muted"] is True
    assert driver.audio_set_volume(42)["volume_percent"] == 42
    assert driver.audio_set_mute(False)["muted"] is False
