from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


class PdfParser:
    def supports(self, filename: str, content_type: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext == ".pdf" or "pdf" in (content_type or "").lower()

    def parse(self, data: bytes, filename: str) -> str:
        reader = PdfReader(BytesIO(data))
        pages: list[str] = []
        for index, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(f"## Page {index + 1}\n\n{text}")
        return f"# {filename}\n\n" + "\n\n".join(pages)
