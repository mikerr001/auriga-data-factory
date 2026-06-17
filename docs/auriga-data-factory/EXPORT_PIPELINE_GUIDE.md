# EXPORT_PIPELINE_GUIDE.md
# Auriga Data Factory — Export Pipeline Guide

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This guide defines how approved Auriga datasets are packaged and distributed to downstream repositories. It covers export formats, packaging procedures, downstream request contracts, integrity verification, and constitutional constraints on distribution.

The export pipeline is the final stage of the Data Factory pipeline. It must enforce two guarantees:

1. **Only approved datasets may be exported.** Validated-but-not-approved datasets must never reach downstream consumers.
2. **Exported datasets are integrity-verified.** Every export bundle carries checksums so consumers can verify they received an unmodified copy of the approved dataset.

---

## 2. Constitutional Rules for Export

- Only datasets with `status: approved` in the registry may be exported.
- Synthetic datasets must be clearly identified as synthetic in the export bundle.
- Hybrid datasets must include per-record source type labels.
- No export may include prohibited fields (device serial numbers, personal identifiers).
- Downstream consumers must reference the exported dataset version in their own documentation.

---

## 3. Export Formats

The Data Factory supports three export formats. All formats are generated from the same approved dataset source.

### Format 1: Canonical JSON Bundle (Primary)

**Use case:** Downstream Python code, Colab notebooks, Auriga core repositories.

**Structure:**
```
{dataset_version}_bundle/
├── manifest.json           ← Dataset metadata and file inventory
├── metadata.json           ← All records in JSON array format
├── images/                 ← All referenced image files
│   ├── aruco_1p0m_flat_deviceA_001.jpg
│   └── ...
├── checksum_manifest.json  ← SHA-256 checksums for all files
└── RELEASE_NOTES.md        ← Human-readable release summary
```

**`manifest.json` structure:**
```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "exportFormat": "canonical_json_bundle",
  "exportDate": "2026-06-16T14:30:00Z",
  "dataFactoryVersion": "1.0.0",
  "schemaVersion": "canonical_v1",
  "sourceType": "real",
  "recordCount": 96,
  "imageCount": 96,
  "approvedDate": "2026-06-16",
  "approver": "Project Lead",
  "checksumAlgorithm": "sha256",
  "manifestChecksum": "sha256:...",
  "reportPath": "See reports/fiducials_aruco_v2_report.md in auriga-data-factory",
  "knownLimitations": ["Single environment", "Single device"],
  "researchDebtItems": ["RD-001"]
}
```

### Format 2: CSV Export (Analysis)

**Use case:** Spreadsheet analysis, quick inspection, Pandas DataFrames.

**Structure:**
```
{dataset_version}_csv/
├── metadata.csv            ← All records in CSV format (canonical column names)
├── checksum_manifest.json
└── RELEASE_NOTES.md
```

**Note:** CSV export does not include images. It is intended for metadata analysis only.

### Format 3: Colab Bundle (Notebooks)

**Use case:** Google Colab analysis notebooks.

**Structure:**
```
{dataset_version}_colab.zip   ← Single zip file containing:
  ├── metadata.csv
  ├── metadata.json
  ├── images/
  ├── checksum_manifest.json
  ├── RELEASE_NOTES.md
  └── sample_notebook.ipynb   ← Starter Colab notebook for this dataset
```

---

## 4. Export Package Contents Reference

### `checksum_manifest.json`

```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "algorithm": "sha256",
  "generatedAt": "2026-06-16T14:30:00Z",
  "files": {
    "manifest.json": "sha256:abc123...",
    "metadata.json": "sha256:def456...",
    "metadata.csv": "sha256:ghi789...",
    "images/aruco_1p0m_flat_deviceA_001.jpg": "sha256:jkl012...",
    "images/aruco_1p0m_flat_deviceA_002.jpg": "sha256:mno345..."
  }
}
```

### `RELEASE_NOTES.md`

```markdown
# Release Notes — {dataset_version}

**Release date:** {date}
**Export format:** {format}
**Record count:** {n}
**Approved by:** Project Lead
**Approval date:** {date}

## What's in this dataset

{brief description}

## Changes from previous version

{changes or "First release of this dataset family."}

## Known limitations

{list}

## Research debt items

{list of open RD items}

## How to cite this dataset

Project Auriga Data Factory, {dataset_version}, exported {date}.
Repository: auriga-data-factory
```

---

## 5. Export Pipeline Procedure

### Step 1: Verify approved status

```python
from factory.versioning.version_manager import VersionManager

vm = VersionManager()
status = vm.get_status("fiducials_aruco_v2")
assert status == "approved", f"Cannot export dataset with status: {status}"
```

### Step 2: Load approved dataset

