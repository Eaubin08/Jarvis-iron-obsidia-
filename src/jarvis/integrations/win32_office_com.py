"""Windows Office COM driver behind Jarvis-owned capabilities."""
from __future__ import annotations

from pathlib import Path


class Win32OfficeCOMDriver:
    def _dispatch(self, prog_id: str):
        try:
            import win32com.client
        except ImportError as exc:
            raise RuntimeError("pywin32 is not installed; install the windows optional dependency") from exc
        return win32com.client.Dispatch(prog_id)

    @staticmethod
    def _active_document(app, attr: str):
        obj = getattr(app, attr, None)
        if obj is None:
            raise RuntimeError(f"no active Office object: {attr}")
        return obj

    def word_insert_table(self, *, rows: int, columns: int) -> dict:
        app = self._dispatch("Word.Application")
        doc = self._active_document(app, "ActiveDocument")
        rng = doc.Content
        rng.Collapse(0)
        rng.InsertParagraphAfter()
        table = doc.Tables.Add(rng, rows, columns)
        table.Borders.Enable = True
        return {"application": "word", "rows": rows, "columns": columns}

    def word_save_as(self, *, file_path: str) -> dict:
        app = self._dispatch("Word.Application")
        doc = self._active_document(app, "ActiveDocument")
        path = str(Path(file_path).expanduser().resolve())
        ext = Path(path).suffix.casefold()
        formats = {".docx": 12, ".pdf": 17, ".txt": 2, ".rtf": 6}
        if ext not in formats:
            raise ValueError(f"unsupported Word save extension: {ext}")
        doc.SaveAs(path, FileFormat=formats[ext])
        return {"application": "word", "file_path": path}

    def excel_get_range(self, *, sheet: str, start_row: int, start_col: int, end_row: int, end_col: int) -> dict:
        app = self._dispatch("Excel.Application")
        book = self._active_document(app, "ActiveWorkbook")
        ws = book.Worksheets(sheet)
        values = ws.Range(ws.Cells(start_row, start_col), ws.Cells(end_row, end_col)).Value
        if isinstance(values, tuple):
            serializable = [list(row) if isinstance(row, tuple) else [row] for row in values]
        else:
            serializable = [[values]]
        return {"application": "excel", "sheet": sheet, "values": serializable}

    def excel_set_range(self, *, sheet: str, start_row: int, start_col: int, values: list[list[object]]) -> dict:
        app = self._dispatch("Excel.Application")
        book = self._active_document(app, "ActiveWorkbook")
        ws = book.Worksheets(sheet)
        rows = len(values)
        cols = max(len(row) for row in values)
        if any(len(row) != cols for row in values):
            raise ValueError("Excel values must form a rectangular matrix")
        end_row = start_row + rows - 1
        end_col = start_col + cols - 1
        ws.Range(ws.Cells(start_row, start_col), ws.Cells(end_row, end_col)).Value = tuple(tuple(row) for row in values)
        return {
            "application": "excel",
            "sheet": sheet,
            "range": [start_row, start_col, end_row, end_col],
        }

    def powerpoint_set_background(self, *, color: str, slide_indexes: list[int] | None = None) -> dict:
        value = color.strip().lstrip("#")
        if len(value) != 6:
            raise ValueError("PowerPoint color must be a 6-digit RGB hex value")
        try:
            red, green, blue = int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16)
        except ValueError as exc:
            raise ValueError("PowerPoint color must be hexadecimal") from exc

        app = self._dispatch("PowerPoint.Application")
        deck = self._active_document(app, "ActivePresentation")
        indexes = slide_indexes or list(range(1, deck.Slides.Count + 1))
        rgb = red | (green << 8) | (blue << 16)
        for index in indexes:
            if index < 1 or index > deck.Slides.Count:
                raise ValueError(f"PowerPoint slide index out of range: {index}")
            slide = deck.Slides(index)
            slide.FollowMasterBackground = False
            slide.Background.Fill.Visible = True
            slide.Background.Fill.Solid()
            slide.Background.Fill.ForeColor.RGB = rgb
        return {"application": "powerpoint", "slides": indexes, "color": value.upper()}

    def powerpoint_save_as(self, *, file_path: str) -> dict:
        app = self._dispatch("PowerPoint.Application")
        deck = self._active_document(app, "ActivePresentation")
        path = str(Path(file_path).expanduser().resolve())
        ext = Path(path).suffix.casefold()
        formats = {".pptx": 24, ".pdf": 32, ".png": 18, ".jpg": 17}
        if ext not in formats:
            raise ValueError(f"unsupported PowerPoint save extension: {ext}")
        deck.SaveAs(path, FileFormat=formats[ext])
        return {"application": "powerpoint", "file_path": path}
