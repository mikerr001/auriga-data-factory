# DATA_FACTORY_ARCHITECTURE.md
# Auriga Data Factory — System Architecture

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory
**Classification:** Foundational Architecture Document

---

## Constitutional Preamble

This document forms part of the foundational architecture of Project Auriga. All decisions recorded here carry constitutional weight within the Auriga ecosystem. Future agents, contributors, and phases must respect the constraints documented below unless a formal constitutional amendment process explicitly overrides them.

> **Auriga's foundational principle:** Offline-first, privacy-preserving spatial intelligence from a single RGB camera, serving visually impaired users on commodity hardware.

---

## 1. Purpose and Scope

The Auriga Data Factory is the research laboratory of the Auriga ecosystem. Its role is not simply to store files. It is responsible for the systematic ingestion, validation, generation, versioning, and distribution of all datasets used throughout Auriga's development lifecycle.

### 1.1 What the Data Factory Is

- A scientific instrument designed to support rigorous hypothesis testing.
- A quality gate ensuring all datasets meet defined standards before use.
- A versioning system ensuring scientific traceability across Auriga's evolution.
- A synthetic generation engine for controlled experiment design.
- A coverage analysis tool for identifying gaps in real-world data.
- A reporting system for documenting dataset provenance and fitness.
- A distribution interface supplying downstream repositories with reliable inputs.

### 1.2 What the Data Factory Is Not

- It is **not** a production backend service.
- It is **not** a cloud data warehouse.
- It is **not** a machine learning training platform.
- It is **not** a file storage system without governance.
- It is **not** a black-box pipeline that conceals its reasoning.

### 1.3 Scope of This Document

This document describes:
- The overall architecture of the Data Factory.
- Its major subsystems and their responsibilities.
- The data flow model from ingestion to distribution.
- Constitutional constraints that govern all operations.
- Extension points for future phases.

---

## 2. Architectural Principles

The following principles are **non-negotiable** and govern every design decision within the Data Factory.

### P1: Offline-First
The Data Factory must operate without internet access. No step in any pipeline may have a mandatory cloud dependency.

### P2: Explainability Over Opacity
Every transformation, validation, and generation step must produce human-readable rationale. Black-box operations are prohibited unless documented as research debt with an explicit justification.

### P3: Immutability After Approval
Approved datasets are immutable. Corrections require new versions. Prior versions are never overwritten.

### P4: Privacy by Default
No personally identifying information. No unique hardware identifiers. No user-linked spatial data. User spatial memories never leave the device.

### P5: Scientific Traceability
Every dataset must carry provenance metadata sufficient to reproduce the conditions under which it was collected or generated.

### P6: Human Accountability
Automated validation assists but does not replace human judgment. Humans retain final authority over approval decisions.

### P7: Minimal Assumption
The Data Factory must not assume specific hardware beyond a commodity smartphone camera, nor assume internet access, cloud infrastructure, or specialized sensors.

### P8: Extensibility
All subsystems must expose clearly defined interfaces so that future dataset types, validation rules, and generation strategies can be added without redesigning the core architecture.

---

## 3. Repository Structure

The Data Factory lives as a standalone GitHub repository. Development occurs in a Replit environment. GitHub is the canonical source of truth.

