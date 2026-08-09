"""Data quality detection for KPIs (Part 4 §26)."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from stratiq.domain.entities import KPI
from stratiq.domain.enums import DataQualityCode
from stratiq.application.kpi_intelligence import parse_numeric

_PERIOD_OK = re.compile(
    r"^("
    r"\d{4}"  # 2024
    r"|Q[1-4]\s*\d{4}"  # Q1 2024
    r"|\d{4}\s*[-/]?\s*Q[1-4]"  # 2024-Q1
    r"|\d{4}\s*[-/]\s*\d{1,2}"  # 2024-01
    r"|FY\s*\d{2,4}"  # FY24
    r"|H[12]\s*\d{4}"  # H1 2024
    r"|[A-Za-z]{3,9}\s+\d{4}"  # Jan 2024
    r")$",
    re.IGNORECASE,
)


def detect_kpi_quality_issues(
    kpis: list[KPI],
    *,
    existing_kpis: list[KPI] | None = None,
) -> list[dict[str, Any]]:
    """Return structured data-quality warnings for a KPI set."""
    warnings: list[dict[str, Any]] = []
    pool = list(kpis)
    history = list(existing_kpis or []) + pool

    for kpi in kpis:
        if not str(kpi.value or "").strip():
            warnings.append(
                _warn(
                    DataQualityCode.missing_value,
                    f"KPI '{kpi.name}' has a missing value.",
                    kpi_name=kpi.name,
                )
            )
        if not (kpi.period and str(kpi.period).strip()):
            warnings.append(
                _warn(
                    DataQualityCode.missing_period,
                    f"KPI '{kpi.name}' has no reporting period.",
                    kpi_name=kpi.name,
                )
            )
        elif not _PERIOD_OK.match(str(kpi.period).strip()):
            warnings.append(
                _warn(
                    DataQualityCode.invalid_period,
                    f"KPI '{kpi.name}' has an invalid or unrecognized period '{kpi.period}'.",
                    kpi_name=kpi.name,
                )
            )
        if parse_numeric(kpi.value) is not None and not (kpi.unit and str(kpi.unit).strip()):
            warnings.append(
                _warn(
                    DataQualityCode.missing_unit,
                    f"KPI '{kpi.name}' looks numeric but has no unit.",
                    kpi_name=kpi.name,
                    severity="warning",
                )
            )

    # Duplicates within the new set: same name+period+unit+value
    seen: dict[tuple[str, str, str, str], int] = defaultdict(int)
    for kpi in kpis:
        key = (
            kpi.name.strip().lower(),
            (kpi.period or "").strip().lower(),
            (kpi.unit or "").strip().lower(),
            str(kpi.value).strip().lower(),
        )
        seen[key] += 1
    for key, count in seen.items():
        if count > 1:
            warnings.append(
                _warn(
                    DataQualityCode.duplicate_record,
                    f"Duplicate KPI records for '{key[0]}' period '{key[1] or 'n/a'}' ({count} copies).",
                    kpi_name=key[0],
                )
            )

    # Inconsistent units for same KPI name
    units_by_name: dict[str, set[str]] = defaultdict(set)
    for kpi in history:
        if kpi.unit and str(kpi.unit).strip():
            units_by_name[kpi.name.strip().lower()].add(str(kpi.unit).strip().lower())
    for name, units in units_by_name.items():
        if len(units) > 1:
            warnings.append(
                _warn(
                    DataQualityCode.inconsistent_units,
                    f"KPI '{name}' uses inconsistent units: {', '.join(sorted(units))}.",
                    kpi_name=name,
                )
            )

    # Conflicting values: same name+period+unit, different values
    conflict_map: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for kpi in history:
        conflict_map[
            (
                kpi.name.strip().lower(),
                (kpi.period or "").strip().lower(),
                (kpi.unit or "").strip().lower(),
            )
        ].add(str(kpi.value).strip())
    for key, values in conflict_map.items():
        if len(values) > 1:
            warnings.append(
                _warn(
                    DataQualityCode.conflicting_values,
                    f"Conflicting values for '{key[0]}' period '{key[1] or 'n/a'}': {', '.join(sorted(values))}.",
                    kpi_name=key[0],
                )
            )

    # Insufficient history for trend (only one observation for name+unit)
    hist_counts: dict[tuple[str, str], int] = defaultdict(int)
    for kpi in history:
        hist_counts[(kpi.name.strip().lower(), (kpi.unit or "").strip().lower())] += 1
    reported: set[str] = set()
    for kpi in kpis:
        key = (kpi.name.strip().lower(), (kpi.unit or "").strip().lower())
        if hist_counts[key] < 2 and key[0] not in reported:
            reported.add(key[0])
            warnings.append(
                _warn(
                    DataQualityCode.insufficient_history,
                    f"Insufficient history for '{kpi.name}' to compute a reliable trend.",
                    kpi_name=kpi.name,
                    severity="info",
                )
            )

    return _dedupe(warnings)


def _warn(
    code: DataQualityCode,
    message: str,
    *,
    kpi_name: str | None = None,
    severity: str = "warning",
) -> dict[str, Any]:
    return {
        "code": code.value,
        "message": message,
        "kpi_name": kpi_name,
        "severity": severity,
    }


def _dedupe(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for w in warnings:
        key = (w["code"], w.get("kpi_name") or "", w["message"])
        if key in seen:
            continue
        seen.add(key)
        out.append(w)
    return out
