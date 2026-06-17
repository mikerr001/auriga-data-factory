# DATASET_SPECIFICATIONS.md
# Auriga Data Factory — Dataset Specifications

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This document defines the specification for every dataset family recognized by the Auriga Data Factory. It serves as the single source of truth for what each dataset contains, how it is structured, what quality thresholds apply, and what constitutional constraints govern it.

Every downstream repository consuming Auriga datasets must treat this document as authoritative.

---

## 2. Auriga Canonical Schema

All datasets must conform to the Auriga Canonical Metadata Schema before they may be validated or versioned.

### 2.1 Schema Version

**Schema version:** `canonical_v1`

This schema version governs all Tier 1 MVP datasets. Future schema versions must be backwards-compatible unless a constitutional amendment documents the breaking change and its migration path.

### 2.2 Field Definitions

#### Required Fields

```
recordId          : string (UUID v4)
                    Unique identifier for this record.
                    Generated at ingestion. Never reused.

datasetVersion    : string
                    Version identifier of the dataset this record belongs to.
                    Format: {family}_{type}_v{n}
                    Example: fiducials_aruco_v2

sourceType        : enum ["real", "synthetic", "hybrid"]
                    Indicates data origin.
                    "real"      → captured from a physical device in the world
                    "synthetic" → mathematically derived, no physical capture
                    "hybrid"    → real measurements extended with synthetic interpolation

captureTimestamp  : string (ISO 8601)
                    When the sample was captured (real) or generated (synthetic).
                    Format: 2026-06-16T14:30:00Z
                    Required for real and hybrid. For synthetic, use generation timestamp.

filename          : string
                    The image filename as stored on disk.
                    Example: aruco_1m_flat_deviceA_001.jpg

imagePath         : string
                    Relative path from the dataset root to the image file.
                    Example: images/aruco_1m_flat_deviceA_001.jpg
                    For synthetic records without images: null is permitted.

fiducialType      : enum ["aruco", "apriltag", "qr", "custom", "none"]
                    The type of fiducial marker present in the image.
                    "none" indicates no marker (environmental imagery).

distanceMeters    : float (positive)
                    Distance from camera optical axis to the fiducial marker,
                    measured along the horizontal ground plane. In meters.
                    Measurement precision: ±0.05 m for real data.

orientation       : enum ["flat", "angled", "tilted", "overhead", "down", "unknown"]
                    Describes camera/marker relationship.
                    "flat"     → camera level, marker perpendicular to viewing axis
                    "angled"   → camera at a horizontal angle to marker
                    "tilted"   → camera pitched up or down relative to marker
                    "overhead" → camera looking up at a suspended marker
                    "down"     → camera looking down at a ground-plane marker
                    "unknown"  → orientation not recorded

cameraHeightCm    : float (positive)
                    Height of camera above ground plane at capture time. Centimeters.
                    Approximate recording is acceptable at ±2 cm for MVP.

deviceModel       : string
                    Human-readable device model name.
                    Example: "Samsung Galaxy A05s"
                    Example: "HP Laptop Webcam"

deviceAlias       : string
                    Researcher-assigned alias for this physical device unit.
                    Example: "Device-A"
                    Must not be a real identifier. See constitutional rules.

detectionSuccess  : boolean
                    Whether automated fiducial detection succeeded on this sample.
                    false records are valid and must be retained for coverage analysis.
```

#### Optional Fields

```
markerWidthPx     : integer (positive)
                    Detected marker bounding box width in pixels.

markerHeightPx    : integer (positive)
                    Detected marker bounding box height in pixels.

markerAreaPx      : integer (positive)
                    Detected marker bounding box area in pixels.

centerX           : float
                    X coordinate of detected marker center. Pixels from left edge.

centerY           : float
                    Y coordinate of detected marker center. Pixels from top edge.

markerPhysicalSizeMm : float (positive)
                    Physical size of the printed marker in millimeters.
                    For square markers, this is the side length.

bearingDegrees    : float (-180.0 to 180.0)
                    Estimated bearing from camera axis to marker.
                    0 = directly ahead, positive = right, negative = left.

pitchDegrees      : float (-90.0 to 90.0)
                    Camera pitch at capture time. Positive = tilted up.

yawDegrees        : float (-180.0 to 180.0)
                    Camera yaw at capture time.

lightingCondition : enum ["indoor_artificial", "indoor_natural", "outdoor", "unknown"]

environmentType   : enum ["hallway", "room", "outdoor", "lab", "unknown"]

syntheticParameters : object
                    Present only for sourceType = "synthetic" or "hybrid".
                    Must document all generation parameters used to produce this record.
                    See SYNTHETIC_GENERATION_GUIDE.md for structure.

notes             : string
                    Freeform observations about this specific sample.
                    Document anomalies, collection circumstances, or known issues.
```

