"""Unit tests for TabularParser."""

from __future__ import annotations

import io

import openpyxl
import pandas as pd
import pytest

from stratiq.domain.exceptions import ProcessingError
from stratiq.infrastructure.parsers.tabular_parser import TabularParser


def _make_excel(data: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in data:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_csv(rows: list[list]) -> bytes:
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df.to_csv(index=False).encode()


class TestTabularParserExcel:
    def test_parses_simple_xlsx(self):
        data = [["Name", "Revenue", "Growth"], ["ACME", "1000000", "15%"], ["Beta", "500000", "8%"]]
        raw = _make_excel(data)
        parser = TabularParser("xlsx")
        result = parser.parse(raw)
        assert "Name" in result
        assert "ACME" in result
        assert "Revenue" in result

    def test_returns_markdown_table(self):
        data = [["A", "B"], [1, 2], [3, 4]]
        raw = _make_excel(data)
        parser = TabularParser("xlsx")
        result = parser.parse(raw)
        assert "|" in result

    def test_empty_rows_dropped(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Col1", "Col2"])
        ws.append([None, None])
        ws.append(["val", "val2"])
        buf = io.BytesIO()
        wb.save(buf)
        parser = TabularParser("xlsx")
        result = parser.parse(buf.getvalue())
        assert "val" in result


class TestTabularParserCSV:
    def test_parses_simple_csv(self):
        data = [["Country", "GDP"], ["USA", "25000"], ["Germany", "4000"]]
        raw = _make_csv(data)
        parser = TabularParser("csv")
        result = parser.parse(raw)
        assert "Country" in result
        assert "USA" in result

    def test_csv_is_markdown(self):
        data = [["X", "Y"], [1, 2]]
        raw = _make_csv(data)
        parser = TabularParser("csv")
        result = parser.parse(raw)
        assert "|" in result


class TestTabularParserErrors:
    def test_unsupported_extension_raises(self):
        parser = TabularParser("docx")
        with pytest.raises(ProcessingError, match="Unsupported"):
            parser.parse(b"some bytes")

    def test_invalid_excel_bytes_raises(self):
        parser = TabularParser("xlsx")
        with pytest.raises(ProcessingError):
            parser.parse(b"not an excel file at all!!!!")
