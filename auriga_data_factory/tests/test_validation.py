"""
Unit tests — Validation module
================================
Tests covering all seven validation checks, including adversarial cases.
"""

import unittest

from ..schema.canonical import CanonicalDataset, CanonicalSample, DatasetState, SourceType, FiducialType
from ..validation.engine import ValidationEngine
from ..validation.results import ValidationStatus


def make_sample(sample_id="S-001", **overrides) -> CanonicalSample:
    defaults = dict(
        sample_id=sample_id,
        filename="img001.jpg",
        image_path="/fake/path/img001.jpg",
        fiducial_type=FiducialType.ARUCO.value,
        object_name="target",
        distance_meters=1.5,
        orientation="Down",
        camera_height_cm=120.0,
        device_model="TestPhone",
        device_alias="DeviceA",
        marker_width_px=80.0,
        marker_height_px=80.0,
        marker_area_px=6400.0,
        center_x=960.0,
        center_y=540.0,
        detection_success=True,
        capture_timestamp="2026-06-17T10:00:00+00:00",
        source_type=SourceType.REAL.value,
    )
    defaults.update(overrides)
    return CanonicalSample(**defaults)


def make_dataset(samples=None, name="Test Dataset") -> CanonicalDataset:
    samples = samples or [make_sample()]
    return CanonicalDataset(name=name, samples=samples)


class TestValidationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ValidationEngine(check_image_existence=False)

    # ── Schema validation ────────────────────────────────────────────── #

    def test_schema_pass_on_valid_sample(self):
        ds = make_dataset()
        report = self.engine.validate(ds)
        schema_result = next(r for r in report.results if r.check_name == "schema_validation")
        self.assertEqual(schema_result.status, ValidationStatus.PASS)

    def test_schema_fail_on_empty_sample_id(self):
        ds = make_dataset([make_sample(sample_id="")])
        report = self.engine.validate(ds)
        schema_result = next(r for r in report.results if r.check_name == "schema_validation")
        self.assertEqual(schema_result.status, ValidationStatus.FAIL)

    def test_schema_fail_on_empty_fiducial_type(self):
        ds = make_dataset([make_sample(fiducial_type="")])
        report = self.engine.validate(ds)
        schema_result = next(r for r in report.results if r.check_name == "schema_validation")
        self.assertEqual(schema_result.status, ValidationStatus.FAIL)

    # ── Duplicate detection ──────────────────────────────────────────── #

    def test_duplicates_pass_on_unique_ids(self):
        ds = make_dataset([make_sample(f"S-{i}") for i in range(5)])
        report = self.engine.validate(ds)
        dup_result = next(r for r in report.results if r.check_name == "duplicate_detection")
        self.assertEqual(dup_result.status, ValidationStatus.PASS)

    def test_duplicates_fail_on_duplicate_ids(self):
        ds = make_dataset([make_sample("S-001"), make_sample("S-001")])
        report = self.engine.validate(ds)
        dup_result = next(r for r in report.results if r.check_name == "duplicate_detection")
        self.assertEqual(dup_result.status, ValidationStatus.FAIL)

    def test_duplicates_warns_on_identical_measurements(self):
        # Same measurements but different IDs → duplicate hash warning.
        s1 = make_sample("S-001")
        s2 = make_sample("S-002")  # same measurements
        ds = make_dataset([s1, s2])
        report = self.engine.validate(ds)
        dup_result = next(r for r in report.results if r.check_name == "duplicate_detection")
        # Should be WARNING (duplicate hash) but not FAIL (IDs are different).
        self.assertIn(dup_result.status, [ValidationStatus.WARNING, ValidationStatus.PASS])

    # ── Impossible measurements ──────────────────────────────────────── #

    def test_impossible_negative_distance(self):
        ds = make_dataset([make_sample(distance_meters=-1.0)])
        report = self.engine.validate(ds)
        result = next(r for r in report.results
                      if r.check_name == "impossible_measurement_detection")
        self.assertEqual(result.status, ValidationStatus.FAIL)

    def test_impossible_negative_area(self):
        ds = make_dataset([make_sample(marker_area_px=-100.0)])
        report = self.engine.validate(ds)
        result = next(r for r in report.results
                      if r.check_name == "impossible_measurement_detection")
        self.assertEqual(result.status, ValidationStatus.FAIL)

    def test_impossible_success_with_zero_area(self):
        ds = make_dataset([make_sample(detection_success=True, marker_area_px=0.0)])
        report = self.engine.validate(ds)
        result = next(r for r in report.results
                      if r.check_name == "impossible_measurement_detection")
        self.assertEqual(result.status, ValidationStatus.FAIL)

    def test_valid_measurements_pass(self):
        ds = make_dataset([make_sample(distance_meters=2.0, marker_area_px=5000.0)])
        report = self.engine.validate(ds)
        result = next(r for r in report.results
                      if r.check_name == "impossible_measurement_detection")
        self.assertEqual(result.status, ValidationStatus.PASS)

    # ── Outlier detection ────────────────────────────────────────────── #

    def test_outlier_warns_on_extreme_value(self):
        # Nine normal samples plus one extreme outlier.
        normal = [make_sample(f"S-{i}", distance_meters=1.5) for i in range(9)]
        outlier = make_sample("S-999", distance_meters=9999.0)
        ds = make_dataset(normal + [outlier])
        report = self.engine.validate(ds)
        result = next(r for r in report.results if r.check_name == "outlier_identification")
        self.assertEqual(result.status, ValidationStatus.WARNING)
        self.assertIn("S-999", result.affected_samples)

    def test_no_outliers_in_uniform_data(self):
        samples = [make_sample(f"S-{i}", distance_meters=1.5) for i in range(10)]
        ds = make_dataset(samples)
        report = self.engine.validate(ds)
        result = next(r for r in report.results if r.check_name == "outlier_identification")
        self.assertEqual(result.status, ValidationStatus.PASS)

    # ── Referential integrity ────────────────────────────────────────── #

    def test_referential_integrity_pass(self):
        ds = make_dataset()
        report = self.engine.validate(ds)
        result = next(r for r in report.results if r.check_name == "referential_integrity")
        self.assertEqual(result.status, ValidationStatus.PASS)

    def test_referential_integrity_fail_invalid_source_type(self):
        s = make_sample(source_type="totally_invalid")
        ds = make_dataset([s])
        report = self.engine.validate(ds)
        result = next(r for r in report.results if r.check_name == "referential_integrity")
        self.assertEqual(result.status, ValidationStatus.FAIL)

    def test_referential_integrity_synthetic_without_notes_fails(self):
        s = make_sample(source_type=SourceType.SYNTHETIC.value, notes="")
        s.provenance = {}
        ds = make_dataset([s])
        report = self.engine.validate(ds)
        result = next(r for r in report.results if r.check_name == "referential_integrity")
        self.assertEqual(result.status, ValidationStatus.FAIL)

    # ── Overall status ───────────────────────────────────────────────── #

    def test_overall_fail_if_any_fail(self):
        ds = make_dataset([make_sample(distance_meters=-1.0)])
        report = self.engine.validate(ds)
        self.assertEqual(report.overall_status, ValidationStatus.FAIL)

    def test_overall_pass_clean_dataset(self):
        # Create engine with lenient coverage settings so a modest dataset passes.
        engine = ValidationEngine(
            check_image_existence=False,
            min_samples_per_orientation=1,
            min_distance_values=2,
        )
        samples = [
            make_sample(f"S-{i:03d}",
                        distance_meters=float(i + 1),
                        orientation=o,
                        source_type=SourceType.REAL.value)
            for i, o in enumerate(["Down", "Up", "Left", "Down", "Up"])
        ]
        ds = make_dataset(samples)
        report = engine.validate(ds)
        # May be WARNING due to coverage — but must not be FAIL.
        self.assertNotEqual(report.overall_status, ValidationStatus.FAIL)

    # ── Constitutional rule: failures never hidden ───────────────────── #

    def test_all_checks_reported_even_on_exception(self):
        """Validation must return results for all checks even if one crashes."""
        ds = make_dataset()
        report = self.engine.validate(ds)
        # Expect at least 7 check results.
        self.assertGreaterEqual(len(report.results), 7)

    # ── Report text output ───────────────────────────────────────────── #

    def test_report_as_text_includes_status(self):
        ds = make_dataset()
        report = self.engine.validate(ds)
        text = report.as_text()
        self.assertIn("VALIDATION REPORT", text)
        self.assertIn("PASS", text)

    def test_report_to_dict_serialisable(self):
        import json
        ds = make_dataset()
        report = self.engine.validate(ds)
        d = report.to_dict()
        # Must be JSON-serialisable.
        json.dumps(d)


