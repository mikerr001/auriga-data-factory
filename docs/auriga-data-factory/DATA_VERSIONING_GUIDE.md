# DATA_VERSIONING_GUIDE.md
# Auriga Data Factory — Data Versioning Guide

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This guide defines the complete versioning system for Auriga datasets. It specifies naming conventions, lifecycle states, immutability guarantees, promotion procedures, and registry management.

Scientific traceability is a foundational principle of Project Auriga. Every change to a dataset must be recorded as a new version rather than overwriting a previous one. This ensures that any result produced by any downstream repository can be traced back to the exact dataset version that produced it.

---

## 2. Core Versioning Principles

### P1: Immutability After Approval
Once a dataset reaches `approved` status, it is immutable. Its records, images, metadata, and checksums must never be altered. If corrections are necessary, a new version must be created.

### P2: Linear Versioning
Versions are numbered sequentially. There are no branches, forks, or parallel version trees for a given dataset family. This simplifies traceability and avoids merge conflicts in research workflows.

### P3: Provenance Preservation
Every version must document what changed from its predecessor and why. Version history is a scientific record, not just a technical convenience.

### P4: Superposition of Versions
Older approved versions are never deleted. They remain available for comparison, reproduction, and regression analysis.

### P5: Explicit Hybrid Classification
Synthetic and hybrid datasets receive distinct version namespaces from real datasets, preventing silent contamination of real-data baselines.

---

## 3. Version Naming Convention

### 3.1 Format

```
{dataset_family}_{subtype}_v{n}
```

| Component | Description | Example |
|---|---|---|
| `dataset_family` | The broad dataset category | `fiducials`, `perspective`, `hazard`, `place_memory`, `navigation` |
| `subtype` | The specific variant | `aruco`, `hallway`, `ground`, `synthetic`, `hybrid` |
| `v{n}` | Sequential integer version | `v1`, `v2`, `v3` |

### 3.2 Examples

| Description | Version Identifier |
|---|---|
| First ArUco calibration dataset | `fiducials_aruco_v1` |
| Second ArUco dataset (extended) | `fiducials_aruco_v2` |
| Synthetic ArUco extension | `fiducials_aruco_synthetic_v1` |
| Hybrid ArUco (real + synthetic) | `fiducials_aruco_hybrid_v1` |
| First hallway perspective dataset | `perspective_hallway_v1` |
| Ground hazard first collection | `hazard_ground_v1` |

### 3.3 Naming Rules

- Use lowercase only.
- Use underscores as separators.
- No spaces, hyphens, or special characters except underscores.
- Version numbers are always integers starting at 1.
- Do not skip version numbers (no `v1` then `v3`).
- Do not use descriptive labels in place of version numbers (`_final`, `_corrected`, `_new`).

---

## 4. Dataset Lifecycle States

Every dataset passes through a defined sequence of states. State transitions are logged in `registry/dataset_registry.json`.

```
RAW
  │
  │  (ingestion + normalization)
  ▼
STAGED
  │
  │  (automated validation)
  ├── FAIL ──→ REJECTED
  │
  ▼ PASS
VALIDATED
  │
  │  (coverage analysis + report generation)
  ▼
CANDIDATE
  │
  │  (human review)
  ├── REJECT ──→ REJECTED
  │
  ▼ APPROVE
APPROVED  ←── immutable from this point forward
  │
  │  (export pipeline)
  ▼
DISTRIBUTED
```

### State Definitions

| State | Description | Mutable? |
|---|---|---|
| `raw` | Ingested but not yet validated. May contain errors. | Yes |
| `staged` | Normalized to canonical schema. Awaiting validation. | Yes |
| `validated` | Passed all automated validation checks. Ready for human review. | Yes (minor corrections only) |
| `candidate` | Validation report complete. Awaiting human approval decision. | No |
| `approved` | Human-approved. Immutable. Assigned permanent version identifier. | **No** |
| `rejected` | Failed validation or human review. Archived for reference. | No |
| `distributed` | Exported and delivered to downstream consumers. | No |

### Rejected State

Rejected datasets are never silently discarded. They are archived to `datasets/rejected/` with the rejection report attached. This preserves research value and supports retrospective analysis.

---

## 5. Promotion Procedure

### Step 1: Ingestion → Staged

```
trigger: new data files added to datasets/raw/
action:  run ingestor
output:  staged dataset with canonical schema applied
```

### Step 2: Staged → Validated

```
trigger: manual or automated validation run
action:  run validator
output:  validation report in reports/
         dataset moves to datasets/validated/
         OR dataset moves to datasets/rejected/ if blocking failures
```

### Step 3: Validated → Candidate

```
trigger: validation report reviewed for completeness
action:  run coverage analyzer
output:  coverage report appended to validation report
         dataset promoted to candidate status in registry
```

### Step 4: Candidate → Approved

```
trigger: project lead reviews candidate report
action:  project lead issues approval decision
         (see HUMAN_DATA_APPROVAL_GUIDE.md for full procedure)
output:  dataset written to datasets/approved/
         checksum generated and stored
         registry entry updated to approved
         version identifier permanently assigned
         dataset becomes immutable
```

### Step 5: Approved → Distributed

```
trigger: downstream repository requests dataset
action:  export pipeline packages approved dataset
output:  export bundle in exports/
         downstream consumer notified of export path and checksum
```

---

## 6. Version Registry

### 6.1 Registry File

