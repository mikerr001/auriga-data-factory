"""
Auriga Data Factory — Geometry Generator
Mathematically derived synthetic data from camera geometry models.

Primary MVP generator. Implements four models:
  1. FiducialAppearanceModel  — pixel size vs. distance
  2. PerspectiveTransformModel — angle effects on apparent dimensions
  3. BearingEstimationModel   — lateral offset to bearing angle
  4. CameraHeightVariationModel — height variation effects

See SYNTHETIC_GENERATION_GUIDE.md Section 4 for full mathematical derivation.

CRITICAL WARNING (Research Debt RD-011):
  The noise_std parameter (default 0.03) is an uncalibrated design estimate.
  DO NOT use synthetic datasets produced with this default value as production
  inputs to downstream repositories until noise_std has been calibrated against
  real Auriga data. See ADVERSARIAL_REVIEW.md ATTACK-005.
"""

import csv
import json
import math
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .generator import SyntheticGenerator


class GeometryGenerator(SyntheticGenerator):
    """
    Generates synthetic fiducial observations derived from camera projection geometry.

    Constitutional position: This is the only generator permitted in MVP.
    All other generators are placeholders pending constitutional review.
    """

    def __init__(
        self,
        focal_length_px: float,
        physical_marker_size_mm: float,
        # WARNING: noise_std=0.03 is an uncalibrated design estimate. See RD-011.
        noise_std: float = 0.03,
        seed: Optional[int] = None,
    ):
        """
        Args:
            focal_length_px: Calibrated focal length in pixels for the target device.
                             Derive from real Auriga calibration data using:
                             focal_length_px = (pixel_width × distance_mm) / physical_width_mm
                             See RD-012 for per-device vs. per-session considerations.
            physical_marker_size_mm: Physical size of the fiducial marker (mm, square side length).
            noise_std: Standard deviation of multiplicative Gaussian noise applied to pixel dimensions.
                       UNCALIBRATED DESIGN ESTIMATE — see RD-011. Do not treat as validated.
            seed: Random seed for reproducibility (None = non-deterministic).
        """
        self.focal_length_px = focal_length_px
        self.physical_marker_size_mm = physical_marker_size_mm
        self.noise_std = noise_std

        if seed is not None:
            random.seed(seed)

    def generator_name(self) -> str:
        return "GeometryGenerator"

    def generate(
        self,
        coverage_gaps: List[Dict[str, Any]],
        base_dataset_version: str,
        output_path: str,
    ) -> str:
        """Generate synthetic records for each identified coverage gap."""
        records = []
        synthetic_version = base_dataset_version.replace("_v", "_synthetic_v")

        for gap in coverage_gaps:
            gap_records = self._generate_for_gap(gap, synthetic_version, base_dataset_version)
            records.extend(gap_records)

        os.makedirs(output_path, exist_ok=True)
        metadata_path = os.path.join(output_path, "metadata.csv")
        self._write_csv(records, metadata_path)

        manifest_path = os.path.join(output_path, "synthetic_manifest.json")
        self._write_manifest(records, synthetic_version, base_dataset_version, manifest_path)

        return output_path

    def apparent_pixel_size(
        self,
        distance_m: float,
        yaw_degrees: float = 0.0,
        pitch_degrees: float = 0.0,
    ) -> Tuple[float, float]:
        """
        Model 1 + Model 2: Compute apparent pixel width and height.

        Args:
            distance_m: Distance from camera to marker in meters.
            yaw_degrees: Horizontal angle offset from direct facing.
            pitch_degrees: Vertical pitch angle.

        Returns:
            (apparent_width_px, apparent_height_px)
        """
        distance_mm = distance_m * 1000.0
        if distance_mm <= 0:
            raise ValueError(f"distance_m must be positive, got {distance_m}")

        frontal_size_px = (self.physical_marker_size_mm * self.focal_length_px) / distance_mm

        # Apply perspective distortion from angle
        yaw_rad = math.radians(abs(yaw_degrees))
        pitch_rad = math.radians(abs(pitch_degrees))
        apparent_width = frontal_size_px * math.cos(yaw_rad)
        apparent_height = frontal_size_px * math.cos(pitch_rad)

        # Apply calibrated noise
        # WARNING: noise_std=0.03 is an uncalibrated estimate. See RD-011.
        w_noise = random.gauss(1.0, self.noise_std)
        h_noise = random.gauss(1.0, self.noise_std)
        apparent_width *= max(0.5, w_noise)
        apparent_height *= max(0.5, h_noise)

        return apparent_width, apparent_height

    def bearing_to_center_x(
        self,
        bearing_degrees: float,
        image_width: int = 1280,
    ) -> float:
        """
        Model 3: Convert bearing angle to image centerX coordinate.

        Args:
            bearing_degrees: Bearing in degrees (0 = center, + = right, - = left).
            image_width: Width of the image in pixels.

        Returns:
            centerX coordinate in pixels.
        """
        offset = math.tan(math.radians(bearing_degrees)) * self.focal_length_px
        return (image_width / 2.0) + offset

    def apparent_pitch_from_height(
        self,
        camera_height_m: float,
        distance_m: float,
    ) -> float:
        """
        Model 4: Compute apparent pitch angle from camera height and distance.

        Args:
            camera_height_m: Camera height above ground in meters.
            distance_m: Horizontal distance to target in meters.

        Returns:
            Apparent pitch angle in degrees (positive = looking down).
        """
        if distance_m <= 0:
            raise ValueError(f"distance_m must be positive, got {distance_m}")
        return math.degrees(math.atan(camera_height_m / distance_m))

    def _generate_for_gap(
        self,
        gap: Dict[str, Any],
        synthetic_version: str,
        base_version: str,
    ) -> List[Dict[str, Any]]:
        """Generate a set of synthetic records for one coverage gap."""
        records = []
        distance = gap.get("distanceMeters", 1.0)
        orientation = gap.get("orientation", "flat")
        camera_height_cm = gap.get("cameraHeightCm", 120.0)
        device_alias = gap.get("deviceAlias", "Device-A")
        device_model = gap.get("deviceModel", "Unknown")
        n_samples = gap.get("targetSamples", 5)

        yaw = 0.0
        pitch = 0.0
        if orientation == "angled":
            yaw = 30.0
        elif orientation == "tilted":
            pitch = 20.0
        elif orientation == "down":
            pitch = -self.apparent_pitch_from_height(camera_height_cm / 100.0, distance)

        for _ in range(n_samples):
            width_px, height_px = self.apparent_pixel_size(distance, yaw, pitch)
            area_px = width_px * height_px

            record = {
                "recordId": str(uuid.uuid4()),
                "datasetVersion": synthetic_version,
                "sourceType": "synthetic",
                "captureTimestamp": datetime.now(timezone.utc).isoformat(),
                "filename": None,
                "imagePath": None,
                "fiducialType": "aruco",
                "distanceMeters": round(distance, 2),
                "orientation": orientation,
                "cameraHeightCm": camera_height_cm,
                "deviceModel": device_model,
                "deviceAlias": device_alias,
                "detectionSuccess": True,
                "markerWidthPx": round(width_px),
                "markerHeightPx": round(height_px),
                "markerAreaPx": round(area_px),
                "centerX": None,
                "centerY": None,
                "markerPhysicalSizeMm": self.physical_marker_size_mm,
                "notes": f"Synthetically generated. Gap coverage at {distance}m {orientation}.",
                "syntheticParameters": {
                    "generatorClass": "GeometryGenerator",
                    "generatorVersion": self.GENERATOR_VERSION,
                    "model": "FiducialAppearanceModel+PerspectiveTransformModel",
                    "generatedAt": datetime.now(timezone.utc).isoformat(),
                    "inputs": {
                        "physicalMarkerSizeMm": self.physical_marker_size_mm,
                        "focalLengthPx": self.focal_length_px,
                        "distanceM": distance,
                        "yawDegrees": yaw,
                        "pitchDegrees": pitch,
                        "cameraHeightCm": camera_height_cm,
                        # WARNING: noiseStd is an uncalibrated design estimate. See RD-011.
                        "noiseStd": self.noise_std,
                    },
                    "derivedFrom": base_version,
                    "derivationPurpose": f"Coverage extension at {distance}m {orientation}",
                    "researchDebtItems": ["RD-011", "RD-012"],
                },
            }
            records.append(record)

        return records

    def _write_csv(self, records: List[Dict[str, Any]], path: str) -> None:
        if not records:
            return
        fieldnames = list(records[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                row = {k: json.dumps(v) if isinstance(v, dict) else v
                       for k, v in record.items()}
                writer.writerow(row)

    def _write_manifest(
        self,
        records: List[Dict[str, Any]],
        synthetic_version: str,
        base_version: str,
        path: str,
    ) -> None:
        manifest = {
            "syntheticDatasetVersion": synthetic_version,
            "basedOn": base_version,
            "generator": self.generator_name(),
            "generatorVersion": self.GENERATOR_VERSION,
            "recordCount": len(records),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "focalLengthPx": self.focal_length_px,
            "physicalMarkerSizeMm": self.physical_marker_size_mm,
            "noiseStd": self.noise_std,
            "researchDebtWarning": (
                "noiseStd is an uncalibrated design estimate (RD-011). "
                "Do not use this dataset as a production input until noise_std "
                "has been calibrated against real Auriga data."
            ),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)


class AugmentationGenerator(SyntheticGenerator):
    """PLACEHOLDER — not implemented in MVP. See RD-010."""
    def generator_name(self) -> str:
        return "AugmentationGenerator"
    def generate(self, *args, **kwargs) -> str:
        raise NotImplementedError(
            "AugmentationGenerator is a future capability. "
            "See SYNTHETIC_GENERATION_GUIDE.md Research Debt RD-010."
        )


class RenderingGenerator(SyntheticGenerator):
    """PLACEHOLDER — not implemented in MVP. See RD-010."""
    def generator_name(self) -> str:
        return "RenderingGenerator"
    def generate(self, *args, **kwargs) -> str:
        raise NotImplementedError(
            "RenderingGenerator is a future capability. "
            "See SYNTHETIC_GENERATION_GUIDE.md Research Debt RD-010."
        )


class MLGenerator(SyntheticGenerator):
    """PLACEHOLDER — requires constitutional review before any implementation. See RD-010."""
    def generator_name(self) -> str:
        return "MLGenerator"
    def generate(self, *args, **kwargs) -> str:
        raise NotImplementedError(
            "MLGenerator requires formal constitutional review before implementation. "
            "See SYNTHETIC_GENERATION_GUIDE.md Research Debt RD-010 and CONSTITUTION.md."
        )
