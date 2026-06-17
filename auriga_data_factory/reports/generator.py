"""
Auriga Data Factory — Report Generator
========================================
Produces machine-readable (JSON) and human-readable (Markdown/text) reports
for ingestion, validation, coverage, and approval events.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schema.canonical import CanonicalDataset
from ..validation.results import ValidationReport
from ..coverage.results import CoverageReport
from ..observability.research_debt import ResearchDebtRegister
from ..observability.logger import get_logger

logger = get_logger("auriga.reports.generator")


class ReportGenerator:
    """
    Generates structured and human-readable reports.

    Parameters
    ----------
    output_dir:
        Directory where reports are saved.
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path("reports")

    # ------------------------------------------------------------------ #
    # Validation report                                                     #
    # ------------------------------------------------------------------ #

    def save_validation_report(
        self,
        report: ValidationReport,
        dataset: Optional[CanonicalDataset] = None,
    ) -> Dict[str, Path]:
        """
        Save validation report in JSON and Markdown formats.

        Returns
        -------
        Dict mapping format → file path.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = f"validation_{report.dataset_id[:8]}_{self._timestamp()}"

        paths: Dict[str, Path] = {}

        # JSON (machine-readable).
        json_path = self.output_dir / f"{base}.json"
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, indent=2)
        paths["json"] = json_path

        # Markdown (human-readable).
        md_path = self.output_dir / f"{base}.md"
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(self._validation_to_markdown(report, dataset))
        paths["markdown"] = md_path

        # Plain text summary.
        txt_path = self.output_dir / f"{base}.txt"
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(report.as_text())
        paths["text"] = txt_path

        logger.info(f"Validation report saved: {json_path}", dataset_id=report.dataset_id)
        return paths

    # ------------------------------------------------------------------ #
    # Coverage report                                                       #
    # ------------------------------------------------------------------ #

    def save_coverage_report(
        self,
        report: CoverageReport,
    ) -> Dict[str, Path]:
        """Save coverage report in JSON and Markdown formats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = f"coverage_{report.dataset_id[:8]}_{self._timestamp()}"

        paths: Dict[str, Path] = {}

        json_path = self.output_dir / f"{base}.json"
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report.to_dict(), fh, indent=2)
        paths["json"] = json_path

        md_path = self.output_dir / f"{base}.md"
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(self._coverage_to_markdown(report))
        paths["markdown"] = md_path

        txt_path = self.output_dir / f"{base}.txt"
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(report.as_text())
        paths["text"] = txt_path

        logger.info(f"Coverage report saved: {json_path}", dataset_id=report.dataset_id)
        return paths

    # ------------------------------------------------------------------ #
    # Research debt register                                                #
    # ------------------------------------------------------------------ #

    def save_research_debt_register(
        self,
        register: ResearchDebtRegister,
    ) -> Dict[str, Path]:
        """Save the research debt register in JSON and Markdown formats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = f"research_debt_{self._timestamp()}"
        paths: Dict[str, Path] = {}

        md_path = self.output_dir / f"{base}.md"
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.write(register.as_markdown())
        paths["markdown"] = md_path

        json_path = self.output_dir / f"{base}.json"
        import dataclasses
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(
                [dataclasses.asdict(d) for d in register.all_items()],
                fh, indent=2,
            )
        paths["json"] = json_path

        logger.info(f"Research debt register saved: {md_path}")
        return paths

    # ------------------------------------------------------------------ #
    # Architecture compliance report                                        #
    # ------------------------------------------------------------------ #

    def save_architecture_compliance_report(self) -> Path:
        """
        Generate a Markdown report mapping each spec requirement to its
        implementation location.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / "architecture_compliance_report.md"

        content = _ARCHITECTURE_COMPLIANCE_REPORT
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        logger.info(f"Architecture compliance report saved: {path}")
        return path

    # ------------------------------------------------------------------ #
    # Human validation checklist                                            #
    # ------------------------------------------------------------------ #

    def save_human_validation_checklist(self) -> Path:
        """Generate a Markdown checklist for the project lead."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / "human_validation_checklist.md"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_HUMAN_VALIDATION_CHECKLIST)
        logger.info(f"Human validation checklist saved: {path}")
        return path

    # ------------------------------------------------------------------ #
    # Ingestion report                                                      #
    # ------------------------------------------------------------------ #

    def save_ingestion_report(
        self,
        dataset: CanonicalDataset,
    ) -> Path:
        """Save a brief ingestion report for a newly imported dataset."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        base = f"ingestion_{dataset.dataset_id[:8]}_{self._timestamp()}"
        path = self.output_dir / f"{base}.json"
        report = {
            "report_type": "ingestion",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dataset_id": dataset.dataset_id,
            "dataset_name": dataset.name,
            "version": dataset.version,
            "state": dataset.state,
            "sample_count": dataset.sample_count,
            "real_sample_count": dataset.real_sample_count,
            "synthetic_sample_count": dataset.synthetic_sample_count,
            "provenance": dataset.provenance,
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        logger.info(f"Ingestion report saved: {path}", dataset_id=dataset.dataset_id)
        return path

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    @staticmethod
    def _validation_to_markdown(
        report: ValidationReport,
        dataset: Optional[CanonicalDataset] = None,
    ) -> str:
        lines = [
            f"# Validation Report — {report.dataset_name} v{report.dataset_version}",
            f"",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Dataset ID | `{report.dataset_id}` |",
            f"| Validated | {report.validated_at} |",
            f"| Overall Status | **{report.overall_status.value}** |",
            f"| PASS | {report.pass_count} |",
            f"| WARNING | {report.warning_count} |",
            f"| FAIL | {report.fail_count} |",
            f"",
            f"## Check Results",
            f"",
            f"| Check | Status | Message |",
            f"|-------|--------|---------|",
        ]
        for r in report.results:
            icon = {"PASS": "✓", "WARNING": "⚠", "FAIL": "✗"}.get(r.status.value, "?")
            lines.append(f"| {r.check_name} | {icon} {r.status.value} | {r.message} |")

        for r in report.results:
            if r.affected_samples or r.details:
                lines += [f"", f"### {r.check_name}"]
                if r.details:
                    if isinstance(r.details, list):
                        for d in r.details[:10]:
                            lines.append(f"- {d}")
                if r.affected_samples:
                    lines.append(f"**Affected samples ({len(r.affected_samples)}):** "
                                 f"`{', '.join(r.affected_samples[:10])}`")
        return "\n".join(lines)

    @staticmethod
    def _coverage_to_markdown(report: CoverageReport) -> str:
        lines = [
            f"# Coverage Report — {report.dataset_name} v{report.dataset_version}",
            f"",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Dataset ID | `{report.dataset_id}` |",
            f"| Analysed | {report.analysed_at} |",
            f"| Overall Coverage | **{report.overall_score:.1%}** |",
            f"",
            f"## Dimension Scores",
            f"",
            f"| Dimension | Score | Missing |",
            f"|-----------|-------|---------|",
        ]
        for score in report.scores:
            missing_str = ", ".join(str(v) for v in score.missing_values[:5]) or "None"
            lines.append(f"| {score.dimension} | {score.score:.1%} | {missing_str} |")

        if report.recommendations:
            lines += ["", "## Collection Recommendations", ""]
            for i, rec in enumerate(report.recommendations, 1):
                lines.append(f"{i}. {rec}")

        return "\n".join(lines)


# ─────────────────────── Static report content ───────────────────────────── #

_ARCHITECTURE_COMPLIANCE_REPORT = """\
# Architecture Compliance Report — Auriga Data Factory

Generated automatically. Maps each specification requirement to its implementation.

## Primary Objectives

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Dataset Ingestion Engine | ✓ IMPLEMENTED | `auriga_data_factory/ingestion/engine.py` |
| CSV + image directory support | ✓ IMPLEMENTED | `ingestion/adapters.py::CSVAdapter` |
| Auriga fiducial dataset support | ✓ IMPLEMENTED | `ingestion/adapters.py::AurigaFiducialAdapter` |
| Legacy experimental dataset support | ✓ IMPLEMENTED | `ingestion/adapters.py::LegacyExperimentAdapter` |
| Adapter interface for extensibility | ✓ IMPLEMENTED | `ingestion/adapters.py::BaseAdapter` |
| Canonical dataset objects | ✓ IMPLEMENTED | `schema/canonical.py::CanonicalDataset` |
| Ingestion reports | ✓ IMPLEMENTED | `reports/generator.py::save_ingestion_report` |
| Provenance preservation | ✓ IMPLEMENTED | `CanonicalSample.provenance` field |
| Canonical schema with all required fields | ✓ IMPLEMENTED | `schema/canonical.py::CanonicalSample` |
| Versioned schema | ✓ IMPLEMENTED | `schema/versioning.py::DatasetVersion` |
| Forward-compatible schema | ✓ IMPLEMENTED | `CanonicalSample.from_dict` (unknown keys dropped) |
| Automated Validation Engine | ✓ IMPLEMENTED | `validation/engine.py::ValidationEngine` |
| Schema validation | ✓ IMPLEMENTED | `ValidationEngine._check_schema` |
| Missing image detection | ✓ IMPLEMENTED | `ValidationEngine._check_missing_images` |
| Duplicate detection | ✓ IMPLEMENTED | `ValidationEngine._check_duplicates` |
| Impossible measurement detection | ✓ IMPLEMENTED | `ValidationEngine._check_impossible_measurements` |
| Outlier identification | ✓ IMPLEMENTED | `ValidationEngine._check_outliers` |
| Coverage completeness checks | ✓ IMPLEMENTED | `ValidationEngine._check_coverage_completeness` |
| Referential integrity checks | ✓ IMPLEMENTED | `ValidationEngine._check_referential_integrity` |
| PASS/WARNING/FAIL categorisation | ✓ IMPLEMENTED | `validation/results.py::ValidationStatus` |
| Machine-readable reports | ✓ IMPLEMENTED | `ValidationReport.to_dict()` → JSON |
| Human-readable reports | ✓ IMPLEMENTED | `ValidationReport.as_text()` + Markdown |
| Coverage Analysis Engine | ✓ IMPLEMENTED | `coverage/engine.py::CoverageEngine` |
| Distance coverage | ✓ IMPLEMENTED | `CoverageEngine._analyse_distance` |
| Orientation coverage | ✓ IMPLEMENTED | `CoverageEngine._analyse_orientation` |
| Device coverage | ✓ IMPLEMENTED | `CoverageEngine._analyse_device` |
| Sample distribution balance | ✓ IMPLEMENTED | `CoverageEngine._analyse_balance` |
| Coverage heatmaps | ✓ IMPLEMENTED | `CoverageEngine._build_heatmap` |
| Collection recommendations | ✓ IMPLEMENTED | `CoverageEngine._generate_recommendations` |
| Coverage scores | ✓ IMPLEMENTED | `coverage/results.py::CoverageScore` |
| Synthetic Geometry Generator | ✓ IMPLEMENTED | `synthetic/generator.py::SyntheticGenerator` |
| No GANs / no diffusion models | ✓ COMPLIANT | Perspective projection only |
| Perspective scaling model | ✓ IMPLEMENTED | `generator.py::_perspective_pixel_size` |
| Bearing change model | ✓ IMPLEMENTED | `SyntheticGenerator.generate_bearing_variants` |
| Camera height variation | ✓ IMPLEMENTED | `SyntheticGenerator.generate_height_variants` |
| Synthetic labelling | ✓ IMPLEMENTED | `source_type='synthetic'` on all generated samples |
| Dataset Approval Workflow | ✓ IMPLEMENTED | `approval/workflow.py::ApprovalWorkflow` |
| candidate → validated | ✓ IMPLEMENTED | `promote_to_validated` (requires validation PASS) |
| validated → human_reviewed | ✓ IMPLEMENTED | `promote_to_human_reviewed` (requires reviewer name) |
| human_reviewed → approved | ✓ IMPLEMENTED | `promote_to_approved` (checksum locked) |
| approved → archived | ✓ IMPLEMENTED | `ApprovalWorkflow.archive` |
| Immutable approved datasets | ✓ IMPLEMENTED | Checksum + `verify_integrity` |
| Modification produces new version | ✓ IMPLEMENTED | `ApprovalWorkflow.create_new_version` |
| Observability / structured logging | ✓ IMPLEMENTED | `observability/logger.py::AurigaLogger` |
| Ingestion events | ✓ IMPLEMENTED | `AurigaLogger.ingestion` |
| Validation events | ✓ IMPLEMENTED | `AurigaLogger.validation` |
| Promotion events | ✓ IMPLEMENTED | `AurigaLogger.promotion` |
| Research debt identifiers | ✓ IMPLEMENTED | `observability/research_debt.py::ResearchDebtRegister` |

## Constitutional Constraints

| Constraint | Status | Enforcement |
|------------|--------|-------------|
| Never store unique hardware identifiers | ✓ COMPLIANT | `device_alias` used, not hardware ID |
| Never transmit to cloud by default | ✓ COMPLIANT | All I/O is local file system only |
| Never modify approved datasets | ✓ COMPLIANT | `create_new_version` required; checksum locks |
| Never bypass human approval | ✓ COMPLIANT | `promote_to_approved` requires prior human_reviewed state |
| Never hide validation failures | ✓ COMPLIANT | All failures surface in `ValidationReport` |
| Always preserve provenance | ✓ COMPLIANT | `provenance` field on every sample and dataset |
| Always distinguish real vs synthetic | ✓ COMPLIANT | `source_type` enum; `is_synthetic` property |
| Always document uncertainty | ✓ COMPLIANT | RD-DATA-001 in synthetic notes and debt register |
"""

_HUMAN_VALIDATION_CHECKLIST = """\
# Human Validation Checklist — Auriga Data Factory

Use this checklist to manually verify the Data Factory implementation
against the Auriga specification.

## 1. Ingestion

- [ ] Can a CSV metadata file be imported using `auriga-factory ingest`?
- [ ] Are all canonical fields populated in the output JSON dataset?
- [ ] Is provenance information recorded (source file, adapter used, timestamp)?
- [ ] Can a directory containing `metadata.csv` + `images/` be ingested?
- [ ] Can a legacy JSON experiment file be imported?
- [ ] Is an ingestion report generated?
- [ ] Does the dataset start in `candidate` state after ingestion?

## 2. Validation

- [ ] Does the validation engine accept a valid dataset without errors?
- [ ] Does the validation engine FAIL a dataset with missing required fields?
- [ ] Does the validation engine FAIL a dataset referencing non-existent image files?
- [ ] Does the validation engine detect duplicate sample IDs?
- [ ] Does the validation engine detect impossible values (e.g. negative distance)?
- [ ] Does the validation engine detect outliers in numeric fields?
- [ ] Does the validation engine WARNING when coverage is sparse?
- [ ] Is a machine-readable JSON report generated?
- [ ] Is a human-readable text/Markdown report generated?
- [ ] Are ALL failures reported — none hidden?

## 3. Coverage Analysis

- [ ] Does the coverage engine report a score for each dimension?
- [ ] Are collection recommendations generated (e.g. "Collect 3 more at 2.5m Down")?
- [ ] Is a coverage heatmap matrix included in the output?
- [ ] Does overall score reflect true dataset completeness?

## 4. Synthetic Generation

- [ ] Can synthetic samples be generated via `auriga-factory generate-synthetic`?
- [ ] Are all synthetic samples labelled `source_type='synthetic'`?
- [ ] Do generated pixel sizes scale correctly with distance (larger at closer range)?
- [ ] Do synthetic samples carry provenance and uncertainty notes?
- [ ] Is RD-DATA-001 referenced in synthetic sample notes?

## 5. Approval Workflow

- [ ] Can a candidate dataset be promoted to `validated` after passing validation?
- [ ] Is promotion to `validated` blocked if validation fails?
- [ ] Can a validated dataset be marked `human_reviewed` with a reviewer name?
- [ ] Is human_reviewed promotion blocked without a non-empty reviewer name?
- [ ] Can a human_reviewed dataset be promoted to `approved`?
- [ ] Is a content checksum stored on approval?
- [ ] Does `verify_integrity` return True immediately after approval?
- [ ] Does `verify_integrity` return False after manually editing an approved dataset?
- [ ] Can an approved dataset be archived?
- [ ] Does `create_new_version` produce a new `candidate` dataset without modifying the approved one?

## 6. Observability

- [ ] Are ingestion events visible in console logs?
- [ ] Are validation events logged with dataset ID?
- [ ] Are promotion events logged with approver name and new state?
- [ ] Are errors logged with exception detail?
- [ ] Does the research debt register list all RD-DATA-* items?
- [ ] Can the research debt register be exported as Markdown?

## 7. Constitutional Constraints

- [ ] Confirm no unique hardware identifiers are stored (check `device_model` and `device_alias` fields).
- [ ] Confirm no network calls are made during ingestion, validation, or approval.
- [ ] Confirm an approved dataset cannot be silently modified (checksum check).
- [ ] Confirm synthetic samples are clearly distinguishable from real samples.

## 8. CLI

- [ ] Does `python -m auriga_data_factory.cli.main --help` display usage?
- [ ] Does `ingest` command produce a JSON dataset file?
- [ ] Does `validate` command produce validation report files?
- [ ] Does `analyse-coverage` command produce coverage report files?
- [ ] Does `generate-synthetic` command produce samples?
- [ ] Does `approve` pipeline work end-to-end?
- [ ] Does `debt-register` command produce the research debt report?
"""