```
auriga-data-factory/
├── docs/
│   ├── DATA_FACTORY_ARCHITECTURE.md       ← This document
│   ├── DATASET_SPECIFICATIONS.md
│   ├── DATA_VERSIONING_GUIDE.md
│   ├── DATA_VALIDATION_PROTOCOL.md
│   ├── SYNTHETIC_GENERATION_GUIDE.md
│   ├── COVERAGE_ANALYSIS_GUIDE.md
│   ├── DATASET_REPORT_TEMPLATE.md
│   ├── DATA_INGESTION_GUIDE.md
│   ├── EXPORT_PIPELINE_GUIDE.md
│   └── HUMAN_DATA_APPROVAL_GUIDE.md
│
├── schemas/
│   ├── canonical_metadata_schema_v1.json  ← Canonical metadata specification
│   └── validation_rules_v1.json          ← Automated validation ruleset
│
├── factory/
│   ├── __init__.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── ingestor.py                   ← Base ingestor interface
│   │   ├── csv_ingestor.py               ← CSV + image ingestion
│   │   └── normalizer.py                 ← Legacy format normalizer
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── validator.py                  ← Validation orchestrator
│   │   ├── schema_validator.py           ← Schema compliance checks
│   │   ├── completeness_checker.py       ← Missing data detection
│   │   ├── duplicate_detector.py         ← Duplicate detection
│   │   ├── consistency_checker.py        ← Cross-field consistency
│   │   └── outlier_detector.py           ← Statistical outlier detection
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── generator.py                  ← Base generator interface
│   │   ├── geometry_generator.py         ← Mathematical synthetic generation
│   │   ├── augmentation_generator.py     ← Placeholder: future augmentation
│   │   ├── rendering_generator.py        ← Placeholder: future rendering
│   │   └── ml_generator.py               ← Placeholder: future ML generation
│   ├── versioning/
│   │   ├── __init__.py
│   │   ├── version_manager.py            ← Version registry and promotion
│   │   └── manifest.py                   ← Dataset manifest generator
│   ├── coverage/
│   │   ├── __init__.py
│   │   └── coverage_analyzer.py          ← Coverage gap detection
│   ├── reporting/
│   │   ├── __init__.py
│   │   └── report_generator.py           ← Validation and dataset reports
│   └── export/
│       ├── __init__.py
│       └── export_pipeline.py            ← Dataset export for downstream repos
│
├── datasets/
│   ├── raw/                              ← Ingested but not yet validated
│   ├── validated/                        ← Passed automated validation
│   ├── approved/                         ← Human-approved, immutable
│   └── synthetic/                        ← Synthetically generated datasets
│
├── reports/
│   └── [dataset_name]_[version]_report.md
│
├── registry/
│   └── dataset_registry.json            ← Global dataset version registry
│
├── tests/
│   └── [test files]
│
├── notebooks/
│   └── [Colab-compatible notebooks]
│
├── CONSTITUTION.md                       ← Auriga constitutional rules
├── RESEARCH_DEBT.md                      ← Open research questions
├── README.md
└── requirements.txt
```

---

## 4. Major Subsystems

### 4.1 Ingestion Subsystem

**Responsibility:** Accept raw data from external sources and normalize it to the Auriga Canonical Schema.

**Key operations:**
- Accept CSV + image file bundles.
- Accept JSON metadata + image file bundles.
- Normalize legacy formats with provenance preservation.
- Assign staging identifiers.
- Move normalized data to `datasets/raw/` staging area.

**Constraints:**
- Must preserve original provenance metadata.
- Must never silently discard fields.
- Unknown fields must be flagged, not dropped.

**Status:** Implements immediately. CSV ingestor is the MVP priority.

### 4.2 Validation Subsystem

**Responsibility:** Assess the quality and fitness of staged datasets before human review.

**Validation layers (in order):**

| Layer | Check | Blocking? |
|---|---|---|
| Schema | All required fields present and typed correctly | Yes |
| Completeness | No missing values in mandatory fields | Yes |
| File integrity | All referenced image files exist and are readable | Yes |
| Duplicate detection | No duplicate entries by filename or coordinates | Yes |
| Consistency | Cross-field logical consistency (e.g., distanceMeters > 0) | Yes |
| Outlier detection | Statistical outliers flagged for human review | No (flag only) |
| Coverage analysis | Coverage gaps identified and reported | No (flag only) |

**Output:** A structured validation report in Markdown and JSON.

**Status:** Core layers implemented in MVP. Outlier and coverage layers are MVP.

### 4.3 Synthetic Generation Subsystem

**Responsibility:** Produce mathematically derived synthetic datasets that extend real-world data coverage.

**Architecture:**