The global version registry is maintained at:

```
registry/dataset_registry.json
```

This is the single source of truth for all dataset versions across the Data Factory.

### 6.2 Registry Entry Schema

```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "family": "fiducials_aruco",
  "status": "approved",
  "sourceType": "real",
  "recordCount": 96,
  "schemaVersion": "canonical_v1",
  "createdDate": "2026-05-01",
  "validatedDate": "2026-05-03",
  "approvedDate": "2026-06-16",
  "approver": "Project Lead",
  "approvalNotes": "All validation checks passed. Minor coverage gap at 4.5m noted.",
  "checksum": "sha256:abc123...",
  "checksumAlgorithm": "sha256",
  "reportPath": "reports/fiducials_aruco_v2_report.md",
  "exportPath": "exports/fiducials_aruco_v2.zip",
  "supersedes": "fiducials_aruco_v1",
  "supersededBy": null,
  "knownLimitations": [
    "Single indoor environment",
    "Single device (Device-A)",
    "No outdoor samples"
  ],
  "researchDebtItems": ["RD-001"],
  "distributedTo": []
}
```

### 6.3 Registry Rules

- The registry is append-only. Entries are never modified after approval.
- The `supersedes` field links versions into a traceable chain.
- The `supersededBy` field is updated when a newer version is approved.
- The registry must be committed to GitHub alongside every approved dataset.

---

## 7. Immutability Implementation

### 7.1 File System Enforcement

Approved datasets are stored in `datasets/approved/` which is treated as read-only.

```python
# Pseudo-implementation reference
def promote_to_approved(dataset_id: str, approval_record: dict) -> None:
    """
    Move a candidate dataset to immutable approved storage.
    Generates and stores a content checksum.
    Writes dataset to approved/ directory.
    Registers in dataset_registry.json.
    """
    candidate_path = f"datasets/validated/{dataset_id}"
    approved_path = f"datasets/approved/{dataset_id}"

    checksum = compute_sha256(candidate_path)
    write_to_approved(candidate_path, approved_path)
    write_checksum_manifest(approved_path, checksum)
    update_registry(dataset_id, status="approved", checksum=checksum)
    record_approval(dataset_id, approval_record)
```

### 7.2 Checksum Verification

Every approved dataset carries a `checksum_manifest.json` file alongside it:

```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "checksumAlgorithm": "sha256",
  "manifestChecksum": "sha256:...",
  "files": {
    "metadata.csv": "sha256:...",
    "images/aruco_1m_flat_001.jpg": "sha256:...",
    "images/aruco_1m_flat_002.jpg": "sha256:..."
  }
}
```

### 7.3 Integrity Verification Script

Any downstream consumer may verify an approved dataset:

```python
# Pseudo-implementation reference
def verify_dataset_integrity(dataset_version: str) -> bool:
    """
    Recomputes checksums for all files in an approved dataset.
    Returns True if all checksums match the stored manifest.
    Raises IntegrityError if any file has been modified.
    """
```

### 7.4 Modification Attempt Handling

If any process attempts to write to an approved dataset path:
1. The operation is blocked.
2. An integrity alert is logged.
3. A human notification is generated.

---

## 8. Correction Workflow

When errors are found in an approved dataset:

### Step 1: Document the error
Create an issue in the Data Factory repository describing:
- The affected dataset version.
- The nature of the error.
- The affected records (by `recordId`).
- The proposed correction.

### Step 2: Create a corrected candidate
- Do **not** modify the approved dataset.
- Prepare a corrected version of the raw data.
- Run the full ingestion → validation → coverage → candidate pipeline on the corrected data.

### Step 3: Reference the correction
In the new dataset's registry entry:
```json
{
  "supersedes": "fiducials_aruco_v2",
  "correctionNotes": "Corrected distanceMeters values for records recorded at 3.0m. Original tape measure error discovered during v3 collection."
}
```

### Step 4: Approve the new version
Follow the standard human approval procedure.

### Step 5: Mark the original version
Update the original registry entry's `supersededBy` field:
```json
{
  "supersededBy": "fiducials_aruco_v3",
  "supersessionReason": "Measurement error corrected in v3"
}
```

The original version remains in `datasets/approved/`. It is never deleted.

---

## 9. Downstream Dependency Tracking

When a downstream repository begins using a dataset version:

1. The requesting repository must record which dataset version it depends on.
2. The Data Factory registry entry's `distributedTo` field must be updated.
3. When a new version is released, dependent repositories are notified.

```json
"distributedTo": [
  {
    "repository": "auriga-core",
    "distributedDate": "2026-06-16",
    "purpose": "Virtual Fiducial distance estimation calibration"
  }
]
```

---

## 10. Version Compatibility Policy

- Downstream repositories **should** migrate to newer dataset versions when available.
- Downstream repositories **may** continue using older approved versions if compatibility concerns exist.
- Any repository pinned to an older version must document its reasons in its own research debt log.
- Critically corrected versions (safety-relevant errors) **must** prompt immediate migration with a documented timeline.

---

## 11. Research Debt

| ID | Question |
|---|---|
| RD-006 | Should a formal semantic versioning policy (major/minor/patch) replace the simple sequential numbering? |
| RD-007 | Should the registry be migrated from JSON to a lightweight SQLite database as the dataset count grows? |

---

## 12. Human Approval Record

| Field | Value |
|---|---|
| Document | DATA_VERSIONING_GUIDE.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
