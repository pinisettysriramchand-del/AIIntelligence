"""Stage 4G: DR runbook presence and required content."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_dr_runbook_defines_rpo_rto_and_procedures():
    path = ROOT / "docs" / "ops" / "DR_RUNBOOK.md"
    assert path.is_file(), "docs/ops/DR_RUNBOOK.md missing"
    text = path.read_text(encoding="utf-8")
    for needle in (
        "RPO",
        "RTO",
        "PostgreSQL",
        "Object storage",
        "Configuration",
        "backup-postgres",
        "restore-postgres",
        "dead_letter",
        "alembic upgrade head",
    ):
        assert needle in text, f"DR runbook missing required mention: {needle}"


def test_backup_scripts_exist():
    scripts = ROOT / "scripts"
    for name in (
        "backup-postgres.ps1",
        "backup-postgres.sh",
        "restore-postgres.ps1",
        "restore-postgres.sh",
        "backup-config.ps1",
    ):
        assert (scripts / name).is_file(), f"missing script {name}"
