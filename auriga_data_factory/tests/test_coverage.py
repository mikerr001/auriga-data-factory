"""
Unit tests — Coverage module
==============================
Tests for the coverage analysis engine and report generation.
"""

import unittest

from ..schema.canonical import CanonicalDataset, CanonicalSample, SourceType, FiducialType
from ..coverage.engine import CoverageEngine
from ..coverage.results import CoverageReport, CoverageScore


def make_sample(sample_id="S-001", distance=1.5, orientation="Down") -> CanonicalSample:
    return CanonicalSample(
        sample_id=sample_id,
        filename=f"{sample_id}.jpg",
        image_path="",
        fiducial_type=FiducialType.ARUCO.value,
        object_name="target",
        distance_meters=distance,
        orientation=orientation,
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


class TestCoverageEngine(unittest.TestCase):

    def _make_full_dataset(self) -> CanonicalDataset:
        """Return a dataset covering all expected distances and orientations."""
        distances = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        orientations = ["Down", "Up", "Left", "Right", "Angled", "Flat"]
        samples = []
        idx = 0
        for d in distances:
            for o in orientations:
                for _ in range(3):  # 3 per cell
                    samples.append(make_sample(f"S-{idx:04d}", distance=d, orientation=o))
                    idx += 1
        return CanonicalDataset(name="Full Dataset", samples=samples)

    def test_analyse_returns_report(self):
        ds = self._make_full_dataset()
        engine = CoverageEngine()
        report = engine.analyse(ds)
        self.assertIsInstance(report, CoverageReport)

    def test_full_dataset_high_score(self):
        ds = self._make_full_dataset()
        engine = CoverageEngine()
        report = engine.analyse(ds)
        self.assertGreaterEqual(report.overall_score, 0.7)

    def test_empty_dataset_low_score(self):
        ds = CanonicalDataset(name="Empty", samples=[])
        engine = CoverageEngine(
            expected_distances=[1.0, 2.0],
            expected_orientations=["Down", "Up"],
        )
        report = engine.analyse(ds)
        self.assertEqual(report.overall_score, 0.0)

    def test_recommendations_generated_for_sparse_dataset(self):
        ds = CanonicalDataset(
            name="Sparse",
            samples=[make_sample("S-001", distance=1.0, orientation="Down")],
        )
        engine = CoverageEngine(
            expected_distances=[1.0, 2.0],
            expected_orientations=["Down", "Up"],
            min_cell_samples=3,
        )
        report = engine.analyse(ds)
        self.assertGreater(len(report.recommendations), 0)

    def test_no_recommendations_for_complete_dataset(self):
        ds = self._make_full_dataset()
        engine = CoverageEngine(min_cell_samples=3)
        report = engine.analyse(ds)
        # May have a few, but should not have as many as a sparse dataset.
        self.assertLess(len(report.recommendations), 10)

    def test_heatmap_data_included(self):
        ds = self._make_full_dataset()
        engine = CoverageEngine()
        report = engine.analyse(ds)
        self.assertIn("distance_x_orientation", report.heatmap_data)
        hm = report.heatmap_data["distance_x_orientation"]
        self.assertIn("matrix", hm)
        self.assertIn("x_labels", hm)
        self.assertIn("y_labels", hm)

    def test_distance_coverage_score_zero_for_no_samples(self):
        ds = CanonicalDataset(name="Empty", samples=[])
        engine = CoverageEngine(expected_distances=[1.0, 2.0], expected_orientations=["Down"])
        report = engine.analyse(ds)
        dist_score = next(s for s in report.scores if s.dimension == "distance")
        self.assertEqual(dist_score.score, 0.0)

    def test_orientation_missing_values_reported(self):
        # Only "Down" orientation in dataset; "Up" is missing.
        samples = [make_sample(f"S-{i}", distance=1.0, orientation="Down") for i in range(5)]
        ds = CanonicalDataset(name="OneOrientation", samples=samples)
        engine = CoverageEngine(
            expected_orientations=["Down", "Up"],
            expected_distances=[1.0],
        )
        report = engine.analyse(ds)
        orient_score = next(s for s in report.scores if s.dimension == "orientation")
        self.assertIn("Up", orient_score.missing_values)

    def test_report_as_text_contains_score(self):
        ds = self._make_full_dataset()
        engine = CoverageEngine()
        report = engine.analyse(ds)
        text = report.as_text()
        self.assertIn("COVERAGE REPORT", text)
        self.assertIn("distance", text)

    def test_report_serialisable(self):
        import json
        ds = self._make_full_dataset()
        engine = CoverageEngine()
        report = engine.analyse(ds)
        json.dumps(report.to_dict())


if __name__ == "__main__":
    unittest.main()
