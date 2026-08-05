"""Tabular file parser – converts XLSX/CSV to markdown tables."""

from __future__ import annotations

import io
import logging

import pandas as pd

from stratiq.domain.exceptions import ProcessingError

logger = logging.getLogger(__name__)

_MAX_ROWS_PER_SHEET = 200


class TabularParser:
    """Parse Excel (.xlsx, .xls) and CSV files into markdown."""

    def __init__(self, file_extension: str) -> None:
        self._ext = file_extension.lower().lstrip(".")

    def parse(self, data: bytes) -> str:
        try:
            if self._ext in ("xlsx", "xls"):
                return self._parse_excel(data)
            elif self._ext == "csv":
                return self._parse_csv(data)
            else:
                raise ProcessingError(f"Unsupported tabular format: {self._ext}")
        except ProcessingError:
            raise
        except Exception as exc:
            raise ProcessingError(f"Tabular parsing failed: {exc}") from exc

    def _parse_excel(self, data: bytes) -> str:
        xf = pd.ExcelFile(io.BytesIO(data))
        sections: list[str] = []
        for sheet_name in xf.sheet_names:
            df = pd.read_excel(xf, sheet_name=sheet_name, nrows=_MAX_ROWS_PER_SHEET)
            df = df.dropna(how="all")
            md = df.to_markdown(index=False)
            sections.append(f"## Sheet: {sheet_name}\n\n{md}")
        result = "\n\n".join(sections)
        logger.debug("Excel parsed", extra={"sheets": len(sections), "chars": len(result)})
        return result

    def _parse_csv(self, data: bytes) -> str:
        df = pd.read_csv(io.BytesIO(data), nrows=_MAX_ROWS_PER_SHEET)
        df = df.dropna(how="all")
        result = df.to_markdown(index=False)
        logger.debug("CSV parsed", extra={"rows": len(df), "chars": len(result)})
        return result or ""