```
SyntheticGenerator (abstract base)
├── GeometryGenerator          ← IMPLEMENT NOW
│   ├── FiducialSizeModel       distance → apparent pixel dimensions
│   ├── PerspectiveModel        camera pitch/yaw → projective transforms
│   ├── BearingModel            lateral position → bearing angle
│   └── CameraHeightModel       height variation → ground projection
├── AugmentationGenerator      ← PLACEHOLDER (future)
├── RenderingGenerator         ← PLACEHOLDER (future)
└── MLGenerator                ← PLACEHOLDER (future)
```

**Constitutional rule:** Synthetic data must be clearly labelled. Synthetic samples must never be mixed with real samples without explicit hybrid dataset classification.

**MVP priority:** GeometryGenerator only.

### 4.4 Versioning Subsystem

**Responsibility:** Manage dataset versions and enforce immutability after approval.

**Version naming convention:**
```
{dataset_family}_{type}_v{n}
```

**Examples:**
```
fiducials_aruco_v1
fiducials_aruco_v2
perspective_hallway_v1
hazard_ground_v1
```

**Lifecycle states:**

```
raw → validated → candidate → approved (immutable)
                            ↓
                         rejected → back to raw
```

**Immutability guarantee:** Approved datasets are written to `datasets/approved/` with hash verification. Any modification attempt raises an integrity error.

### 4.5 Coverage Analysis Subsystem

**Responsibility:** Identify gaps in dataset coverage and recommend additional collection or synthetic extension.

**Analysis dimensions for fiducial datasets:**
- Distance coverage (e.g., 0.5 m – 5.0 m range, 0.5 m increments).
- Orientation coverage (Flat, Angled, Tilted, Overhead, Down).
- Camera height coverage.
- Device coverage (which device aliases have been tested).
- Marker type coverage.
- Lighting condition coverage (future).

**Output:** Coverage matrix + gap recommendations + synthetic extension suggestions.

### 4.6 Reporting Subsystem

**Responsibility:** Generate human-readable reports for review and approval.

**Report types:**
- Validation Report: per-dataset quality summary.
- Coverage Report: gap analysis per dataset family.
- Comparison Report: synthetic vs. real distribution comparison.
- Approval Report: human sign-off record.
- Release Notes: per-version summary for downstream consumers.

### 4.7 Export Subsystem

**Responsibility:** Package approved datasets for consumption by downstream Auriga repositories.

**Export formats:**
- Canonical JSON bundle (metadata + image manifest).
- CSV export for analysis notebooks.
- Colab-compatible zip bundles.

**Constitutional constraint:** Only approved datasets may be exported to downstream repositories.

---

## 5. Data Flow Model

```
EXTERNAL SOURCES
(CSV files, images, legacy exports)
         │
         ▼
┌─────────────────┐
│   INGESTION     │  Normalize → Canonical Schema
│   SUBSYSTEM     │  Stage to datasets/raw/
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   VALIDATION    │  Schema → Completeness → Integrity
│   SUBSYSTEM     │  Duplicates → Consistency → Outliers
└────────┬────────┘
         │
         ├──── FAIL ──→ Validation Report (blocking issues)
         │              Back to raw / rejected
         │
         ▼ PASS
┌─────────────────┐
│   COVERAGE      │  Gap analysis
│   SUBSYSTEM     │  Recommendation generation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   REPORTING     │  Full validation report generated
│   SUBSYSTEM     │  Ready for human review
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│   HUMAN REVIEW + APPROVAL       │  Project lead reviews report
│   (HUMAN_DATA_APPROVAL_GUIDE)   │  Approves / rejects / requests changes
└────────┬────────────────────────┘
         │
         ├──── REJECT ──→ Back to raw
         │
         ▼ APPROVE
┌─────────────────┐
│   VERSIONING    │  Assign version identifier
│   SUBSYSTEM     │  Write to datasets/approved/ (immutable)
│                 │  Register in dataset_registry.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   EXPORT        │  Package for downstream consumers
│   SUBSYSTEM     │  Publish to requesting repositories
└─────────────────┘

PARALLEL TRACK:
┌─────────────────┐
│   SYNTHETIC     │  Coverage gaps identified
│   GENERATION   │  → GeometryGenerator produces synthetic extensions
│   SUBSYSTEM     │  → Synthetic datasets follow same validation flow
└─────────────────┘
```