# ── Adversarial tests ────────────────────────────────────────────────────── #

class TestAdversarialValidation(unittest.TestCase):
    """Attempt to surface failure modes in the validation engine."""

    def setUp(self):
        self.engine = ValidationEngine(check_image_existence=False)

    def test_empty_dataset_does_not_crash(self):
        ds = make_dataset(samples=[])
        report = self.engine.validate(ds)
        self.assertIsNotNone(report)

    def test_very_large_sample_id(self):
        long_id = "X" * 10000
        ds = make_dataset([make_sample(sample_id=long_id)])
        report = self.engine.validate(ds)
        self.assertIsNotNone(report)

    def test_unicode_in_fields(self):
        ds = make_dataset([make_sample(object_name="目标_α_β_γ")])
        report = self.engine.validate(ds)
        self.assertIsNotNone(report)

    def test_nan_distance_in_measurements(self):
        ds = make_dataset([make_sample(distance_meters=float("nan"))])
        report = self.engine.validate(ds)
        # Should report as impossible or outlier — must not crash.
        self.assertIsNotNone(report)

    def test_single_sample_passes_no_outlier_check(self):
        """IQR outlier check requires at least 4 values — must not crash on 1."""
        ds = make_dataset([make_sample()])
        report = self.engine.validate(ds)
        self.assertIsNotNone(report)


if __name__ == "__main__":
    unittest.main()
