# SYNTHETIC_GENERATION_GUIDE.md
# Auriga Data Factory — Synthetic Data Generation Guide

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This guide defines how synthetic datasets are generated within the Auriga Data Factory. It specifies the mathematical foundations, generation architecture, labelling requirements, validation procedures, and constitutional constraints that govern synthetic data production.

Synthetic data in Auriga serves a precise purpose: **controlled hypothesis testing and coverage extension**. The goal is not photorealism but physical plausibility. Every synthetic record must be grounded in the same geometric and optical principles that govern real-world Auriga datasets.

---

## 2. Constitutional Position on Synthetic Generation

### Foundational Decision

> **Primary synthetic strategy: Mathematically derived generation from camera geometry and perspective models.**

This decision is constitutional. Future extensions are permitted through documented research debt. The rationale:

1. **Explainability:** Geometry-derived data can be traced back to physical first principles.
2. **Offline operation:** No GPU, no cloud, no ML infrastructure required.
3. **Scientific validity:** Controlled variation enables hypothesis testing impossible with real data alone.
4. **Alignment with Virtual Fiducial methodology:** The same geometric models used for distance estimation can be inverted to generate plausible synthetic observations.

### Prohibited in MVP

- Generative adversarial networks (GANs).
- Diffusion models.
- Neural image synthesis.
- Photorealistic 3D rendering engines.

These are not prohibited permanently. They are deferred as research debt (RD-010) and must not enter the system until their value, constraints, and validation procedures have been documented through the constitutional process.

### Constitutional Rules for Synthetic Data

- **D-5:** Synthetic samples must never be unlabelled or mixed with real samples without explicit hybrid dataset classification.
- Every synthetic record must carry `sourceType: "synthetic"`.
- Every synthetic record must carry a populated `syntheticParameters` object.
- Synthetic datasets must pass the same validation pipeline as real datasets.
- Before a synthetic dataset may be used in downstream repositories, its distribution must be compared to the corresponding real dataset.

---

## 3. Generation Architecture

```
SyntheticGenerator (abstract base class)
│
├── GeometryGenerator              ← IMPLEMENT NOW (MVP)
│   ├── FiducialAppearanceModel    apparent pixel size vs. distance
│   ├── PerspectiveTransformModel  camera angle → projective distortion
│   ├── BearingEstimationModel     lateral offset → bearing angle
│   └── CameraHeightVariationModel height variation → ground projection shift
│
├── AugmentationGenerator          ← PLACEHOLDER (future)
│   └── (perturbation of real samples: blur, noise, flip, brightness)
│
├── RenderingGenerator             ← PLACEHOLDER (future)
│   └── (programmatic compositing via OpenCV or 3D engine)
│
└── MLGenerator                    ← PLACEHOLDER (future)
    └── (GAN / diffusion — requires constitutional review before implementation)
```

Placeholder generators expose the interface but raise `NotImplementedError`. This ensures the architecture is extensible without implying these methods are ready for use.

---

## 4. GeometryGenerator — Mathematical Models

### 4.1 Model 1: Fiducial Apparent Size vs. Distance

**Physical basis:** The projected pixel size of a known physical object decreases proportionally as distance increases (perspective projection).

**Model equation:**

```
pixel_width = (physical_width_mm × focal_length_px) / (distance_mm)
```

Where:
- `physical_width_mm` = known physical size of the marker
- `focal_length_px` = calibrated focal length of the device in pixels
- `distance_mm` = distance from camera to marker in millimeters

**Deriving focal_length_px from Auriga calibration data:**

During calibration experiments, we measure `pixel_width` and `distance_mm` for a known `physical_width_mm`. Therefore:

```
focal_length_px = (pixel_width × distance_mm) / physical_width_mm
```

**Generating synthetic pixel_width from distance:**

```
synthetic_pixel_width = (physical_width_mm × focal_length_px) / distance_mm
synthetic_pixel_height ≈ synthetic_pixel_width  (for square markers)
synthetic_marker_area ≈ synthetic_pixel_width²
```

**Uncertainty bounds:**

Real-world measurements deviate from ideal projection due to:
- Measurement imprecision (±0.05 m tape measure error).
- Marker alignment (not perfectly perpendicular to camera axis).
- Lens distortion.
- Camera shake at capture time.

Synthetic records should include uncertainty perturbation:
```
noise_factor = Normal(mean=1.0, std=0.03)
synthetic_pixel_width *= noise_factor
```

The std of 0.03 is a design estimate (Research Debt RD-011). It must be calibrated against real Auriga data.

### 4.2 Model 2: Perspective Transform Effects

**Physical basis:** When the camera is pitched or yawed relative to the marker, the marker's apparent shape is distorted. A square marker appears as a trapezoid when viewed at an angle.

**Model equation (horizontal yaw effect on apparent width):**

```
apparent_width = true_width × cos(yaw_angle_radians)
```

**Model equation (vertical pitch effect on apparent height):**

