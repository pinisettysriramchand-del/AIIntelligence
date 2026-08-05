from stratiq.infrastructure.parsers.tabular_parser import TabularParser


def test_csv_parser_produces_markdown():
    data = b"kpi,value\nRevenue,100\nMargin,12.5\n"
    parser = TabularParser()
    assert parser.supports("sales.csv", "text/csv")
    markdown = parser.parse(data, "sales.csv")
    assert "Revenue" in markdown
    assert "100" in markdown
