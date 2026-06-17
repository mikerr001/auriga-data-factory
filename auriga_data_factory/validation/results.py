"""
Auriga Data Factory — Validation Result Types
==============================================
Data structures representing the outcome of validation checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationStatus(str, Enum):
    """Outcome category for a single validation check."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ValidationResult:
    """
    Result of a single validation check.

    Attributes
    ----------
    check_name:
        Human-readable name of the check, e.g. ``"schema_validation"``.
    status:
        PASS, WARNING, or FAIL.
    message:
        Concise description of the outcome.
    details:
        Optional structured data (e.g. list of offending sample IDs).
    affected_samples:
        List of sample IDs implicated in a failure or warning.
    """

    check_name: str
    status: ValidationStatus
    message: str
    details: Optional[Any] = None
    affected_samples: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status == ValidationStatus.FAIL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "affected_samples": self.affected_samples,
        }


@dataclass
class ValidationReport:
    """
    Aggregated result of a full validation run over a dataset.

    Attributes
    ----------
    dataset_id:
        ID of the validated dataset.
    dataset_name:
        Human-readable name.
    dataset_version:
        Version string.
    results:
        Individual check results.
    validated_at:
        ISO-8601 timestamp of validation.
    """

    dataset_id: str
    dataset_name: str
    dataset_version: str
    results: List[ValidationResult] = field(default_factory=list)
    validated_at: str = ""

    @property
    def overall_status(self) -> ValidationStatus:
        """
        Derive overall status from individual results.

        Rules:
            - Any FAIL → overall FAIL.
            - Any WARNING (with no FAIL) → overall WARNING.
            - All PASS → overall PASS.
        """
        statuses = {r.status for r in self.results}
        if ValidationStatus.FAIL in statuses:
            return ValidationStatus.FAIL
        if ValidationStatus.WARNING in statuses:
            return ValidationStatus.WARNING
        return ValidationStatus.PASS

    @property
    def passed(self) -> bool:
        return self.overall_status == ValidationStatus.PASS

    @property
    def failed(self) -> bool:
        return self.overall_status == ValidationStatus.FAIL

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.failed)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.status == ValidationStatus.WARNING)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "validated_at": self.validated_at,
            "overall_status": self.overall_status.value,
            "pass_count": self.pass_count,
            "warning_count": self.warning_count,
            "fail_count": self.fail_count,
            "results": [r.to_dict() for r in self.results],
        }

    def as_text(self) -> str:
        """Render a human-readable validation report."""
        lines = [
            "=" * 60,
            f"VALIDATION REPORT — {self.dataset_name} v{self.dataset_version}",
            f"Dataset ID : {self.dataset_id}",
            f"Validated  : {self.validated_at}",
            f"Overall    : {self.overall_status.value}",
            f"Results    : {self.pass_count} PASS / {self.warning_count} WARN / {self.fail_count} FAIL",
            "=" * 60,
        ]
        for r in self.results:
            icon = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗"}.get(r.status.value, "?")
            lines.append(f"  {icon} [{r.status.value:7}] {r.check_name}")
            lines.append(f"          {r.message}")
            if r.affected_samples:
                preview = r.affected_samples[:5]
                extra = len(r.affected_samples) - 5
                suffix = f" (+{extra} more)" if extra > 0 else ""
                lines.append(f"          Affected: {preview}{suffix}")
        lines.append("=" * 60)
        return "\n".join(lines)
