from pathlib import Path

from stratiq.domain.exceptions import ValidationError
from stratiq.infrastructure.parsers.pdf_parser import PdfParser
from stratiq.infrastructure.parsers.tabular_parser import TabularParser


def get_parser(filename: str, content_type: str):
    parsers = [PdfParser(), TabularParser()]
    for parser in parsers:
        if parser.supports(filename, content_type):
            return parser
    raise ValidationError(f"No parser for {Path(filename).suffix} ({content_type})")
