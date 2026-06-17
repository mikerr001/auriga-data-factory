"""
Auriga Data Factory — Report Generator
Combines validation and coverage results into a human-ready dataset report.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from factory.validation.validator import ValidationResult
from factory.coverage.coverage_analyzer import CoverageResult


class ReportGenerator:
    """
    Generates the final dataset report by combining:
      - ValidationResult (from Validator)
      - CoverageResult (from CoverageAnalyzer)

    Output: Markdown report conforming to DATASET_REPORT_TEMPLATE.md.
    """

    def generate(
        self,
        dataset_version: str,
        validation_result: ValidationResult,
        coverage_result: CoverageResult,
        collection_notes: Optional[str] = None,
        reports_dir: str = "reports",
    ) -> str:
        """
        Generate and save the full dataset report.
        Returns the path to the saved markdown report.
        """
        os.makedirs(reports_dir, exist_ok=True)
        report_path = os.path.join(reports_dir, f"{dataset_version}_report.md")

        content = self._build_report(
            dataset_version, validation_result, coverage_result, collection_notes
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(content)

        return report_path

    def _build_report(
        self,
        dataset_version: str,
        vr: ValidationResult,
        cr: CoverageResult,
        collection_notes: Optional[str],
    ) -> str:
        now = datetime.now(timezone.utc).isoformat()
        lines = [
            f"# DATASET REPORT",
            f"# {dataset_version}",
            f"",
            f"**Report generated:** {now}",
            f"**Report version:** 1.0",
            f"**Template version:** 1.0.0",
            f"**Schema version:** {vr.schema_version}",
            f"**Report status:** READY FOR REVIEW",
            f"",
            f"---",
            f"",
            f"## Section 1 — Dataset Identity",
            f"",
            f"| Field | Value |",
            f"|---|---|",
            f"| Dataset version | `{dataset_version}` |",
            f"| Record count | `{vr.record_count}` |",
            f"| Creation date | `{now[:10]}` |",
            f"| Supersedes | *(fill in)* |",
            f"",
            f"---",
            f"",
            f"## Section 2 — Collection Summary",
            f"",
        ]
        if collection_notes:
            lines += [collection_notes, ""]
        else:
            lines += ["*(Collection notes not provided — fill in manually.)*", ""]

        # Section 3 — Validation
        lines += [
            f"---",
            f"",
            f"## Section 3 — Validation Results",
            f"",
            f"### 3.1 Overall Validation Status",
            f"",
            f"**RESULT: {vr.overall_status}**",
            f"",
            f"### 3.2 Layer Results",
            f"",
            f"| Layer | Status | Issues |",
            f"|---|---|---|",
        ]
        for lr in vr.layer_results:
            lines.append(f"| {lr.layer_name} | {lr.status} | {lr.issue_count} |")

        if vr.human_review_items:
            lines += ["", "### 3.3 Items Requiring Human Review", ""]
            for i, item in enumerate(vr.human_review_items, 1):
                lines.append(f"{i}. {item}")

        # Section 4 — Coverage
        lines += [
            f"",
            f"---",
            f"",
            f"## Section 4 — Coverage Analysis",
            f"",
            f"**Overall Coverage Score: {cr.coverage_score}%**",
            f"",
            cr.to_markdown(),
        ]

        # Section 7 — Known Limitations (placeholder)
        lines += [
            f"",
            f"---",
            f"",
            f"## Section 7 — Known Limitations",
            f"",
            f"*(Fill in before human review — be complete and honest.)*",
            f"",
            f"---",
            f"",
            f"## Section 10 — Human Review Decision",
            f"",
            f"| Field | Value |",
            f"|---|---|",
            f"| Reviewer | *(Project Lead)* |",
            f"| Review date | *(fill in)* |",
            f"| Decision | **PENDING HUMAN APPROVAL** |",
            f"| Approval notes | *(fill in)* |",
            f"| Known limitations acknowledged | *(Yes / No)* |",
            f"| Research debt acknowledged | *(Yes / No)* |",
        ]

        return "\n".join(lines)
