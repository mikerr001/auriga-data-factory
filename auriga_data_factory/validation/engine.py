"""
Auriga Data Factory — Validation Engine
=========================================
Multi-layer automated validation pipeline for canonical datasets.

Validation checks implemented:
    1. Schema validation         — required fields present and typed correctly.
    2. Missing image detection   — image files referenced by samples exist.
    3. Duplicate detection       — same sample_id or identical measurement hashes.
    4. Impossible measurements   — physically impossible numeric values.
    5. Outlier identification     — IQR-based detection of anomalous measurements.
    6. Coverage completeness     — minimum sample counts across key dimensions.
    7. Referential integrity     — source_type consistency; synthetic flags correct.

Constitutional rule:
    Validation failures MUST NEVER be hidden. All results must be returned
    to the caller regardless of outcome.
"""

from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..schema.canonical import CanonicalDataset, CanonicalSample, SourceType
from ..observability.logger import get_logger
from .results import ValidationResult, ValidationReport, ValidationStatus

logger = get_logger("auriga.validation.engine")


class ValidationEngine:
    """
    Runs all validation checks against a :class:`CanonicalDataset`.

    Parameters
    ----------
    check_image_existence:
        If True, verify that image files referenced by samples exist on disk.
        Disable for unit tests or when images are remote.
    outlier_iqr_multiplier:
        Multiplier applied to IQR for outlier detection (default 1.5).
        See RD-DATA-003.
    min_samples_per_orientation:
        Minimum samples expected per orientation label.
    min_distance_values:
        Minimum number of distinct distance values expected.
    """

    def __init__(
        self,
        check_image_existence: bool = True,
        outlier_iqr_multiplier: float = 1.5,
        min_samples_per_orientation: int = 3,
        min_distance_values: int = 3,
    ) -> None:
        self.check_image_existence = check_image_existence
        self.outlier_iqr_multiplier = outlier_iqr_multiplier
        self.min_samples_per_orientation = min_samples_per_orientation
        self.min_distance_values = min_distance_values

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def validate(self, dataset: CanonicalDataset) -> ValidationReport:
        """
        Run the full validation pipeline over ``dataset``.

        Parameters
        ----------
        dataset:
            The dataset to validate.

        Returns
        -------
        ValidationReport
            Contains all individual check results and an overall status.
            Never raises — failures are recorded in the report.
        """
        logger.validation(
            f"Validation started: '{dataset.name}' v{dataset.version} "
            f"({dataset.sample_count} samples)",
            dataset_id=dataset.dataset_id,
        )

        results: List[ValidationResult] = []

        # Run each check and collect results.
        checks = [
            self._check_schema,
            self._check_missing_images,
            self._check_duplicates,
            self._check_impossible_measurements,
            self._check_outliers,
            self._check_coverage_completeness,
            self._check_referential_integrity,
        ]

        for check_fn in checks:
            try:
                result = check_fn(dataset)
                results.append(result)
            except Exception as exc:
                # Surface unexpected errors as FAIL results — never hide them.
                results.append(
                    ValidationResult(
                        check_name=check_fn.__name__.lstrip("_check_"),
                        status=ValidationStatus.FAIL,
                        message=f"Check raised an unexpected exception: {exc}",
                    )
                )
                logger.error(
                    f"Validation check '{check_fn.__name__}' raised: {exc}",
                    exc_info=True,
                )

        report = ValidationReport(
            dataset_id=dataset.dataset_id,
            dataset_name=dataset.name,
            dataset_version=dataset.version,
            results=results,
            validated_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.validation(
            f"Validation complete: {report.overall_status.value} "
            f"({report.pass_count}P / {report.warning_count}W / {report.fail_count}F)",
            dataset_id=dataset.dataset_id,
            overall_status=report.overall_status.value,
        )

        return report

    # ------------------------------------------------------------------ #
    # Check: Schema validation                                              #
    # ------------------------------------------------------------------ #

    def _check_schema(self, dataset: CanonicalDataset) -> ValidationResult:
        """Verify all required fields are present and have correct types."""
        issues: List[str] = []
        affected: List[str] = []

        required_numeric = [
            "distance_meters", "camera_height_cm",
            "marker_width_px", "marker_height_px", "marker_area_px",
            "center_x", "center_y",
        ]
        required_str = [
            "sample_id", "filename", "fiducial_type", "object_name",
            "orientation", "device_model", "device_alias",
            "capture_timestamp", "source_type",
        ]

        for sample in dataset.samples:
            sid = sample.sample_id or "(no ID)"
            for field in required_str:
                val = getattr(sample, field, None)
                if not val:
                    issues.append(f"Sample {sid}: missing/empty field '{field}'.")
                    if sid not in affected:
                        affected.append(sid)

            for field in required_numeric:
                val = getattr(sample, field, None)
                if val is None:
                    issues.append(f"Sample {sid}: missing numeric field '{field}'.")
                    if sid not in affected:
                        affected.append(sid)

        if not issues:
            return ValidationResult(
                check_name="schema_validation",
                status=ValidationStatus.PASS,
                message=f"All {dataset.sample_count} samples pass schema validation.",
            )

        return ValidationResult(
            check_name="schema_validation",
            status=ValidationStatus.FAIL,
            message=f"{len(issues)} schema issue(s) across {len(affected)} sample(s).",
            details=issues[:20],  # cap detail list
            affected_samples=affected,
        )

    # ------------------------------------------------------------------ #
    # Check: Missing images                                                 #
    # ------------------------------------------------------------------ #

    def _check_missing_images(self, dataset: CanonicalDataset) -> ValidationResult:
        """Verify that image files referenced by samples exist on disk."""
        if not self.check_image_existence:
            return ValidationResult(
                check_name="missing_image_detection",
                status=ValidationStatus.PASS,
                message="Image existence check skipped (disabled).",
            )

        missing: List[str] = []
        empty_paths: List[str] = []

        for sample in dataset.samples:
            if not sample.image_path:
                empty_paths.append(sample.sample_id)
                continue
            if not Path(sample.image_path).exists():
                missing.append(sample.sample_id)

        issues: List[str] = []
        status = ValidationStatus.PASS
        message_parts = []

        if empty_paths:
            issues += empty_paths
            message_parts.append(f"{len(empty_paths)} sample(s) have no image path.")
            status = ValidationStatus.WARNING

        if missing:
            issues += missing
            message_parts.append(f"{len(missing)} sample(s) reference missing image files.")
            status = ValidationStatus.FAIL

        if not message_parts:
            return ValidationResult(
                check_name="missing_image_detection",
                status=ValidationStatus.PASS,
                message=f"All {dataset.sample_count} image paths verified.",
            )

        return ValidationResult(
            check_name="missing_image_detection",
            status=status,
            message=" ".join(message_parts),
            affected_samples=issues,
        )

    # ------------------------------------------------------------------ #
    # Check: Duplicates                                                     #
    # ------------------------------------------------------------------ #

    def _check_duplicates(self, dataset: CanonicalDataset) -> ValidationResult:
        """Detect duplicate sample IDs and identical measurement hashes."""
        id_counts = Counter(s.sample_id for s in dataset.samples)
        hash_counts = Counter(s.content_hash() for s in dataset.samples)

        dup_ids = [sid for sid, count in id_counts.items() if count > 1]
        dup_hashes = [h for h, count in hash_counts.items() if count > 1]

        if not dup_ids and not dup_hashes:
            return ValidationResult(
                check_name="duplicate_detection",
                status=ValidationStatus.PASS,
                message=f"No duplicate sample IDs or measurement hashes found.",
            )

        issues = []
        status = ValidationStatus.WARNING
        if dup_ids:
            issues.append(f"{len(dup_ids)} duplicate sample ID(s).")
            status = ValidationStatus.FAIL
        if dup_hashes:
            issues.append(f"{len(dup_hashes)} duplicate measurement hash(es).")

        return ValidationResult(
            check_name="duplicate_detection",
            status=status,
            message=" ".join(issues),
            details={"duplicate_ids": dup_ids[:10], "duplicate_hashes": dup_hashes[:10]},
            affected_samples=dup_ids[:20],
        )

    # ------------------------------------------------------------------ #
    # Check: Impossible measurements                                        #
    # ------------------------------------------------------------------ #

    def _check_impossible_measurements(self, dataset: CanonicalDataset) -> ValidationResult:
        """Detect physically impossible numeric values."""
        issues: List[str] = []
        affected: List[str] = []

        for sample in dataset.samples:
            sid = sample.sample_id
            problems = []

            if sample.distance_meters < 0:
                problems.append(f"distance_meters={sample.distance_meters} (negative)")
            if sample.distance_meters > 1000:
                problems.append(f"distance_meters={sample.distance_meters} (>1000m, suspicious)")
            if sample.camera_height_cm < 0:
                problems.append(f"camera_height_cm={sample.camera_height_cm} (negative)")
            if sample.marker_width_px < 0 or sample.marker_height_px < 0:
                problems.append("Negative marker dimensions")
            if sample.marker_area_px < 0:
                problems.append("Negative marker area")
            if sample.detection_success and sample.marker_area_px == 0:
                problems.append("detection_success=True but marker_area_px=0")

            if problems:
                for p in problems:
                    issues.append(f"Sample {sid}: {p}")
                if sid not in affected:
                    affected.append(sid)

        if not issues:
            return ValidationResult(
                check_name="impossible_measurement_detection",
                status=ValidationStatus.PASS,
                message="No impossible measurement values detected.",
            )

        return ValidationResult(
            check_name="impossible_measurement_detection",
            status=ValidationStatus.FAIL,
            message=f"{len(issues)} impossible measurement(s) in {len(affected)} sample(s).",
            details=issues[:20],
            affected_samples=affected,
        )

    # ------------------------------------------------------------------ #
    # Check: Outliers                                                        #
    # ------------------------------------------------------------------ #

    def _check_outliers(self, dataset: CanonicalDataset) -> ValidationResult:
        """IQR-based outlier detection on key numeric fields. See RD-DATA-003."""
        fields_to_check = [
            "distance_meters", "marker_width_px",
            "marker_height_px", "marker_area_px",
        ]
        outlier_samples: List[str] = []
        detail: List[str] = []

        for field_name in fields_to_check:
            values = [(s.sample_id, getattr(s, field_name)) for s in dataset.samples]
            nums = [v for _, v in values if v is not None]
            if len(nums) < 4:
                continue

            q1 = statistics.quantiles(nums, n=4)[0]
            q3 = statistics.quantiles(nums, n=4)[2]
            iqr = q3 - q1
            lower = q1 - self.outlier_iqr_multiplier * iqr
            upper = q3 + self.outlier_iqr_multiplier * iqr

            for sid, val in values:
                if val is not None and (val < lower or val > upper):
                    msg = f"Sample {sid}: {field_name}={val:.2f} (outside [{lower:.2f}, {upper:.2f}])"
                    detail.append(msg)
                    if sid not in outlier_samples:
                        outlier_samples.append(sid)

        if not outlier_samples:
            return ValidationResult(
                check_name="outlier_identification",
                status=ValidationStatus.PASS,
                message="No statistical outliers detected.",
            )

        return ValidationResult(
            check_name="outlier_identification",
            status=ValidationStatus.WARNING,
            message=(
                f"{len(outlier_samples)} sample(s) contain outlier values "
                f"(IQR×{self.outlier_iqr_multiplier}). Review recommended."
            ),
            details=detail[:20],
            affected_samples=outlier_samples,
        )

    # ------------------------------------------------------------------ #
    # Check: Coverage completeness                                          #
    # ------------------------------------------------------------------ #

    def _check_coverage_completeness(self, dataset: CanonicalDataset) -> ValidationResult:
        """Check minimum sample counts across orientations and distances. See RD-DATA-002."""
        issues: List[str] = []

        # Orientation coverage.
        orientation_counts = Counter(s.orientation for s in dataset.samples)
        for orientation, count in orientation_counts.items():
            if count < self.min_samples_per_orientation:
                issues.append(
                    f"Orientation '{orientation}' has only {count} sample(s) "
                    f"(minimum: {self.min_samples_per_orientation})."
                )

        # Distance diversity.
        distances = sorted({round(s.distance_meters, 1) for s in dataset.samples})
        if len(distances) < self.min_distance_values:
            issues.append(
                f"Only {len(distances)} distinct distance value(s) found "
                f"(minimum: {self.min_distance_values}). "
                f"Found: {distances}"
            )

        # Warn if dataset is very small.
        if dataset.sample_count < 10:
            issues.append(
                f"Dataset contains only {dataset.sample_count} sample(s). "
                "Downstream models may not generalise reliably."
            )

        if not issues:
            return ValidationResult(
                check_name="coverage_completeness",
                status=ValidationStatus.PASS,
                message="Coverage completeness checks passed.",
            )

        status = ValidationStatus.WARNING if len(issues) <= 2 else ValidationStatus.FAIL
        return ValidationResult(
            check_name="coverage_completeness",
            status=status,
            message=f"{len(issues)} coverage gap(s) detected.",
            details=issues,
        )

    # ------------------------------------------------------------------ #
    # Check: Referential integrity                                          #
    # ------------------------------------------------------------------ #

    def _check_referential_integrity(self, dataset: CanonicalDataset) -> ValidationResult:
        """Validate source_type consistency and synthetic labelling correctness."""
        issues: List[str] = []
        affected: List[str] = []

        valid_source_types = {st.value for st in SourceType}

        for sample in dataset.samples:
            sid = sample.sample_id

            if sample.source_type not in valid_source_types:
                issues.append(
                    f"Sample {sid}: unknown source_type '{sample.source_type}'."
                )
                affected.append(sid)

            # Synthetic samples must carry a note or have a non-empty provenance.
            if sample.is_synthetic and not (sample.notes or sample.provenance):
                issues.append(
                    f"Sample {sid}: marked synthetic but has no notes or provenance."
                )
                affected.append(sid)

        if not issues:
            return ValidationResult(
                check_name="referential_integrity",
                status=ValidationStatus.PASS,
                message="Source type and synthetic labelling integrity checks passed.",
            )

        return ValidationResult(
            check_name="referential_integrity",
            status=ValidationStatus.FAIL,
            message=f"{len(issues)} referential integrity issue(s).",
            details=issues[:20],
            affected_samples=list(set(affected)),
        )
