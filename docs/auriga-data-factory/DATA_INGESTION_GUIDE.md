# DATA_INGESTION_GUIDE.md
# Auriga Data Factory — Data Ingestion Guide

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This guide defines how raw data enters the Auriga Data Factory. It covers collection protocols, file conventions, ingestion scripts, normalization procedures, and legacy data migration.

Ingestion is the first stage of the Data Factory pipeline. Quality at ingestion determines quality throughout. Data that enters the pipeline with structural inconsistencies, missing fields, or ambiguous metadata is significantly more expensive to repair than data collected correctly from the start.

---

## 2. Pre-Collection Checklist

Before collecting any new data, verify that the following conditions are met.

### 2.1 Protocol Checklist

```
□ A dataset version identifier has been assigned (e.g., fiducials_aruco_v3)
□ The collection protocol for this dataset family has been reviewed
□ The collection environment matches the planned conditions
□ The measurement instrument has been verified (tape measure, ruler)
□ The device is identified (model name and alias assigned)
□ The fiducial marker is the correct physical size (measured before collection)
□ The image naming convention has been confirmed
□ The CSV template has been prepared and field names verified
□ The canonical schema has been reviewed for any new required fields
```

### 2.2 Equipment Checklist (Fiducial Datasets)

```
□ Fiducial marker (correct type, correct physical size)
□ Measuring tape or laser distance meter (± 0.05 m precision minimum)
□ Device (correct model, alias assigned)
□ Something to mark distances on the floor (tape, chalk, markers)
□ Notepad for session notes
□ Camera app that records capture timestamp (or manual timestamp recording method)
```

---

## 3. Field Recording Guide

This section provides field-by-field guidance for accurate metadata recording during collection.

### 3.1 `distanceMeters`

**What to measure:** The distance from the camera's approximate optical axis (front of the phone, centre of lens) to the nearest face of the fiducial marker.

**How to measure:** Place a physical marker at the measurement point on the floor. Measure from the toe line (standing position of the collector) to the marker face.

**Precision:** Record to 2 decimal places (e.g., 1.50, not 1.5).

**Common errors:**
- Measuring to the wall the marker is on rather than the marker face.
- Measuring from the back of the phone rather than the lens.
- Not maintaining consistent standing position across samples.

### 3.2 `cameraHeightCm`

**What to measure:** The height of the camera lens above the floor surface when holding the device in the intended capture posture.

**How to measure:** Hold the device in the capture posture. Have an assistant measure from the floor to the camera lens. Alternatively, measure once per session and note if posture changes.

**Precision:** Record to nearest centimeter.

**Common errors:**
- Recording height in meters instead of centimeters.
- Measuring when the device is flat on a table rather than in hand.
- Not recording when height changes during a session.

### 3.3 `orientation`

**What to record:** The spatial relationship between the camera and the marker at the time of capture.

| Value | When to use |
|---|---|
| `flat` | Camera level, marker mounted on a vertical surface at approximately eye level |
| `angled` | Camera level, but angled horizontally relative to the marker face |
| `tilted` | Camera pitched upward or downward relative to the marker |
| `overhead` | Camera aimed upward at a marker mounted overhead |
| `down` | Camera aimed downward at a marker on the floor or a low surface |
| `unknown` | Orientation was not recorded during collection |

**Important:** Avoid using `unknown` unless the information is genuinely irrecoverable. `unknown` reduces the analytical value of the dataset.

### 3.4 `deviceModel` and `deviceAlias`

**`deviceModel`:** Record the full manufacturer model name. Example: `Samsung Galaxy A05s`. Do not use abbreviations unless the full name is documented elsewhere.

**`deviceAlias`:** The researcher-assigned label for this physical unit. Example: `Device-A`. If you have only one phone, use `Device-A`. If you add a second device later, call it `Device-B`.

**Constitutional rule:** Never record serial numbers, IMEI numbers, Android IDs, or any unique hardware identifier.

### 3.5 `captureTimestamp`

**Format:** ISO 8601 with UTC timezone: `2026-06-16T14:30:00Z`.

**For real collections:** Record the actual time of capture if possible. If exact timestamps are unavailable, record the session date and note in `notes` that precise timestamps were not recorded.

**Acceptable fallback:** `2026-06-16T00:00:00Z` with a note: "Date only — exact capture time not recorded."

**Do not leave blank:** An approximate timestamp is better than no timestamp.

### 3.6 `filename` and `imagePath`