---

## 6. Canonical Metadata Schema

The Auriga Canonical Schema is the single unified representation for all dataset records.

**Version:** 1.0
**Defined in:** `schemas/canonical_metadata_schema_v1.json`

### 6.1 Required Fields

| Field | Type | Description |
|---|---|---|
| `recordId` | string (UUID) | Unique record identifier |
| `datasetVersion` | string | e.g., `fiducials_aruco_v1` |
| `sourceType` | enum | `real`, `synthetic`, `hybrid` |
| `captureTimestamp` | string (ISO 8601) | When the sample was captured/generated |
| `filename` | string | Image filename |
| `imagePath` | string | Relative path to image file |
| `fiducialType` | enum | `aruco`, `apriltag`, `qr`, `custom`, `none` |
| `distanceMeters` | float | Distance from camera to fiducial (meters) |
| `orientation` | enum | `flat`, `angled`, `tilted`, `overhead`, `down`, `unknown` |
| `cameraHeightCm` | float | Camera height above ground (centimeters) |
| `deviceModel` | string | e.g., `Samsung Galaxy A05s` |
| `deviceAlias` | string | e.g., `Device-A` |
| `detectionSuccess` | boolean | Whether detection succeeded |

### 6.2 Optional Fields

| Field | Type | Description |
|---|---|---|
| `markerWidthPx` | integer | Detected marker width in pixels |
| `markerHeightPx` | integer | Detected marker height in pixels |
| `markerAreaPx` | integer | Detected marker area in pixels |
| `centerX` | float | Marker center X coordinate |
| `centerY` | float | Marker center Y coordinate |
| `markerPhysicalSizeMm` | float | Physical marker size in millimeters |
| `bearingDegrees` | float | Estimated bearing to marker |
| `pitchDegrees` | float | Camera pitch at time of capture |
| `yawDegrees` | float | Camera yaw at time of capture |
| `lightingCondition` | enum | `indoor_artificial`, `indoor_natural`, `outdoor`, `unknown` |
| `environmentType` | enum | `hallway`, `room`, `outdoor`, `lab`, `unknown` |
| `syntheticParameters` | object | Generation parameters (synthetic only) |
| `notes` | string | Freeform observations |

### 6.3 Privacy Constraints on Schema

**Prohibited fields (never add):**
- Device serial numbers, IMEI, Android ID, MAC address.
- Collector names, email addresses, personal identifiers.
- Precise GPS coordinates.
- Any field that uniquely identifies a physical person.

---

## 7. Dataset Families and Priority Tiers

### Tier 1 — Immediate MVP (implement now)

| Family | Description |
|---|---|
| `fiducials_aruco` | ArUco marker calibration images and measurements |
| `perspective_validation` | Hallway/indoor perspective and vanishing point imagery |

### Tier 2 — Post-geometric integration

| Family | Description |
|---|---|
| `hazard_ground` | Ground obstacle detection datasets |
| `hazard_suspended` | Suspended obstacle datasets |
| `hazard_stairs` | Staircase and elevation datasets |

### Tier 3 — Navigation intelligence

| Family | Description |
|---|---|
| `place_memory` | Environment fingerprints and visual anchors |
| `navigation_logs` | Timestamped navigation trial records |

---

## 8. Downstream Consumer Interface

Future Auriga repositories may request datasets from the Data Factory via a documented interface.

### 8.1 Request Contract

A downstream repository requesting a dataset must specify:

```json
{
  "requestingRepository": "auriga-core",
  "datasetFamily": "fiducials_aruco",
  "minimumVersion": "v1",
  "requiredFields": ["distanceMeters", "markerWidthPx", "detectionSuccess"],
  "sourceTypes": ["real", "hybrid"],
  "requestDate": "2026-06-16"
}
```