```python
dataset = vm.load_approved("fiducials_aruco_v2")
```

### Step 3: Verify integrity against stored checksums

```python
from factory.versioning.version_manager import verify_integrity

integrity_ok = verify_integrity("fiducials_aruco_v2")
assert integrity_ok, "Integrity check failed — dataset may have been modified after approval"
```

### Step 4: Select export format

```python
from factory.export.export_pipeline import ExportPipeline

pipeline = ExportPipeline(export_dir="exports/")

# Choose format:
pipeline.export_canonical_json("fiducials_aruco_v2")
# or
pipeline.export_csv("fiducials_aruco_v2")
# or
pipeline.export_colab_bundle("fiducials_aruco_v2")
```

### Step 5: Register distribution

```python
vm.register_distribution(
    dataset_version="fiducials_aruco_v2",
    requesting_repository="auriga-core",
    distribution_date="2026-06-16",
    purpose="Virtual Fiducial distance estimation calibration",
    export_format="canonical_json_bundle"
)
```

---

## 6. Downstream Consumer Guide

### 6.1 How to Request a Dataset

A downstream repository requests a dataset by specifying a request contract:

```json
{
  "requestingRepository": "auriga-core",
  "datasetFamily": "fiducials_aruco",
  "minimumVersion": "v1",
  "preferredVersion": "latest",
  "requiredFields": ["distanceMeters", "markerWidthPx", "detectionSuccess"],
  "sourceTypes": ["real"],
  "requestDate": "2026-06-16",
  "purpose": "Virtual Fiducial distance estimation calibration lookup table"
}
```

### 6.2 Response Contract

The Data Factory responds with:

```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "status": "approved",
  "exportFormat": "canonical_json_bundle",
  "exportPath": "exports/fiducials_aruco_v2_bundle/",
  "zipPath": "exports/fiducials_aruco_v2_bundle.zip",
  "checksum": "sha256:...",
  "recordCount": 96,
  "approvedDate": "2026-06-16",
  "releaseNotesPath": "exports/fiducials_aruco_v2_bundle/RELEASE_NOTES.md"
}
```

### 6.3 Consumer Obligations

Every downstream repository consuming an Auriga dataset must:

1. Record the dataset version it depends on in its own documentation.
2. Verify the export checksum before using the dataset.
3. Monitor the Data Factory registry for superseding versions.
4. Document its own known limitations relative to the dataset.
5. Never re-export or redistribute the dataset without referencing its provenance.

### 6.4 Consumer Integrity Verification

```python
import hashlib, json

def verify_export_checksum(export_dir: str) -> bool:
    """
    Verifies all files in an export bundle against stored checksums.
    Returns True if all checksums match.
    """
    manifest_path = f"{export_dir}/checksum_manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    for relative_path, expected_checksum in manifest["files"].items():
        full_path = f"{export_dir}/{relative_path}"
        with open(full_path, "rb") as f:
            actual = "sha256:" + hashlib.sha256(f.read()).hexdigest()
        if actual != expected_checksum:
            print(f"CHECKSUM MISMATCH: {relative_path}")
            return False

    print("All checksums verified.")
    return True
```

---

## 7. Export Directory Structure

```
exports/
├── fiducials_aruco_v1_bundle/
│   ├── manifest.json
│   ├── metadata.json
│   ├── metadata.csv
│   ├── images/
│   ├── checksum_manifest.json
│   └── RELEASE_NOTES.md
├── fiducials_aruco_v1_bundle.zip
├── fiducials_aruco_v2_bundle/
│   └── ...
├── fiducials_aruco_v2_bundle.zip
└── fiducials_aruco_v2_colab.zip
```

Old export bundles are retained. They are never deleted once a downstream consumer has referenced them.

---

## 8. Version Update Notifications

When a new version of a dataset is approved, the Data Factory must notify all registered downstream consumers.

**Notification format:**

```markdown
# Dataset Update Notification

New version available: fiducials_aruco_v3
Supersedes: fiducials_aruco_v2

Changes:
- Extended distance coverage to 5.0 m
- Added Device-B samples
- Corrected 3 inconsistency flags from v2 report

Known limitations in v3:
- No outdoor samples
- Limited overhead orientation samples

Recommendation for fiducials_aruco_v2 consumers:
Review v3 for migration. No breaking schema changes.
```

Notifications are posted as entries in `registry/dataset_registry.json` under the `notifications` array.

---

## 9. Research Debt

| ID | Question |
|---|---|
| RD-018 | Should future exports support a streaming or API-based distribution model rather than file bundles? |
| RD-019 | Should the Colab bundle auto-generate analysis code specific to each dataset family? |

---

## 10. Human Approval Record

| Field | Value |
|---|---|
| Document | EXPORT_PIPELINE_GUIDE.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
