"""Stage 4H: executive L1/L2/L3 UI + chart components exist."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
WEB = ROOT / "apps" / "web"


def test_l1_l2_l3_dashboard_markers():
    dashboard = (WEB / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
    for needle in (
        "Level 1 — Executive Signal",
        "Level 2 — Explanation",
        "Level 3 — Action",
        "SparkLine",
        "RankedBarChart",
        "HealthMeter",
    ):
        assert needle in dashboard, f"dashboard missing: {needle}"


def test_chart_components_exist():
    for rel in (
        "components/charts/SparkLine.tsx",
        "components/charts/BarChart.tsx",
        "components/charts/HealthMeter.tsx",
        "lib/charts.ts",
    ):
        assert (WEB / rel).is_file(), f"missing {rel}"


def test_decision_detail_has_layers_and_forecast_chart():
    page = (WEB / "app" / "decisions" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    assert "Level 3 — Action" in page
    assert "Level 2 — Explanation" in page
    assert "SparkLine" in page