#### Prohibited Fields (Never Add)

The following fields must never appear in any Auriga dataset:

```
PROHIBITED:
  - deviceSerialNumber
  - imei
  - androidId
  - macAddress
  - hardwareFingerprint
  - collectorName
  - collectorEmail
  - collectorPhone
  - subjectName
  - gpsCoordinates (precise)
  - homeAddress
  - Any field uniquely identifying a person
```

---

## 3. Dataset Families

### 3.1 Tier 1 — Immediate MVP Priority

#### Dataset Family: `fiducials_aruco`

**Purpose:** Calibration and validation data for the Virtual Fiducial methodology. Records the apparent pixel dimensions of ArUco markers at known real-world distances.

**Primary hypothesis supported:** Pixel appearance of known-size markers correlates predictably with distance under controlled conditions.

**Minimum viable dataset composition:**

| Condition Axis | Required Values |
|---|---|
| Distance | 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0 meters |
| Orientation | flat, angled, down |
| Camera height | Standard holding height (≈120 cm), low (≈80 cm), high (≈150 cm) |
| Device | At least 1 device (Device-A: Samsung Galaxy A05s) |
| Detection outcomes | Both successes and failures |

**Required fields:** All Required fields in canonical schema.

**Recommended optional fields:** `markerWidthPx`, `markerHeightPx`, `markerAreaPx`, `centerX`, `centerY`, `markerPhysicalSizeMm`, `environmentType`, `lightingCondition`

**Quality thresholds (for validation pass):**

| Metric | Threshold |
|---|---|
| Schema completeness | 100% of required fields |
| Image presence | 100% of referenced images must exist |
| Detection success rate | Report actual rate; no minimum imposed for MVP |
| Duplicate records | 0 tolerated |
| Distance value range | 0.1 m – 20.0 m (outside this range → outlier flag) |
| Marker dimensions | Width and height > 0 px when detectionSuccess = true |

**Naming convention:**
```
fiducials_aruco_v1
fiducials_aruco_v2
fiducials_aruco_v3
```

**Expected record count — MVP:** ≥ 50 records. Research debt RD-001 addresses minimum statistical validity.

---

#### Dataset Family: `perspective_validation`

**Purpose:** Images and metadata supporting validation of perspective-grid world models and vanishing point estimation.

**Primary hypothesis supported:** Indoor structured environments contain sufficient perspective cues to support geometric reasoning without IMU sensors.

**Minimum viable dataset composition:**

| Condition Axis | Required Values |
|---|---|
| Environment | Hallway (primary), room (secondary) |
| Viewpoint | Centered, left-offset, right-offset |
| Camera height | Standard holding height |
| Content | Floor visible, walls visible, ceiling visible |

**Required fields:** `recordId`, `datasetVersion`, `sourceType`, `captureTimestamp`, `filename`, `imagePath`, `fiducialType` (= "none"), `orientation`, `cameraHeightCm`, `deviceModel`, `deviceAlias`, `detectionSuccess` (= false)

**Additional required fields for this family:**
```
environmentType   : required (not optional for this family)
lightingCondition : required (not optional for this family)
```

**Naming convention:**
```
perspective_hallway_v1
perspective_room_v1
```

---

### 3.2 Tier 2 — Post-Geometric Integration

#### Dataset Family: `hazard_ground`

**Purpose:** Samples of ground-level obstacles for training and validating hazard detection.

**Examples:** Water bottles, bags, shoes, extension cords, small steps.

**Status:** Architectural placeholder. Not collected during MVP phase.

**Naming convention:**
```
hazard_ground_v1
```

---

#### Dataset Family: `hazard_suspended`

**Purpose:** Samples of suspended or elevated obstacles.

**Examples:** Open cupboard doors, hanging objects, low signage, branches.

**Status:** Architectural placeholder. Not collected during MVP phase.

---

#### Dataset Family: `hazard_stairs`

**Purpose:** Staircase and elevation transition samples.