**Filename convention:**

```
{fiducialType}_{distanceMeters}m_{orientation}_{deviceAlias}_{sequence}.jpg
```

**Examples:**
```
aruco_1p0m_flat_deviceA_001.jpg
aruco_2p5m_down_deviceA_003.jpg
aruco_1p5m_angled_deviceA_002.jpg
```

**Rules:**
- Use `p` as the decimal separator (e.g., `1p5` = 1.5 m) to avoid issues with dots in filenames.
- Sequence numbers are zero-padded to 3 digits (001, 002, 003).
- Use lowercase only.
- No spaces.

**`imagePath`:** Relative path from dataset root. Example: `images/aruco_1p0m_flat_deviceA_001.jpg`.

### 3.7 `detectionSuccess`

**How to determine:** Run ArUco detection on the image after capture. Record `true` if the marker was detected, `false` if it was not.

**Important:** Do not delete failed detection samples. Non-detections are scientifically valuable — they characterize the detection boundary of the algorithm.

### 3.8 `notes`

Use `notes` to record anything unusual:
- Reflections, shadows, unusual lighting.
- Marker was slightly rotated.
- Phone case partially obscured lens.
- Distance was approximate due to obstacles.
- Sample was recaptured due to motion blur.

Do not leave `notes` blank when unusual circumstances were present.

---

## 4. CSV Collection Format

The primary collection tool outputs CSV files. The CSV template must conform to the canonical schema column names.

### 4.1 Required CSV Column Names

```csv
recordId,datasetVersion,sourceType,captureTimestamp,filename,imagePath,fiducialType,distanceMeters,orientation,cameraHeightCm,deviceModel,deviceAlias,detectionSuccess,markerWidthPx,markerHeightPx,markerAreaPx,centerX,centerY,markerPhysicalSizeMm,notes
```

### 4.2 Example CSV Row

```csv
,fiducials_aruco_v3,real,2026-06-16T14:30:00Z,aruco_1p0m_flat_deviceA_001.jpg,images/aruco_1p0m_flat_deviceA_001.jpg,aruco,1.00,flat,120.0,Samsung Galaxy A05s,Device-A,true,312,308,96096,640.5,480.2,100.0,Clear conditions. Standard hallway.
```

**Note:** The `recordId` field is left blank in the CSV. The ingestor generates UUID v4 values at ingestion time.

### 4.3 CSV Field Type Reference

| Field | CSV Type | Example |
|---|---|---|
| recordId | blank (generated at ingestion) | |
| datasetVersion | string | fiducials_aruco_v3 |
| sourceType | string | real |
| captureTimestamp | string ISO 8601 | 2026-06-16T14:30:00Z |
| filename | string | aruco_1p0m_flat_deviceA_001.jpg |
| imagePath | string | images/aruco_1p0m_flat_deviceA_001.jpg |
| fiducialType | string | aruco |
| distanceMeters | float | 1.00 |
| orientation | string | flat |
| cameraHeightCm | float | 120.0 |
| deviceModel | string | Samsung Galaxy A05s |
| deviceAlias | string | Device-A |
| detectionSuccess | boolean | true |
| markerWidthPx | integer (blank if no detection) | 312 |
| markerHeightPx | integer (blank if no detection) | 308 |
| markerAreaPx | integer (blank if no detection) | 96096 |
| centerX | float (blank if no detection) | 640.5 |
| centerY | float (blank if no detection) | 480.2 |
| markerPhysicalSizeMm | float | 100.0 |
| notes | string | Clear conditions. |

---

## 5. Directory Structure for a New Collection

Before running the ingestor, organize your collection files as follows:

```
datasets/raw/{dataset_version}/
├── metadata.csv              ← Collection CSV file
├── images/
│   ├── aruco_1p0m_flat_deviceA_001.jpg
│   ├── aruco_1p0m_flat_deviceA_002.jpg
│   └── ...
├── collection_notes.md       ← Session notes (freeform)
└── device_record.md          ← Device details for this session
```

**`collection_notes.md` template:**

```markdown
# Collection Notes — {dataset_version}

Date: {date}
Collector: {alias or "Project Lead"}
Environment: {description}
Device: {model and alias}
Fiducial: {type, physical size}
Protocol followed: {yes/partially/no — if not, explain}
Unusual circumstances: {description or "None"}
```

**`device_record.md` template:**

