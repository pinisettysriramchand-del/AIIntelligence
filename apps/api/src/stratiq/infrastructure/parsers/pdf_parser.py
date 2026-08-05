"""PDF parser – converts PDF bytes to markdown-ish text using pypdf."""

from __future__ import annotations

import io
import logging

from pypdf import PdfReader

from stratiq.domain.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class PDFParser:
    """Parse PDF files into plain markdown text."""

    def parse(self, data: bytes) -> str:
        try:
            reader = PdfReader(io.BytesIO(data))
            pages: list[str] = []
            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"## Page {page_num}\n\n{text.strip()}")
            result = "\n\n".join(pages)
            logger.debug("PDF parsed", extra={"pages": len(pages), "chars": len(result)})
            return result
        except Exception as exc:
            raise ProcessingError(f"PDF parsing failed: {exc}") from exc
