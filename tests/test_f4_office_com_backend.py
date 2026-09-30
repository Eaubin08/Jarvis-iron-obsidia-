from jarvis.contracts import ActionRequest, Capability
from jarvis.office_com import OfficeCOMBackend


class FakeCOM:
    def __init__(self):
        self.calls = []

    def word_insert_table(self, **kwargs):
        self.calls.append(("word_insert_table", kwargs))
        return kwargs

    def word_save_as(self, **kwargs):
        self.calls.append(("word_save_as", kwargs))
        return kwargs

    def excel_get_range(self, **kwargs):
        self.calls.append(("excel_get_range", kwargs))
        return {"values": [["A", 1]]}

    def excel_set_range(self, **kwargs):
        self.calls.append(("excel_set_range", kwargs))
        return kwargs

    def powerpoint_set_background(self, **kwargs):
        self.calls.append(("powerpoint_set_background", kwargs))
        return kwargs

    def powerpoint_save_as(self, **kwargs):
        self.calls.append(("powerpoint_save_as", kwargs))
        return kwargs


def test_word_insert_table_is_native_windows_capability():
    driver = FakeCOM()
    backend = OfficeCOMBackend(driver)
    request = ActionRequest("office.word.insert_table", {"rows": 2, "columns": 3})
    assert backend.can_execute(request, Capability(request.capability, "windows"))
    result = backend.execute(request)
    assert result.ok and result.backend == "windows.com"
    assert driver.calls == [("word_insert_table", {"rows": 2, "columns": 3})]


def test_excel_get_and_set_range_are_structured():
    driver = FakeCOM()
    backend = OfficeCOMBackend(driver)
    read = backend.execute(ActionRequest("office.excel.get_range", {
        "sheet": "Sheet1", "start_row": 1, "start_col": 1, "end_row": 2, "end_col": 2,
    }))
    write = backend.execute(ActionRequest("office.excel.set_range", {
        "sheet": "Sheet1", "start_row": 1, "start_col": 1, "values": [["A", 1], ["B", 2]],
    }))
    assert read.ok and read.data["values"] == [["A", 1]]
    assert write.ok


def test_powerpoint_background_requires_valid_arguments():
    backend = OfficeCOMBackend(FakeCOM())
    result = backend.execute(ActionRequest("office.powerpoint.set_background", {
        "color": "112233", "slide_indexes": [1, 2],
    }))
    assert result.ok


def test_invalid_excel_matrix_fails_closed():
    result = OfficeCOMBackend(FakeCOM()).execute(ActionRequest("office.excel.set_range", {
        "sheet": "Sheet1", "start_row": 1, "start_col": 1, "values": [],
    }))
    assert not result.ok


def test_office_com_does_not_claim_visual_backend_family():
    backend = OfficeCOMBackend(FakeCOM())
    req = ActionRequest("office.word.insert_table", {"rows": 1, "columns": 1})
    assert not backend.can_execute(req, Capability(req.capability, "visual"))