**Examples:** Ascending stairs, descending stairs, ramps, door thresholds.

**Status:** Architectural placeholder. Not collected during MVP phase.

---

### 3.3 Tier 3 — Navigation Intelligence

#### Dataset Family: `place_memory`

**Purpose:** Visual anchors and environment fingerprints supporting familiar-environment recognition.

**Constitutional constraint:** Place memory data must remain on-device. This dataset family is for research validation only and must never be used to build cloud-hosted environment maps.

**Status:** Architectural placeholder. Not collected during MVP phase.

---

#### Dataset Family: `navigation_logs`

**Purpose:** Timestamped records of navigation trial events.

**Fields (preliminary):**
```
trialId           : string (UUID)
sessionTimestamp  : string (ISO 8601)
eventType         : enum ["detection", "warning", "navigation", "correction", "completion"]
perceptionOutput  : object (structured output from perception subsystem)
userAction        : string (optional freeform)
outcomeAssessment : string (optional human review notes)
deviceAlias       : string
environmentType   : enum
```

**Status:** Architectural placeholder. Not collected during MVP phase.

---

## 4. Dataset Composition Rules

### 4.1 Real Dataset Rules

- Must be collected under documented conditions.
- Collection protocol must be documented before collection begins (see DATA_INGESTION_GUIDE.md).
- All metadata must be recorded at collection time, not reconstructed later.
- Provenance must include: who collected it, when, with what device, in what environment.

### 4.2 Synthetic Dataset Rules

- Must carry `sourceType: "synthetic"`.
- Must include `syntheticParameters` documenting all generation inputs.
- Must not be mixed with real data in the same dataset version without explicit hybrid classification.
- Distribution comparison to real data must be documented before synthetic data may be used in downstream repositories.

### 4.3 Hybrid Dataset Rules

- Must carry `sourceType: "hybrid"`.
- Must document which records are real and which are synthetic (via `sourceType` per record).
- Must carry a `hybridRationale` field at the dataset level explaining the purpose of the combination.
- Must pass distribution comparison checks.

---

## 5. Minimum Coverage Requirements

Before a dataset may be promoted to `candidate` status, it must satisfy minimum coverage requirements.

### 5.1 Fiducial Datasets

**Required coverage (MVP):**

```
Distances:       At least 5 distinct distance values covered
Orientations:    At least 2 orientation types covered
Devices:         At least 1 device covered
Detection:       Both successes and failures present (if applicable)
```

**Recommended coverage (full validation):**

```
Distances:       0.5 m – 5.0 m at 0.5 m increments (10 values)
Orientations:    flat, angled, down (3 values)
Camera heights:  ≥ 2 distinct heights
Devices:         ≥ 1 device
```

Coverage gaps must be documented in the validation report.

### 5.2 Research Debt

RD-001 — Minimum sample count per condition is not yet empirically validated. Current thresholds are design estimates. Empirical calibration is required before Tier 2 dataset collection begins.

---

## 6. Version Naming Reference

### Format
```
{dataset_family}_{subtype}_v{n}
```

### Examples

| Dataset | Version string |
|---|---|
| ArUco calibration v1 | `fiducials_aruco_v1` |
| ArUco calibration v2 | `fiducials_aruco_v2` |
| Hallway perspective v1 | `perspective_hallway_v1` |
| Ground hazard v1 | `hazard_ground_v1` |
| ArUco synthetic v1 | `fiducials_aruco_synthetic_v1` |
| ArUco hybrid v1 | `fiducials_aruco_hybrid_v1` |

---

## 7. Dataset Registry Entry Format

Each approved dataset is registered in `registry/dataset_registry.json`.

```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "family": "fiducials_aruco",
  "status": "approved",
  "sourceType": "real",
  "recordCount": 96,
  "schemaVersion": "canonical_v1",
  "approvedDate": "2026-06-16",
  "approver": "Project Lead",
  "checksum": "sha256:abc123...",
  "reportPath": "reports/fiducials_aruco_v2_report.md",
  "exportPath": "exports/fiducials_aruco_v2.zip",
  "supersedes": "fiducials_aruco_v1",
  "knownLimitations": [
    "Collected in a single indoor environment",
    "Single device only",
    "No outdoor samples"
  ],
  "researchDebtItems": ["RD-001"]
}
```

---

## 8. Human Approval Record

| Field | Value |
|---|---|
| Document | DATASET_SPECIFICATIONS.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
