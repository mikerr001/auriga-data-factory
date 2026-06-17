"""
Unit tests — Schema module
===========================
Tests covering CanonicalSample, CanonicalDataset, DatasetVersion.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ..schema.canonical import (
    CanonicalSample, CanonicalDataset, DatasetState,
    SourceType, FiducialType,
)
from ..schema.versioning import DatasetVersion


def make_sample(**overrides) -> CanonicalSample:
    """Return a minimal valid CanonicalSample with optional overrides."""
    defaults = dict(
        sample_id="S-001",
        filename="img001.jpg",
        image_path="/data/images/img001.jpg",
        fiducial_type=FiducialType.ARUCO.value,
        object_name="target_A",
        distance_meters=1.5,
        orientation="Down",
        camera_height_cm=120.0,
        device_model="TestPhone/1.0",
        device_alias="DeviceA",
        marker_width_px=80.5,
        marker_height_px=81.0,
        marker_area_px=6520.5,
        center_x=960.0,
        center_y=540.0,
        detection_success=True,
        capture_timestamp="2026-06-17T10:00:00+00:00",
        source_type=SourceType.REAL.value,
    )
    defaults.update(overrides)
    return CanonicalSample(**defaults)


class TestCanonicalSample(unittest.TestCase):

    def test_basic_creation(self):
        s = make_sample()
        self.assertEqual(s.sample_id, "S-001")
        self.assertEqual(s.source_type, SourceType.REAL.value)

    def test_is_synthetic_real(self):
        s = make_sample(source_type=SourceType.REAL.value)
        self.assertFalse(s.is_synthetic)

    def test_is_synthetic_synthetic(self):
        s = make_sample(source_type=SourceType.SYNTHETIC.value)
        self.assertTrue(s.is_synthetic)

    def test_is_synthetic_augmented(self):
        s = make_sample(source_type=SourceType.AUGMENTED.value)
        self.assertTrue(s.is_synthetic)

    def test_to_dict_round_trip(self):
        s = make_sample()
        d = s.to_dict()
        s2 = CanonicalSample.from_dict(d)
        self.assertEqual(s.sample_id, s2.sample_id)
        self.assertEqual(s.distance_meters, s2.distance_meters)

    def test_from_dict_ignores_unknown_keys(self):
        d = make_sample().to_dict()
        d["future_field_xyz"] = "some_value"
        # Should not raise.
        s = CanonicalSample.from_dict(d)
        self.assertEqual(s.sample_id, "S-001")

    def test_content_hash_stable(self):
        s = make_sample()
        h1 = s.content_hash()
        h2 = s.content_hash()
        self.assertEqual(h1, h2)

    def test_content_hash_differs_on_change(self):
        s1 = make_sample(distance_meters=1.5)
        s2 = make_sample(distance_meters=2.5)
        self.assertNotEqual(s1.content_hash(), s2.content_hash())

    def test_enum_normalised_to_string(self):
        s = make_sample(source_type=SourceType.REAL)
        self.assertIsInstance(s.source_type, str)
        self.assertEqual(s.source_type, "real")


class TestCanonicalDataset(unittest.TestCase):

    def _make_dataset(self, n_real=3, n_synthetic=2) -> CanonicalDataset:
        samples = [make_sample(sample_id=f"S-{i:03d}") for i in range(n_real)]
        samples += [
            make_sample(sample_id=f"SYN-{i:03d}", source_type=SourceType.SYNTHETIC.value)
            for i in range(n_synthetic)
        ]
        return CanonicalDataset(name="Test Dataset", samples=samples)

    def test_sample_counts(self):
        ds = self._make_dataset(n_real=3, n_synthetic=2)
        self.assertEqual(ds.sample_count, 5)
        self.assertEqual(ds.real_sample_count, 3)
        self.assertEqual(ds.synthetic_sample_count, 2)

    def test_initial_state_is_candidate(self):
        ds = self._make_dataset()
        self.assertEqual(ds.state, DatasetState.CANDIDATE.value)

    def test_is_approved_false_initially(self):
        ds = self._make_dataset()
        self.assertFalse(ds.is_approved)

    def test_checksum_computed(self):
        ds = self._make_dataset()
        checksum = ds.compute_checksum()
        self.assertIsInstance(checksum, str)
        self.assertEqual(len(checksum), 64)  # SHA-256 hex

    def test_verify_checksum_before_set(self):
        ds = self._make_dataset()
        self.assertFalse(ds.verify_checksum())

    def test_verify_checksum_after_set(self):
        ds = self._make_dataset()
        ds.checksum = ds.compute_checksum()
        self.assertTrue(ds.verify_checksum())

    def test_checksum_detects_tampering(self):
        ds = self._make_dataset()
        ds.checksum = ds.compute_checksum()
        # Tamper with a sample.
        ds.samples[0].distance_meters = 999.0
        self.assertFalse(ds.verify_checksum())

    def test_save_and_load(self):
        with TemporaryDirectory() as tmp:
            ds = self._make_dataset()
            path = Path(tmp) / "test_dataset.json"
            ds.save(path)
            ds2 = CanonicalDataset.load(path)
            self.assertEqual(ds.dataset_id, ds2.dataset_id)
            self.assertEqual(ds.sample_count, ds2.sample_count)

    def test_to_dict_includes_samples(self):
        ds = self._make_dataset(n_real=2, n_synthetic=0)
        d = ds.to_dict()
        self.assertIn("samples", d)
        self.assertEqual(len(d["samples"]), 2)


class TestDatasetVersion(unittest.TestCase):

    def test_parse_valid(self):
        v = DatasetVersion.from_string("2.3.4")
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 3)
        self.assertEqual(v.patch, 4)

    def test_str(self):
        v = DatasetVersion(1, 0, 0)
        self.assertEqual(str(v), "1.0.0")

    def test_bump_major(self):
        v = DatasetVersion(1, 2, 3).bump_major()
        self.assertEqual(str(v), "2.0.0")

    def test_bump_minor(self):
        v = DatasetVersion(1, 2, 3).bump_minor()
        self.assertEqual(str(v), "1.3.0")

    def test_bump_patch(self):
        v = DatasetVersion(1, 2, 3).bump_patch()
        self.assertEqual(str(v), "1.2.4")

    def test_comparison(self):
        v1 = DatasetVersion(1, 0, 0)
        v2 = DatasetVersion(2, 0, 0)
        self.assertLess(v1, v2)
        self.assertGreater(v2, v1)

    def test_initial(self):
        v = DatasetVersion.initial()
        self.assertEqual(str(v), "1.0.0")

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            DatasetVersion.from_string("1.0")

    def test_non_integer_raises(self):
        with self.assertRaises(ValueError):
            DatasetVersion.from_string("a.b.c")


if __name__ == "__main__":
    unittest.main()
