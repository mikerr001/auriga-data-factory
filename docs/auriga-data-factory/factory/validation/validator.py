"""
Auriga Data Factory — Validation Orchestrator
Runs all 7 validation layers and produces a structured report.

See DATA_VALIDATION_PROTOCOL.md for full specification.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .schema_validator import SchemaValidator
from .completeness_checker import CompletenessChecker
from .duplicate_detector import DuplicateDetector
from .consistency_checker import ConsistencyChecker
from .outlier_detector import OutlierDetector

logger = logging.getLogger(__name__)


@dataclass
class LayerResult:
    layer_name: str
    is_blocking: bool
    status: str          # "PASS", "FAIL", "ADVISORY"
    issues: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def passed(self) -> bool:
        return self.status in ("PASS", "ADVISORY")


@dataclass
class ValidationResult:
    dataset_version: str
    schema_version: str
    record_count: int
    generated_at: str
    layer_results: List[LayerResult]
    overall_status: str           # "PASS" or "FAIL"
    human_review_items: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "datasetVersion": self.dataset_version,
            "schemaVersion": self.schema_version,
            "recordCount": self.record_count,
            "generatedAt": self.generated_at,
            "overallResult": self.overall_status,
            "layerResults": {
                lr.layer_name: {
                    "status": lr.status,
                    "issueCount": lr.issue_count,
                    "issues": lr.issues,
                }
                for lr in self.layer_results
            },
            "humanReviewItems": self.human_review_items,
            "recommendations": self.recommendations,
        }

    def save_report(self, reports_dir: str) -> None:
        """Write markdown and JSON reports to reports_dir."""
        os.makedirs(reports_dir, exist_ok=True)

        json_path = os.path.join(
            reports_dir, f"{self.dataset_version}_validation_report.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        md_path = os.path.join(
            reports_dir, f"{self.dataset_version}_validation_report.md"
        )
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._to_markdown())

        logger.info(f"Validation reports written to {reports_dir}")

    def _to_markdown(self) -> str:
        lines = [
            f"# Validation Report: {self.dataset_version}",
            f"",
            f"**Generated:** {self.generated_at}",
            f"**Schema version:** {self.schema_version}",
            f"**Record count:** {self.record_count}",
            f"**Overall result:** {self.overall_status}",
            f"",
            f"---",
            f"",
            f"## Layer Summary",
            f"",
            f"| Layer | Status | Issues |",
            f"|---|---|---|",
        ]
        for lr in self.layer_results:
            lines.append(f"| {lr.layer_name} | {lr.status} | {lr.issue_count} |")

        if self.human_review_items:
            lines += ["", "## Items Requiring Human Review", ""]
            for i, item in enumerate(self.human_review_items, 1):
                lines.append(f"{i}. {item}")

        if self.recommendations:
            lines += ["", "## Recommendations", ""]
            for r in self.recommendations:
                lines.append(f"- {r}")

        # Blocking issues detail
        blocking_issues = []
        for lr in self.layer_results:
            if lr.is_blocking and lr.issues:
                blocking_issues.extend(lr.issues)

        if blocking_issues:
            lines += ["", "## Blocking Issues", ""]
            for issue in blocking_issues:
                lines.append(
                    f"- **[{issue.get('layer', '?')}]** "
                    f"Record `{issue.get('recordId', '?')}` — "
                    f"{issue.get('issue', '?')}: {issue.get('detail', '')}"
                )

        return "\n".join(lines)


class Validator:
    """
    Orchestrates all 7 validation layers against a staged dataset.

    Usage:
        validator = Validator()
        result = validator.validate(
            records=my_records,
            dataset_version="fiducials_aruco_v3",
            dataset_path="datasets/staged/fiducials_aruco_v3/"
        )
        result.save_report("reports/")
    """

    SCHEMA_VERSION = "canonical_v1"

    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.completeness_checker = CompletenessChecker()
        self.duplicate_detector = DuplicateDetector()
        self.consistency_checker = ConsistencyChecker()
        self.outlier_detector = OutlierDetector()

    def validate(
        self,
        records: List[Dict[str, Any]],
        dataset_version: str,
        dataset_path: Optional[str] = None,
    ) -> ValidationResult:
        """
        Run all 7 validation layers against the provided records.

        Args:
            records: List of normalized canonical schema records.
            dataset_version: Version string (e.g., 'fiducials_aruco_v3').
            dataset_path: Base path for image file existence checks (Layer 3).

        Returns:
            ValidationResult with full layer-by-layer findings.
        """
        generated_at = datetime.now(timezone.utc).isoformat()
        layer_results: List[LayerResult] = []
        human_review_items: List[str] = []
        recommendations: List[str] = []

        logger.info(f"Starting validation: {dataset_version} ({len(records)} records)")

        # --- Layer 1: Schema Validation (BLOCKING) ---
        schema_issues = self.schema_validator.check(records)
        layer_results.append(LayerResult(
            layer_name="1. Schema Validation",
            is_blocking=True,
            status="PASS" if not schema_issues else "FAIL",
            issues=schema_issues,
        ))

        # --- Layer 2: Completeness Check (BLOCKING) ---
        completeness_issues = self.completeness_checker.check(records)
        layer_results.append(LayerResult(
            layer_name="2. Completeness Check",
            is_blocking=True,
            status="PASS" if not completeness_issues else "FAIL",
            issues=completeness_issues,
        ))

        # --- Layer 3: File Integrity (BLOCKING) ---
        if dataset_path:
            from .file_integrity_checker import FileIntegrityChecker
            integrity_checker = FileIntegrityChecker(base_path=dataset_path)
            integrity_issues = integrity_checker.check(records)
        else:
            integrity_issues = []
            recommendations.append(
                "Layer 3 (File Integrity) skipped — no dataset_path provided. "
                "Pass dataset_path to enable image file existence checks."
            )
        layer_results.append(LayerResult(
            layer_name="3. File Integrity",
            is_blocking=True,
            status="PASS" if not integrity_issues else "FAIL",
            issues=integrity_issues,
        ))

        # --- Layer 4: Duplicate Detection (BLOCKING) ---
        duplicate_issues = self.duplicate_detector.check(records)
        layer_results.append(LayerResult(
            layer_name="4. Duplicate Detection",
            is_blocking=True,
            status="PASS" if not duplicate_issues else "FAIL",
            issues=duplicate_issues,
        ))

        # --- Layer 5: Consistency Check (BLOCKING) ---
        consistency_issues = self.consistency_checker.check(records)
        layer_results.append(LayerResult(
            layer_name="5. Consistency Check",
            is_blocking=True,
            status="PASS" if not consistency_issues else "FAIL",
            issues=consistency_issues,
        ))

        # --- Layer 6: Outlier Detection (ADVISORY) ---
        outlier_findings = self.outlier_detector.check(records)
        layer_results.append(LayerResult(
            layer_name="6. Outlier Detection",
            is_blocking=False,
            status="ADVISORY" if outlier_findings else "PASS",
            issues=outlier_findings,
        ))
        if outlier_findings:
            human_review_items.append(
                f"{len(outlier_findings)} statistical outlier(s) flagged. "
                f"Review each flagged record and provide a disposition in the approval record."
            )

        # --- Layer 7: Coverage Analysis (ADVISORY) ---
        # Coverage analysis is invoked via the CoverageAnalyzer separately.
        # The validator records a placeholder result; the full coverage report
        # is attached by the reporting subsystem.
        layer_results.append(LayerResult(
            layer_name="7. Coverage Analysis",
            is_blocking=False,
            status="ADVISORY",
            issues=[{"note": "See coverage report for gap details."}],
        ))
        human_review_items.append(
            "Review coverage gaps identified in the coverage analysis report."
        )

        # --- Overall result ---
        blocking_failed = any(
            not lr.passed for lr in layer_results if lr.is_blocking
        )
        overall_status = "FAIL" if blocking_failed else "PASS"

        logger.info(f"Validation complete: {dataset_version} → {overall_status}")

        return ValidationResult(
            dataset_version=dataset_version,
            schema_version=self.SCHEMA_VERSION,
            record_count=len(records),
            generated_at=generated_at,
            layer_results=layer_results,
            overall_status=overall_status,
            human_review_items=human_review_items,
            recommendations=recommendations,
        )
