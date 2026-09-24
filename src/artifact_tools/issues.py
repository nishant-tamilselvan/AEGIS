"""Validation findings shared by the artifact, ADR and implementation validators.

Kept in its own module so the validators can import it without importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Issue:
    """A single validation finding."""

    severity: str  # "error" | "warning"
    file: str
    message: str

    def format(self) -> str:
        return f"[{self.severity.upper()}] {self.file}: {self.message}"


def has_errors(issues: list[Issue], *, strict: bool = False) -> bool:
    """Return True when validation should be considered failed."""
    for issue in issues:
        if issue.severity == "error":
            return True
        if strict and issue.severity == "warning":
            return True
    return False