```
apparent_height = true_height × cos(pitch_angle_radians)
```

**Generating synthetic angled observations:**

```python
import math

def synthetic_angled_observation(
    physical_width_mm: float,
    focal_length_px: float,
    distance_m: float,
    yaw_degrees: float,
    pitch_degrees: float
) -> dict:
    distance_mm = distance_m * 1000
    frontal_width = (physical_width_mm * focal_length_px) / distance_mm
    frontal_height = frontal_width
    apparent_width = frontal_width * math.cos(math.radians(yaw_degrees))
    apparent_height = frontal_height * math.cos(math.radians(pitch_degrees))
    return {
        "markerWidthPx": round(apparent_width),
        "markerHeightPx": round(apparent_height),
        "markerAreaPx": round(apparent_width * apparent_height),
        "pitchDegrees": pitch_degrees,
        "yawDegrees": yaw_degrees
    }
```

### 4.3 Model 3: Bearing Estimation

**Physical basis:** The bearing to a marker is determined by the horizontal displacement of the marker's center from the image center, scaled by the camera's field of view.

**Model equation:**

```
bearing_degrees = arctan(
    (centerX - image_width / 2) / focal_length_px
) × (180 / π)
```

**Generating synthetic bearing values:**

Given a desired `bearing_degrees` and known `focal_length_px` and `image_width`:

```python
import math

def bearing_to_centerX(
    bearing_degrees: float,
    focal_length_px: float,
    image_width: int
) -> float:
    offset = math.tan(math.radians(bearing_degrees)) * focal_length_px
    return (image_width / 2) + offset
```

### 4.4 Model 4: Camera Height Variation Effects

**Physical basis:** A camera held at different heights above the ground will observe a ground-plane marker at a different apparent pitch angle.

**Model equation:**

```
apparent_pitch_degrees = arctan(camera_height_m / distance_m) × (180 / π)
```

**Effect on apparent marker height:**

```
apparent_height_px = frontal_height_px × cos(apparent_pitch_degrees × π / 180)
```

This model enables synthetic generation of height-variant observations from a fixed real-world sample.

---

## 5. syntheticParameters Object Structure

Every synthetic record must carry a fully populated `syntheticParameters` object documenting all inputs used to produce the record.

```json
{
  "generatorClass": "GeometryGenerator",
  "generatorVersion": "1.0.0",
  "model": "FiducialAppearanceModel",
  "generatedAt": "2026-06-16T14:30:00Z",
  "inputs": {
    "physicalWidthMm": 100.0,
    "focalLengthPx": 1420.5,
    "distanceM": 2.0,
    "yawDegrees": 0.0,
    "pitchDegrees": 0.0,
    "cameraHeightCm": 120.0,
    "noiseStd": 0.03
  },
  "derivedFrom": "fiducials_aruco_v2",
  "derivationPurpose": "Coverage extension at 4.5m and 5.0m distances",
  "researchDebtItems": ["RD-011"]
}
```

---

## 6. Hybrid Dataset Generation

A hybrid dataset combines real measurements with synthetic interpolation or extension.

### 6.1 When to Use Hybrid Datasets

- Real data covers distances 0.5 m – 3.0 m, but validation requires coverage up to 5.0 m.
- A specific orientation has only 2 real samples; statistical analysis requires at least 10.
- A device has not yet been physically tested but must be modelled.

### 6.2 Hybrid Dataset Requirements

- Must carry `sourceType: "hybrid"` at the dataset level.
- Each individual record carries its own `sourceType`: `"real"` or `"synthetic"`.
- Must include a dataset-level `hybridRationale` field.
- Must document the proportion of real vs. synthetic records.
- Must undergo distribution comparison between real and synthetic subsets.

### 6.3 Hybrid Record Tagging

```json
{
  "recordId": "uuid",
  "sourceType": "synthetic",
  "datasetVersion": "fiducials_aruco_hybrid_v1",
  "syntheticParameters": { ... },
  "notes": "Generated to extend coverage at 4.5m. No real sample collected at this distance."
}
```

---

## 7. Synthetic vs. Real Distribution Comparison

Before any synthetic or hybrid dataset may be distributed to downstream repositories, its distribution must be compared to the corresponding real dataset.

### 7.1 What Is Compared

For each numeric field (where N ≥ 10 in both distributions):

| Metric | Method |
|---|---|
| Central tendency | Compare mean and median |
| Spread | Compare standard deviation and IQR |
| Range | Compare min/max |
| Distribution shape | Visual histogram overlay |
| Correlation to distance | Compare regression slope (pixel size vs. distance) |

### 7.2 Statistical Tests (Future)

Research Debt RD-003 addresses which statistical tests (e.g., Kolmogorov-Smirnov, Mann-Whitney U) should be applied formally. For MVP, visual comparison and summary statistics are sufficient.

### 7.3 Comparison Report Format

