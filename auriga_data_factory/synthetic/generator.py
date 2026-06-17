"""
Auriga Data Factory — Synthetic Geometry Generator
====================================================
Generates synthetic dataset samples using mathematically derived geometric
relationships from camera projection models.

Constitutional rules:
    - NEVER use GANs or diffusion models.
    - ALWAYS label synthetic samples clearly (source_type='synthetic').
    - ALWAYS document uncertainty assumptions (see RD-DATA-001).

Geometric model:
    Perspective scaling law:
        pixel_size ∝ (real_size × focal_length) / distance

    As distance increases, the apparent marker size in pixels decreases
    proportionally. The generator uses this relationship to produce
    synthetic (distance, pixel_size) pairs that are geometrically consistent
    but must be validated against real observations (RD-DATA-001).
"""

from __future__ import annotations

import math
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..schema.canonical import CanonicalSample, SourceType, FiducialType
from ..observability.logger import get_logger

logger = get_logger("auriga.synthetic.generator")


# ──────────────────────────────── Camera model ───────────────────────────── #

def _perspective_pixel_size(
    real_size_m: float,
    focal_length_px: float,
    distance_m: float,
) -> float:
    """
    Compute expected marker size in pixels using perspective projection.

    Formula:
        pixel_size = (real_size_m * focal_length_px) / distance_m

    Parameters
    ----------
    real_size_m:
        Physical marker size in metres.
    focal_length_px:
        Camera focal length in pixels.
    distance_m:
        Distance from camera to marker in metres.

    Returns
    -------
    float
        Expected marker dimension in pixels.
    """
    if distance_m <= 0:
        raise ValueError(f"distance_m must be positive, got {distance_m}.")
    return (real_size_m * focal_length_px) / distance_m


def _bearing_shift(
    center_x: float,
    center_y: float,
    image_width: float,
    image_height: float,
    bearing_deg: float,
) -> Tuple[float, float]:
    """
    Compute new marker centre position after applying a bearing change.

    Uses a simplified linear approximation. For small bearing changes
    (< 30 degrees) this is geometrically reasonable.

    Parameters
    ----------
    center_x, center_y:
        Original marker centre (pixels).
    image_width, image_height:
        Image dimensions (pixels).
    bearing_deg:
        Bearing change in degrees (positive = right).

    Returns
    -------
    Tuple[float, float]
        New (center_x, center_y) clamped to image bounds.
    """
    shift_x = image_width * math.tan(math.radians(bearing_deg)) * 0.1
    new_x = max(0.0, min(image_width, center_x + shift_x))
    return new_x, center_y


# ─────────────────────────── Generator ──────────────────────────────────── #

