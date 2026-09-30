from jarvis.contracts import ActionRequest
from jarvis.integrations.pyautogui_visual_driver import PyAutoGUIVisualDriver
from jarvis.monitor_layout import Monitor, MonitorLayout


class Provider:
    def __init__(self, layout):
        self._layout = layout

    def layout(self):
        return self._layout


class FakePyAutoGUI:
    def __init__(self):
        self.clicks = []

    def click(self, *, x, y):
        self.clicks.append((x, y))


class Driver(PyAutoGUIVisualDriver):
    def __init__(self, layout):
        super().__init__(monitor_provider=Provider(layout))
        self.fake = FakePyAutoGUI()

    def _pyautogui(self):
        return self.fake

    def _capture_virtual_desktop(self, path, layout):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fake")


def dual_layout():
    return MonitorLayout((
        Monitor("secondary-left", -1920, 0, 0, 1080, False),
        Monitor("primary", 0, 0, 1920, 1080, True),
    ))


def test_monitor_layout_supports_negative_secondary_coordinates():
    layout = dual_layout()
    assert layout.left == -1920
    assert layout.right == 1920
    assert layout.width == 3840
    assert layout.monitor_for_point(-100, 500).monitor_id == "secondary-left"
    assert layout.monitor_for_point(100, 500).monitor_id == "primary"


def test_snapshot_exposes_virtual_desktop_and_each_monitor(tmp_path):
    driver = Driver(dual_layout())
    driver.evidence_dir = tmp_path
    state = driver.snapshot()

    assert state["left"] == -1920
    assert state["width"] == 3840
    assert state["coordinate_space"] == "windows_virtual_desktop"
    assert len(state["monitors"]) == 2


def test_click_accepts_negative_coordinate_on_secondary_monitor(tmp_path):
    driver = Driver(dual_layout())
    driver.evidence_dir = tmp_path
    state = driver.snapshot()

    data = driver.execute(ActionRequest("visual.click", {"x": -100, "y": 500}), state)

    assert data["monitor_id"] == "secondary-left"
    assert driver.fake.clicks == [(-100, 500)]


def test_click_rejects_gap_between_real_monitors(tmp_path):
    layout = MonitorLayout((
        Monitor("left", -1920, 0, -100, 1080),
        Monitor("primary", 0, 0, 1920, 1080, True),
    ))
    driver = Driver(layout)
    driver.evidence_dir = tmp_path
    state = driver.snapshot()

    try:
        driver.execute(ActionRequest("visual.click", {"x": -50, "y": 500}), state)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "gap between monitors" in str(exc)