```markdown
## Distribution Comparison: fiducials_aruco_synthetic_v1 vs fiducials_aruco_v2

| Field           | Real Mean | Synth Mean | Δ%    | Concern |
|---|---|---|---|---|
| markerWidthPx   | 312.4     | 308.9      | 1.1%  | None    |
| markerHeightPx  | 308.1     | 305.2      | 0.9%  | None    |
| distanceMeters  | 2.3       | 2.8        | 21.7% | Review  |

Conclusion: Synthetic distribution is consistent with real distribution for
pixel dimensions. Distance distribution differs because synthetic dataset
intentionally extends coverage to 4.5m–5.0m range not present in real data.
This is expected and acceptable.
```

### 7.4 Acceptance Criteria

A distribution comparison is considered acceptable when:
- Mean differences in pixel dimension fields are < 15% (design estimate — Research Debt RD-011).
- Distribution shape is visually similar (no bimodal artifacts from generation errors).
- Any intentional deviations (e.g., extended distance coverage) are explicitly documented.

---

## 8. Synthetic Data Generation Workflow

```
IDENTIFY COVERAGE GAP
(from coverage_analyzer output)
        │
        ▼
SELECT GENERATION MODEL
(FiducialAppearanceModel / PerspectiveModel / etc.)
        │
        ▼
CONFIGURE PARAMETERS
(physical size, focal length, target distances, noise)
        │
        ▼
RUN GEOMETRY GENERATOR
        │
        ▼
GENERATE SYNTHETIC RECORDS
(each record includes syntheticParameters)
        │
        ▼
VALIDATE SYNTHETIC DATASET
(same 7-layer pipeline as real data)
        │
        ▼
COMPARE TO REAL DISTRIBUTION
        │
        ▼
HUMAN REVIEW + APPROVAL
        │
        ▼
REGISTER AS APPROVED SYNTHETIC DATASET
```

---

## 9. Python Reference Implementation Structure

```python
# factory/generation/generator.py
from abc import ABC, abstractmethod
from typing import List, Dict

class SyntheticGenerator(ABC):
    """Abstract base for all synthetic generation strategies."""

    @abstractmethod
    def generate(
        self,
        coverage_gaps: List[Dict],
        base_dataset_version: str,
        output_path: str
    ) -> str:
        """
        Generate synthetic records to address coverage gaps.
        Returns the path to the generated dataset.
        """
        raise NotImplementedError


# factory/generation/geometry_generator.py
class GeometryGenerator(SyntheticGenerator):
    """
    Mathematically derived synthetic data from camera geometry models.
    Primary MVP generator.
    """
    def __init__(self, focal_length_px: float, physical_marker_size_mm: float):
        self.focal_length_px = focal_length_px
        self.physical_marker_size_mm = physical_marker_size_mm

    def generate(self, coverage_gaps, base_dataset_version, output_path) -> str:
        records = []
        for gap in coverage_gaps:
            record = self._generate_from_gap(gap, base_dataset_version)
            records.append(record)
        self._write_records(records, output_path)
        return output_path

    def _generate_from_gap(self, gap: dict, base_version: str) -> dict:
        # Implementation per Model 1 (FiducialAppearanceModel)
        ...


# factory/generation/augmentation_generator.py
class AugmentationGenerator(SyntheticGenerator):
    """PLACEHOLDER. Not implemented in MVP."""
    def generate(self, *args, **kwargs):
        raise NotImplementedError(
            "AugmentationGenerator is a future capability. "
            "See SYNTHETIC_GENERATION_GUIDE.md Research Debt RD-010."
        )


# factory/generation/rendering_generator.py
class RenderingGenerator(SyntheticGenerator):
    """PLACEHOLDER. Not implemented in MVP."""
    def generate(self, *args, **kwargs):
        raise NotImplementedError(
            "RenderingGenerator is a future capability. "
            "See SYNTHETIC_GENERATION_GUIDE.md Research Debt RD-010."
        )


# factory/generation/ml_generator.py
class MLGenerator(SyntheticGenerator):
    """PLACEHOLDER. Requires constitutional review before implementation."""
    def generate(self, *args, **kwargs):
        raise NotImplementedError(
            "MLGenerator requires formal constitutional review. "
            "See SYNTHETIC_GENERATION_GUIDE.md Research Debt RD-010."
        )
```

---

## 10. Research Debt

| ID | Question |
|---|---|
| RD-010 | AugmentationGenerator, RenderingGenerator, MLGenerator — conditions for MVP implementation |
| RD-011 | Noise standard deviation (0.03) for FiducialAppearanceModel needs empirical calibration against real Auriga data |
| RD-003 | Formal statistical tests for synthetic vs. real distribution comparison |
| RD-012 | Should focal length be treated as a constant or device-specific calibrated parameter? |
| RD-013 | How should lens distortion be modelled in the GeometryGenerator? |

---

## 11. Human Approval Record

| Field | Value |
|---|---|
| Document | SYNTHETIC_GENERATION_GUIDE.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