class SyntheticGenerator:
    """
    Produces synthetic :class:`CanonicalSample` records using geometric models.

    All produced samples are labelled ``source_type='synthetic'`` and carry
    provenance documenting the generation parameters and uncertainty.

    Parameters
    ----------
    focal_length_px:
        Simulated camera focal length in pixels (default 800).
    image_width:
        Simulated image width in pixels (default 1920).
    image_height:
        Simulated image height in pixels (default 1080).
    noise_fraction:
        Gaussian noise applied to pixel sizes as a fraction of computed value.
        Models sensor/detection noise. See RD-DATA-001.
    real_marker_size_m:
        Physical marker size in metres (default 0.15 m = 15 cm ArUco).
    device_alias:
        Device alias to attach to generated samples.
    seed:
        Optional random seed for reproducibility.
    """

    def __init__(
        self,
        focal_length_px: float = 800.0,
        image_width: float = 1920.0,
        image_height: float = 1080.0,
        noise_fraction: float = 0.03,
        real_marker_size_m: float = 0.15,
        device_alias: str = "SyntheticDevice",
        seed: Optional[int] = None,
    ) -> None:
        self.focal_length_px = focal_length_px
        self.image_width = image_width
        self.image_height = image_height
        self.noise_fraction = noise_fraction
        self.real_marker_size_m = real_marker_size_m
        self.device_alias = device_alias
        self._rng = random.Random(seed)

        logger.research_debt(
            "RD-DATA-001",
            "Synthetic generator uses idealised perspective projection. "
            "Lens distortion, occlusion, and sensor noise are not fully modelled.",
        )

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def generate_perspective_scaling(
        self,
        distances: List[float],
        orientations: Optional[List[str]] = None,
        camera_heights: Optional[List[float]] = None,
        samples_per_cell: int = 5,
        fiducial_type: str = FiducialType.ARUCO.value,
        object_name: str = "synthetic_target",
        dataset_version: str = "1.0.0",
    ) -> List[CanonicalSample]:
        """
        Generate synthetic samples for combinations of (distance, orientation).

        Each sample's pixel dimensions are computed from the perspective
        projection formula with optional Gaussian noise.

        Parameters
        ----------
        distances:
            List of distances (metres) to generate samples for.
        orientations:
            List of orientation labels. Defaults to ["Down", "Up", "Left"].
        camera_heights:
            List of camera height values (cm). Defaults to [120.0].
        samples_per_cell:
            Number of samples to generate per (distance × orientation) cell.
        fiducial_type:
            Fiducial marker type string.
        object_name:
            Logical name for the synthetic target.
        dataset_version:
            Version to attach to generated samples.

        Returns
        -------
        List[CanonicalSample]
        """
        orientations = orientations or ["Down", "Up", "Left"]
        camera_heights = camera_heights or [120.0]

        samples: List[CanonicalSample] = []
        total = len(distances) * len(orientations) * len(camera_heights) * samples_per_cell

        logger.info(
            f"Generating {total} synthetic samples via perspective scaling.",
            distances=distances,
            orientations=orientations,
        )

        for dist in distances:
            for orient in orientations:
                for height in camera_heights:
                    for _ in range(samples_per_cell):
                        sample = self._make_perspective_sample(
                            distance_m=dist,
                            orientation=orient,
                            camera_height_cm=height,
                            fiducial_type=fiducial_type,
                            object_name=object_name,
                            dataset_version=dataset_version,
                        )
                        samples.append(sample)

        logger.info(f"Synthetic generation complete: {len(samples)} samples produced.")
        return samples

    def generate_bearing_variants(
        self,
        base_sample: CanonicalSample,
        bearing_angles: Optional[List[float]] = None,
        dataset_version: str = "1.0.0",
    ) -> List[CanonicalSample]:
        """
        Generate variants of ``base_sample`` at different bearing angles.

        The marker centre position shifts according to a linear bearing model.

        Parameters
        ----------
        base_sample:
            The real or synthetic base sample to perturb.
        bearing_angles:
            Bearing offsets in degrees. Defaults to [-15, -7.5, 7.5, 15].
        dataset_version:
            Version string for produced samples.

        Returns
        -------
        List[CanonicalSample]
        """
        bearing_angles = bearing_angles or [-15.0, -7.5, 7.5, 15.0]
        variants: List[CanonicalSample] = []

        for angle in bearing_angles:
            new_cx, new_cy = _bearing_shift(
                center_x=base_sample.center_x,
                center_y=base_sample.center_y,
                image_width=self.image_width,
                image_height=self.image_height,
                bearing_deg=angle,
            )
            sample = CanonicalSample(
                sample_id=f"SYN-BEAR-{uuid.uuid4().hex[:6].upper()}",
                filename=f"synthetic_bearing_{angle:+.1f}.jpg",
                image_path="",
                fiducial_type=base_sample.fiducial_type,
                object_name=base_sample.object_name,
                distance_meters=base_sample.distance_meters,
                orientation=base_sample.orientation,
                camera_height_cm=base_sample.camera_height_cm,
                device_model="SyntheticCameraModel/1.0",
                device_alias=self.device_alias,
                marker_width_px=base_sample.marker_width_px,
                marker_height_px=base_sample.marker_height_px,
                marker_area_px=base_sample.marker_width_px * base_sample.marker_height_px,
                center_x=new_cx,
                center_y=new_cy,
                detection_success=True,
                capture_timestamp=datetime.now(timezone.utc).isoformat(),
                source_type=SourceType.SYNTHETIC.value,
                notes=(
                    f"Bearing variant of sample {base_sample.sample_id} "
                    f"at {angle:+.1f}°. "
                    "Generated via linear bearing shift model. "
                    "See RD-DATA-001 for uncertainty assumptions."
                ),
                dataset_version=dataset_version,
                provenance={
                    "generator": "SyntheticGenerator.generate_bearing_variants",
                    "base_sample_id": base_sample.sample_id,
                    "bearing_deg": angle,
                    "uncertainty": "linear_approximation_valid_lt_30_deg",
                },
            )
            variants.append(sample)

        return variants

    def generate_height_variants(
        self,
        base_distance: float,
        orientation: str,
        heights_cm: Optional[List[float]] = None,
        samples_per_height: int = 3,
        dataset_version: str = "1.0.0",
    ) -> List[CanonicalSample]:
        """
        Generate samples varying camera height at a fixed distance.

        Height variation affects the pitch of the camera and causes subtle
        changes in marker geometry. This generator uses a simple trigonometric
        correction.

        Parameters
        ----------
        base_distance:
            Horizontal ground-truth distance (metres).
        orientation:
            Orientation label.
        heights_cm:
            Camera heights to simulate. Defaults to [80, 100, 120, 140, 160].
        samples_per_height:
            Number of samples per height.
        dataset_version:
            Version string.

        Returns
        -------
        List[CanonicalSample]
        """
        heights_cm = heights_cm or [80.0, 100.0, 120.0, 140.0, 160.0]
        samples: List[CanonicalSample] = []

        for height in heights_cm:
            # True slant distance accounting for height (Pythagoras).
            slant_distance = math.sqrt(base_distance ** 2 + (height / 100.0) ** 2)

            for _ in range(samples_per_height):
                sample = self._make_perspective_sample(
                    distance_m=slant_distance,
                    orientation=orientation,
                    camera_height_cm=height,
                    fiducial_type=FiducialType.ARUCO.value,
                    object_name="height_variant_target",
                    dataset_version=dataset_version,
                    extra_notes=(
                        f"Height variant: horizontal_dist={base_distance}m, "
                        f"height={height}cm, slant={slant_distance:.3f}m."
                    ),
                )
                samples.append(sample)

        return samples

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _make_perspective_sample(
        self,
        distance_m: float,
        orientation: str,
        camera_height_cm: float,
        fiducial_type: str,
        object_name: str,
        dataset_version: str,
        extra_notes: str = "",
    ) -> CanonicalSample:
        """Build one synthetic sample using the perspective projection model."""
        base_px = _perspective_pixel_size(
            real_size_m=self.real_marker_size_m,
            focal_length_px=self.focal_length_px,
            distance_m=distance_m,
        )
        # Apply Gaussian noise to simulate detection uncertainty.
        noise = self._rng.gauss(0, base_px * self.noise_fraction)
        width_px = max(1.0, base_px + noise)
        height_px = max(1.0, base_px + self._rng.gauss(0, base_px * self.noise_fraction))
        area_px = width_px * height_px

        # Centre of image with small random jitter.
        cx = self.image_width / 2.0 + self._rng.gauss(0, self.image_width * 0.02)
        cy = self.image_height / 2.0 + self._rng.gauss(0, self.image_height * 0.02)

        notes = (
            f"Synthetic sample: perspective_scaling model. "
            f"focal_length={self.focal_length_px}px, "
            f"real_size={self.real_marker_size_m}m, "
            f"noise_fraction={self.noise_fraction}. "
            "See RD-DATA-001 for uncertainty assumptions."
        )
        if extra_notes:
            notes += " " + extra_notes

        return CanonicalSample(
            sample_id=f"SYN-{uuid.uuid4().hex[:8].upper()}",
            filename=f"synthetic_{distance_m:.2f}m_{orientation}.jpg",
            image_path="",
            fiducial_type=fiducial_type,
            object_name=object_name,
            distance_meters=round(distance_m, 4),
            orientation=orientation,
            camera_height_cm=camera_height_cm,
            device_model="SyntheticCameraModel/1.0",
            device_alias=self.device_alias,
            marker_width_px=round(width_px, 2),
            marker_height_px=round(height_px, 2),
            marker_area_px=round(area_px, 2),
            center_x=round(cx, 2),
            center_y=round(cy, 2),
            detection_success=True,
            capture_timestamp=datetime.now(timezone.utc).isoformat(),
            source_type=SourceType.SYNTHETIC.value,
            notes=notes,
            dataset_version=dataset_version,
            provenance={
                "generator": "SyntheticGenerator._make_perspective_sample",
                "model": "perspective_projection",
                "focal_length_px": self.focal_length_px,
                "real_marker_size_m": self.real_marker_size_m,
                "noise_fraction": self.noise_fraction,
                "uncertainty": "RD-DATA-001",
            },
        )