### 8.2 Response Contract

The Data Factory responds with:
```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "status": "approved",
  "recordCount": 128,
  "exportPath": "exports/fiducials_aruco_v2.zip",
  "checksum": "sha256:...",
  "approvalDate": "2026-06-16",
  "approver": "Project Lead",
  "releaseNotes": "See reports/fiducials_aruco_v2_report.md"
}
```

### 8.3 Constitutional Rule on Distribution

Only datasets with `status: approved` may be distributed to downstream consumers. Validated-but-not-approved datasets must never be exported as production inputs.

---

## 9. Execution Environments

The Data Factory must run in all of the following without modification:

| Environment | Priority | Notes |
|---|---|---|
| Replit | Primary MVP development | Current working environment |
| Google Colab | Secondary | Notebook-based analysis and generation |
| Local Python | Future | After local Python installation |
| GitHub Actions | Future | Automated validation CI |

**Constitutional constraint:** The Data Factory must never acquire a mandatory dependency on Replit-specific infrastructure.

---

## 10. Constitutional Rules Summary

The following rules are embedded throughout all Data Factory documents. Violation of any rule requires formal constitutional review.

### Privacy Rules
- P-1: Never upload user environmental imagery to cloud services by default.
- P-2: Never store device serial numbers, IMEI, Android ID, or hardware fingerprints.
- P-3: Never store personally identifying information of data collectors or subjects.
- P-4: Place memories remain on-device by default.

### Data Integrity Rules
- D-1: Approved datasets are immutable.
- D-2: Corrections create new versions; prior versions are never overwritten.
- D-3: Provenance metadata must never be removed.
- D-4: Known data limitations must be documented, not hidden.
- D-5: Synthetic samples must never be unlabelled or mixed with real samples without explicit hybrid classification.

### Validation Rules
- V-1: No dataset may be approved without passing automated validation.
- V-2: No dataset may be approved without human review.
- V-3: Validation failures may not be reclassified as successes without documented justification.
- V-4: Validation logs must be archived; they may not be silently discarded.

### Research Integrity Rules
- R-1: Hypotheses must never be reported as established facts.
- R-2: Validated findings, working assumptions, exploratory ideas, and unresolved questions must be distinguished.
- R-3: Every phase must include both automated and human validation.
- R-4: Research debt must be documented explicitly and tracked.

### Safety Rules
- S-1: Auriga augments, never replaces, professional mobility aids or O&M training.
- S-2: Certainty must never be communicated when only probabilistic estimates exist.
- S-3: Uncertainty must never be suppressed in degraded-perception environments.

### AI Agent Rules
- A-1: AI-generated outputs do not bypass human oversight for constitutional decisions.
- A-2: AI agents may propose but not redefine constitutional rules.
- A-3: Self-correction must be attempted before escalation to human reviewers.
- A-4: Human reviewers retain final authority over safety, dataset, and constitutional approvals.

---

## 11. Research Debt — Open Questions

The following questions remain unresolved and are tracked as research debt. They must not be treated as answered until evidence-based resolution has been documented.

| ID | Question | Impact |
|---|---|---|
| RD-001 | What minimum sample count per condition is sufficient for statistical validity? | Validation thresholds |
| RD-002 | How should outlier thresholds be calibrated for geometric measurements? | Outlier detection rules |
| RD-003 | What statistical tests are appropriate for synthetic vs. real distribution comparison? | Comparison methodology |
| RD-004 | Should hybrid datasets receive separate validation treatment from pure real datasets? | Hybrid classification |
| RD-005 | How should coverage gaps be scored for severity? | Coverage analysis priority |

---

## 12. Adversarial Review Notes

*To be completed after human review of this document.*

---

## 13. Human Approval Record

| Field | Value |
|---|---|
| Document | DATA_FACTORY_ARCHITECTURE.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |

> **This document is not finalized until the project lead has reviewed and approved it.**
