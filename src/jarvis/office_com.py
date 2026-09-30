"""Jarvis-owned native Office COM backend, adapted from UFO² WinCOM patterns."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .contracts import ActionRequest, ActionResult, Capability


class OfficeCOMDriver(Protocol):
    def word_insert_table(self, *, rows: int, columns: int) -> dict: ...
    def word_save_as(self, *, file_path: str) -> dict: ...
    def excel_get_range(self, *, sheet: str, start_row: int, start_col: int, end_row: int, end_col: int) -> dict: ...
    def excel_set_range(self, *, sheet: str, start_row: int, start_col: int, values: list[list[object]]) -> dict: ...
    def powerpoint_set_background(self, *, color: str, slide_indexes: list[int] | None = None) -> dict: ...
    def powerpoint_save_as(self, *, file_path: str) -> dict: ...


@dataclass
class OfficeCOMBackend:
    driver: OfficeCOMDriver
    name: str = "windows.com"
    priority: int = 6

    _supported = frozenset({
        "office.word.insert_table",
        "office.word.save_as",
        "office.excel.get_range",
        "office.excel.set_range",
        "office.powerpoint.set_background",
        "office.powerpoint.save_as",
    })

    def can_execute(self, request: ActionRequest, capability: Capability) -> bool:
        return capability.backend_family == "windows" and request.capability in self._supported

    def execute(self, request: ActionRequest) -> ActionResult:
        try:
            args = request.arguments
            if request.capability == "office.word.insert_table":
                data = self.driver.word_insert_table(
                    rows=self._positive_int(args, "rows"),
                    columns=self._positive_int(args, "columns"),
                )
            elif request.capability == "office.word.save_as":
                data = self.driver.word_save_as(file_path=self._required_str(args, "file_path"))
            elif request.capability == "office.excel.get_range":
                data = self.driver.excel_get_range(
                    sheet=self._required_str(args, "sheet"),
                    start_row=self._positive_int(args, "start_row"),
                    start_col=self._positive_int(args, "start_col"),
                    end_row=self._positive_int(args, "end_row"),
                    end_col=self._positive_int(args, "end_col"),
                )
            elif request.capability == "office.excel.set_range":
                values = args.get("values")
                if not isinstance(values, list) or not values or not all(isinstance(row, list) for row in values):
                    raise ValueError("invalid Office COM argument: values")
                data = self.driver.excel_set_range(
                    sheet=self._required_str(args, "sheet"),
                    start_row=self._positive_int(args, "start_row"),
                    start_col=self._positive_int(args, "start_col"),
                    values=values,
                )
            elif request.capability == "office.powerpoint.set_background":
                indexes = args.get("slide_indexes")
                if indexes is not None and (
                    not isinstance(indexes, list)
                    or not all(isinstance(i, int) and i > 0 for i in indexes)
                ):
                    raise ValueError("invalid Office COM argument: slide_indexes")
                data = self.driver.powerpoint_set_background(
                    color=self._required_str(args, "color"),
                    slide_indexes=indexes,
                )
            elif request.capability == "office.powerpoint.save_as":
                data = self.driver.powerpoint_save_as(file_path=self._required_str(args, "file_path"))
            else:
                return ActionResult(False, "unsupported Office COM capability", backend=self.name)
        except ValueError as exc:
            return ActionResult(False, str(exc), backend=self.name)
        except Exception as exc:
            return ActionResult(
                False,
                f"Office COM driver failure: {type(exc).__name__}: {exc}",
                backend=self.name,
            )
        return ActionResult(True, "Office COM action completed", data=data, backend=self.name)

    @staticmethod
    def _required_str(args: dict, key: str) -> str:
        value = args.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing Office COM argument: {key}")
        return value.strip()

    @staticmethod
    def _positive_int(args: dict, key: str) -> int:
        value = args.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"invalid Office COM argument: {key}")
        return value
