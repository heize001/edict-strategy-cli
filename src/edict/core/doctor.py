from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DoctorReport:
    ok: bool
    issues: list[str]


def _is_poetry_project(root: Path) -> bool:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return False
    txt = pyproject.read_text(encoding="utf-8")
    return "[build-system]" in txt


def _has_strategy_layout(root: Path) -> bool:
    return (root / "src" / "strategies").exists() or (root / "src" / "edict").exists()


def run_doctor(root: Path) -> DoctorReport:
    issues: list[str] = []

    if not _is_poetry_project(root):
        issues.append("Missing pyproject.toml (Poetry/Python project not detected)")

    if not _has_strategy_layout(root):
        issues.append("Missing src/strategies or src/edict (no strategy/code layout detected)")

    # Python version checks are intentionally omitted here because this code
    # runs inside the current interpreter anyway.

    return DoctorReport(ok=(len(issues) == 0), issues=issues)
