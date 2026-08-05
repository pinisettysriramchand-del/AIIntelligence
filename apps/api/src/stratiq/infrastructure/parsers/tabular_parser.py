from io import BytesIO
from pathlib import Path

import pandas as pd


class TabularParser:
    def supports(self, filename: str, content_type: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in {".csv", ".xlsx", ".xls"} or any(
            token in (content_type or "").lower()
            for token in ("csv", "spreadsheet", "excel")
        )

    def parse(self, data: bytes, filename: str) -> str:
        ext = Path(filename).suffix.lower()
        if ext == ".csv":
            frame = pd.read_csv(BytesIO(data))
            return self._frame_to_markdown(filename, frame)
        frame_dict = pd.read_excel(BytesIO(data), sheet_name=None)
        sections = [f"# {filename}"]
        for sheet_name, frame in frame_dict.items():
            sections.append(self._frame_to_markdown(str(sheet_name), frame, heading_level=2))
        return "\n\n".join(sections)

    @staticmethod
    def _frame_to_markdown(title: str, frame: pd.DataFrame, heading_level: int = 1) -> str:
        heading = "#" * heading_level
        if frame.empty:
            return f"{heading} {title}\n\n_No rows_"
        preview = frame.head(200)
        try:
            table = preview.to_markdown(index=False)
        except ImportError:
            table = preview.to_string(index=False)
        return f"{heading} {title}\n\n{table}"