```markdown
# Device Record — {dataset_version}

Device alias: Device-A
Device model: Samsung Galaxy A05s
Camera app used: {app name or "default camera"}
Camera resolution: {if known}
Focus mode: {auto / fixed / unknown}
Capture conditions: {handheld / tripod / other}
Firmware version: {if known}
Notes: {any relevant device notes}
```

---

## 6. Ingestion Script

### 6.1 Purpose

The ingestor reads a raw CSV + images directory and produces a normalized dataset conforming to the Auriga Canonical Schema.

### 6.2 What the Ingestor Does

1. Reads `metadata.csv` from the raw dataset directory.
2. Generates `recordId` (UUID v4) for each record.
3. Validates that image paths are correctly formed.
4. Converts field types (e.g., string "true" → boolean True).
5. Normalizes string fields (strip whitespace, lowercase enums).
6. Detects and flags unknown columns.
7. Produces a normalized dataset in `datasets/staged/{dataset_version}/`.
8. Produces an ingestion report documenting any transformations applied.

### 6.3 Python Reference

```python
from factory.ingestion.csv_ingestor import CsvIngestor

ingestor = CsvIngestor()
result = ingestor.ingest(
    raw_path="datasets/raw/fiducials_aruco_v3/",
    dataset_version="fiducials_aruco_v3"
)

print(result.record_count)       # 96
print(result.warnings)           # List of non-blocking issues
result.save_staged("datasets/staged/")
```

### 6.4 Ingestion Report

Every ingestor run produces:

```
reports/{dataset_version}_ingestion_report.md
```

Contents:
- Records processed.
- Records with UUID generated.
- Fields normalized (type conversions applied).
- Unknown fields detected.
- Warnings (non-blocking issues).
- Errors (blocking issues, if any).

---

## 7. Legacy Data Migration

Auriga has existing datasets in multiple formats collected before the canonical schema was established.

### 7.1 Migration Principles

- **Preserve provenance:** Never discard original files during migration.
- **Document transformations:** Every change made during migration must be documented.
- **Mark gaps honestly:** If a field was not recorded and cannot be reliably inferred, set it to null and document why.
- **Do not invent data:** Missing fields should be null, not estimated, unless the estimation method is explicitly documented.

### 7.2 Known Legacy Format — Browser-Based Collector

The existing Auriga web-based collector produced CSV files with the following column structure:

```
filename, width, height, area, centerX, centerY, detected, distance, orientation, camera_height, device, timestamp
```

**Migration mapping:**

| Legacy column | Canonical field | Notes |
|---|---|---|
| filename | filename | Direct map |
| width | markerWidthPx | Type: int |
| height | markerHeightPx | Type: int |
| area | markerAreaPx | Type: int |
| centerX | centerX | Type: float |
| centerY | centerY | Type: float |
| detected | detectionSuccess | Type: boolean |
| distance | distanceMeters | Type: float |
| orientation | orientation | Normalize to enum values |
| camera_height | cameraHeightCm | Check units (may be in cm or m) |
| device | deviceModel | Map to full model name where possible |
| timestamp | captureTimestamp | Convert to ISO 8601 |

**Fields that must be added manually:**
- `recordId`: Generated at migration.
- `datasetVersion`: Assigned during migration.
- `sourceType`: Set to `real`.
- `deviceAlias`: Assign Device-A to all legacy records (single device).
- `fiducialType`: Set to `aruco` for all legacy records.
- `markerPhysicalSizeMm`: Set if known from collection notes; else null.

### 7.3 Migration Validation

After migration, the full 7-layer validation protocol must be run. Legacy datasets are not exempt from validation.

---

## 8. Constitutional Rules for Ingestion

- **Never invent data to fill gaps.** Null is preferable to fabricated values.
- **Never discard original files.** Keep `datasets/raw/` copies permanently.
- **Never ingest without an assigned dataset version identifier.**
- **Never store unique hardware identifiers** (IMEI, serial number, Android ID).
- **Never record collector personal names.** Use project lead, contributor alias, or collection system name.

---

## 9. Research Debt

| ID | Question |
|---|---|
| RD-015 | Should the ingestor support JSON metadata format as a first-class input (alongside CSV)? |
| RD-016 | What strategy should be used to recover timestamps from images where EXIF data exists but CSV timestamps are missing? |
| RD-017 | Should image filenames be enforced by the ingestor (reject non-conforming names) or normalised automatically? |

---

## 10. Human Approval Record

| Field | Value |
|---|---|
| Document | DATA_INGESTION_GUIDE.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
