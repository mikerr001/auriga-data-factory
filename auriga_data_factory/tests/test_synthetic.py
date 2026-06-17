"""
Unit tests — Synthetic Generator
==================================
Tests covering the geometry-based synthetic sample generator.
"""

import math
import unittest

from ..schema.canonical import SourceType
from ..synthetic.generator import SyntheticGenerator, _perspective_pixel_size


class TestPerspectiveFormula(unittest.TestCase):
    """Unit tests for the underlying perspective projection formula."""

    def test_pixel_size_decreases_with_distance(self):
        """Closer objects appear larger — fundamental perspective law."""
        close = _perspective_pixel_size(0.15, 800, 1.0)
        far = _perspective_pixel_size(0.15, 800, 3.0)
        self.assertGreater(close, far)

    def test_pixel_size_doubles_when_distance_halved(self):
        """Linear inverse relationship: halve distance → double pixel size."""
        px1 = _perspective_pixel_size(0.15, 800, 2.0)
        px2 = _perspective_pixel_size(0.15, 800, 1.0)
        self.assertAlmostEqual(px2 / px1, 2.0, places=5)

    def test_zero_distance_raises(self):
        with self.assertRaises(ValueError):
            _perspective_pixel_size(0.15, 800, 0.0)

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            _perspective_pixel_size(0.15, 800, -1.0)


class TestSyntheticGenerator(unittest.TestCase):

    def setUp(self):
        self.gen = SyntheticGenerator(seed=42)

    def test_all_samples_labelled_synthetic(self):
        samples = self.gen.generate_perspective_scaling(
            distances=[1.0, 2.0],
            orientations=["Down"],
            samples_per_cell=3,
        )
        for s in samples:
            self.assertEqual(
                s.source_type, SourceType.SYNTHETIC.value,
                f"Sample {s.sample_id} should be labelled synthetic.",
            )

    def test_correct_count_generated(self):
        # 3 distances × 2 orientations × 4 samples = 24
        samples = self.gen.generate_perspective_scaling(
            distances=[1.0, 2.0, 3.0],
            orientations=["Down", "Up"],
            samples_per_cell=4,
        )
        self.assertEqual(len(samples), 24)

    def test_pixel_size_scales_inversely_with_distance(self):
        """Samples at 1m should have larger pixel sizes than at 3m (mean)."""
        gen = SyntheticGenerator(noise_fraction=0.0, seed=0)
        close = gen.generate_perspective_scaling(
            distances=[1.0], orientations=["Down"], samples_per_cell=10
        )
        far = gen.generate_perspective_scaling(
            distances=[3.0], orientations=["Down"], samples_per_cell=10
        )
        mean_close = sum(s.marker_width_px for s in close) / len(close)
        mean_far = sum(s.marker_width_px for s in far) / len(far)
        self.assertGreater(mean_close, mean_far)

    def test_reproducibility_with_seed(self):
        gen1 = SyntheticGenerator(seed=99)
        gen2 = SyntheticGenerator(seed=99)
        s1 = gen1.generate_perspective_scaling([1.0], ["Down"], samples_per_cell=5)
        s2 = gen2.generate_perspective_scaling([1.0], ["Down"], samples_per_cell=5)
        for a, b in zip(s1, s2):
            self.assertAlmostEqual(a.marker_width_px, b.marker_width_px, places=5)

    def test_samples_carry_uncertainty_notes(self):
        samples = self.gen.generate_perspective_scaling([1.0], ["Down"], samples_per_cell=1)
        for s in samples:
            self.assertIn("RD-DATA-001", s.notes)

    def test_samples_carry_provenance(self):
        samples = self.gen.generate_perspective_scaling([1.0], ["Down"], samples_per_cell=1)
        for s in samples:
            self.assertIn("generator", s.provenance)
            self.assertIn("uncertainty", s.provenance)

    def test_bearing_variants_generated(self):
        from ..schema.canonical import CanonicalSample, SourceType, FiducialType
        base = CanonicalSample(
            sample_id="BASE-001",
            filename="base.jpg",
            image_path="",
            fiducial_type=FiducialType.ARUCO.value,
            object_name="target",
            distance_meters=2.0,
            orientation="Down",
            camera_height_cm=120.0,
            device_model="TestPhone",
            device_alias="DeviceA",
            marker_width_px=60.0,
            marker_height_px=60.0,
            marker_area_px=3600.0,
            center_x=960.0,
            center_y=540.0,
            detection_success=True,
            capture_timestamp="2026-06-17T10:00:00+00:00",
            source_type=SourceType.REAL.value,
        )
        variants = self.gen.generate_bearing_variants(base, bearing_angles=[-15, 0, 15])
        self.assertEqual(len(variants), 3)
        for v in variants:
            self.assertEqual(v.source_type, SourceType.SYNTHETIC.value)

    def test_height_variants_generated(self):
        variants = self.gen.generate_height_variants(
            base_distance=2.0,
            orientation="Down",
            heights_cm=[80.0, 120.0, 160.0],
            samples_per_height=2,
        )
        self.assertEqual(len(variants), 6)
        for v in variants:
            self.assertEqual(v.source_type, SourceType.SYNTHETIC.value)

    def test_no_neural_network_imports(self):
        """Verify no GAN/diffusion model dependencies are present."""
        import sys
        disallowed = {"torch", "tensorflow", "keras", "diffusers", "jax"}
        loaded = set(sys.modules.keys())
        intersection = disallowed & loaded
        # Only flag if they were introduced BY this module.
        # (They would be absent in a clean environment.)
        self.assertEqual(len(intersection), 0,
                         f"Disallowed ML framework loaded: {intersection}")


if __name__ == "__main__":
    unittest.main()
