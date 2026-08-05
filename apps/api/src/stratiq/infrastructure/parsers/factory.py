"""Parser factory – selects the correct parser based on MIME type or file extension."""

from __future__ import annotations

from stratiq.domain.exceptions import ProcessingError
from stratiq.infrastructure.parsers.base import DocumentParser
from stratiq.infrastructure.parsers.pdf_parser import PDFParser
from stratiq.infrastructure.parsers.tabular_parser import TabularParser

_MIME_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "text/csv": "csv",
    "application/csv": "csv",
}

_EXT_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".csv": "csv",
}


class ParserFactory:
    def get_parser(self, mime_type: str, filename: str) -> DocumentParser:
        kind = _MIME_MAP.get(mime_type)
        if kind is None:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            kind = _EXT_MAP.get(ext)

        if kind == "pdf":
            return PDFParser()
        elif kind in ("xlsx", "xls", "csv"):
            ext = kind
            return TabularParser(file_extension=ext)
        else:
            raise ProcessingError(
                f"No parser available for mime_type='{mime_type}', filename='{filename}'. "
                "Supported: PDF, XLSX, XLS, CSV."
            )
