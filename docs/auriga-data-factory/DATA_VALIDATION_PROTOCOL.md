# DATA_VALIDATION_PROTOCOL.md
# Auriga Data Factory — Data Validation Protocol

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This document defines the complete validation protocol applied to all datasets entering the Auriga Data Factory. It specifies every automated check, its logic, its severity level, and how results are communicated to the human reviewer.

Validation is the quality gate between raw ingested data and human review. No dataset may receive human approval consideration without first passing this protocol.

### Constitutional Rules Governing This Document

- **V-1:** No dataset may be approved without passing automated validation.
- **V-2:** No dataset may be approved without human review.
- **V-3:** Validation failures may not be reclassified as successes without documented justification.
- **V-4:** Validation logs must be archived; they may not be silently discarded.
- **R-2:** Validated findings, working assumptions, and unresolved questions must be clearly distinguished in reports.

---

## 2. Validation Architecture

Validation is organized into seven ordered layers. Layers 1–5 are **blocking** — a failure in any blocking layer halts the pipeline and prevents progression to `validated` status. Layers 6–7 are **advisory** — they produce flagged findings for human review but do not block promotion.

```
Layer 1: Schema Validation       ← BLOCKING
Layer 2: Completeness Check      ← BLOCKING
Layer 3: File Integrity Check    ← BLOCKING
Layer 4: Duplicate Detection     ← BLOCKING
Layer 5: Consistency Check       ← BLOCKING
Layer 6: Outlier Detection       ← ADVISORY (flag only)
Layer 7: Coverage Analysis       ← ADVISORY (flag only)
```

Layers are executed in order. If a blocking layer fails, subsequent layers are still executed and their results are included in the report, but the overall result is FAIL.

---

## 3. Layer 1 — Schema Validation

**Purpose:** Verify that every record conforms to the Auriga Canonical Schema.

**Severity:** BLOCKING

### 3.1 Checks Performed

| Check | Description | Error if |
|---|---|---|
| Required field presence | All required fields exist in every record | Any required field is absent |
| Type conformance | Each field contains the correct data type | Field type does not match schema |
| Enum conformance | Enum fields contain only permitted values | Value not in permitted set |
| UUID format | `recordId` is a valid UUID v4 | Invalid UUID format |
| Timestamp format | `captureTimestamp` is valid ISO 8601 | Invalid or unparseable timestamp |
| Version string format | `datasetVersion` matches `{family}_{subtype}_v{n}` | Malformed version string |
| Prohibited field detection | No prohibited field names present | Any prohibited field found |

### 3.2 Error Reporting

Each schema violation produces a structured error entry:

```json
{
  "layer": "schema",
  "severity": "blocking",
  "recordId": "uuid-or-row-index",
  "field": "distanceMeters",
  "issue": "MISSING_REQUIRED_FIELD",
  "detail": "Field 'distanceMeters' is required but absent in record at row 14.",
  "recommendation": "Add distanceMeters value. Check collection log for this sample."
}
```

### 3.3 Pass Condition

Layer 1 passes when zero blocking violations are found across all records.

---

## 4. Layer 2 — Completeness Check

**Purpose:** Detect missing values in required fields that passed type checks but are empty, null, or whitespace-only.

**Severity:** BLOCKING

### 4.1 Checks Performed

| Check | Description | Error if |
|---|---|---|
| Null required fields | Required fields are not null | Required field is null |
| Empty string fields | String fields are not empty | Required string is empty |
| Zero-value check | Numeric fields that must be positive are not zero | `distanceMeters` = 0, `cameraHeightCm` = 0 |
| Negative value check | Numeric fields that must be positive are not negative | Any positive-constrained field is < 0 |

### 4.2 Context-Dependent Completeness

Some optional fields become required based on other field values:

| Condition | Field becomes required |
|---|---|
| `detectionSuccess = true` | `markerWidthPx`, `markerHeightPx`, `centerX`, `centerY` |
| `sourceType = "synthetic"` | `syntheticParameters` |
| `sourceType = "hybrid"` | `syntheticParameters`, `hybridRationale` (dataset-level) |

### 4.3 Pass Condition

Layer 2 passes when no required fields contain null, empty, or logically invalid values.

---

## 5. Layer 3 — File Integrity Check

**Purpose:** Verify that every referenced image file exists and is readable.

**Severity:** BLOCKING

### 5.1 Checks Performed

| Check | Description | Error if |
|---|---|---|
| Image file existence | File at `imagePath` exists on disk | File not found |
| Image readability | File can be opened as an image | File corrupt or unreadable |
| Filename consistency | `filename` matches the filename component of `imagePath` | Mismatch between fields |
| Synthetic null allowance | `imagePath` = null is permitted when `sourceType` = "synthetic" | null imagePath when sourceType ≠ "synthetic" |

### 5.2 Pass Condition

Layer 3 passes when all referenced image files exist and are readable.

---

## 6. Layer 4 — Duplicate Detection

**Purpose:** Identify duplicate records that would introduce bias or overcounting.

**Severity:** BLOCKING

### 6.1 Duplicate Detection Strategies

**Strategy A — Exact recordId duplicates:**
- Two records with identical `recordId` values.
- Always blocking.

**Strategy B — Identical filename duplicates:**
- Two records referencing the same image file.
- Blocking unless files differ by sourceType (real vs. synthetic may share filenames as reference).

**Strategy C — Near-duplicate detection:**
- Records with identical values across: `distanceMeters`, `orientation`, `cameraHeightCm`, `deviceAlias`, `captureTimestamp`.
- Advisory flag. Blocking only if timestamp is identical to within 1 second.

**Strategy D — Content hash duplicates (future):**
- Image content hash comparison.
- Noted as research debt RD-008. Not implemented in MVP.

### 6.2 Duplicate Report Format

```json
{
  "layer": "duplicates",
  "severity": "blocking",
  "duplicateType": "identical_filename",
  "affectedRecords": ["record-uuid-1", "record-uuid-2"],
  "detail": "Both records reference 'aruco_1m_flat_001.jpg'.",
  "recommendation": "Verify whether these are two captures of the same file or an ingestion error. Remove one record."
}
```

### 6.3 Pass Condition

Layer 4 passes when no blocking duplicate types are found.

---

## 7. Layer 5 — Consistency Check

**Purpose:** Verify that field values are internally consistent and logically coherent with each other.

**Severity:** BLOCKING

### 7.1 Cross-Field Consistency Rules

| Rule | Description | Error if |
|---|---|---|
| C-01 | Detection results match pixel data | `detectionSuccess = true` but `markerWidthPx` is null |
| C-02 | Marker dimensions are positive when detected | `detectionSuccess = true` but `markerWidthPx` ≤ 0 |
| C-03 | Marker area consistent with dimensions | `markerAreaPx` significantly deviates from `markerWidthPx` × `markerHeightPx` (>20% difference) |
| C-04 | Center coordinates within image bounds | `centerX` or `centerY` negative, or implausibly large (>10,000 px) |
| C-05 | Distance and pixel size correlation | For real datasets: `distanceMeters` increases while `markerWidthPx` increases (inverse expected) — flag for review |
| C-06 | Dataset version consistency | All records in a single dataset file carry the same `datasetVersion` |
| C-07 | Source type consistency | A dataset declared as `real` contains no records with `sourceType = "synthetic"` |

### 7.2 Advisory Consistency Rules

| Rule | Description |
|---|---|
| C-08 | `captureTimestamp` ordering is chronological within a collection session (flag if out of order) |
| C-09 | `cameraHeightCm` values are within physiologically plausible range (60–200 cm) for handheld device — flag outside range |

### 7.3 Pass Condition

Layer 5 passes when no blocking consistency violations are found.

---

## 8. Layer 6 — Outlier Detection

**Purpose:** Identify statistically unusual values that may indicate measurement errors, equipment issues, or genuinely unusual samples.

**Severity:** ADVISORY (does not block promotion)

### 8.1 Statistical Outlier Methods

**Method: IQR (Interquartile Range) — Primary MVP method**

For each numeric field with sufficient samples (≥ 10 records):
```
Q1 = 25th percentile
Q3 = 75th percentile
IQR = Q3 - Q1
Lower fence = Q1 - 1.5 × IQR
Upper fence = Q3 + 1.5 × IQR
Outlier = any value outside [Lower fence, Upper fence]
```

**Fields analyzed:**
- `distanceMeters`
- `markerWidthPx`
- `markerHeightPx`
- `markerAreaPx`
- `cameraHeightCm`
- `bearingDegrees` (if present)

### 8.2 Domain-Specific Hard Limits

Regardless of statistical distribution, values outside these absolute bounds are flagged:

| Field | Minimum | Maximum | Rationale |
|---|---|---|---|
| `distanceMeters` | 0.1 | 20.0 | Beyond 20m, ArUco detection unreliable |
| `cameraHeightCm` | 10 | 250 | Physical plausibility |
| `markerWidthPx` | 1 | 4000 | Sensor resolution bounds |
| `markerHeightPx` | 1 | 4000 | Sensor resolution bounds |

### 8.3 Outlier Report Format

```json
{
  "layer": "outliers",
  "severity": "advisory",
  "recordId": "uuid",
  "field": "markerWidthPx",
  "value": 4850,
  "boundType": "hard_limit",
  "bound": 4000,
  "detail": "markerWidthPx value of 4850 exceeds absolute maximum of 4000px.",
  "recommendation": "Review image at images/sample.jpg. Likely a detection artifact or image resolution anomaly."
}
```

### 8.4 Research Debt

RD-002 — Outlier thresholds for geometric measurements have not been empirically validated. Current bounds are design estimates based on physical reasoning. Calibration against real Auriga datasets is required.

---

## 9. Layer 7 — Coverage Analysis

**Purpose:** Identify systematic gaps in the dataset's coverage of the experimental space.

**Severity:** ADVISORY (does not block promotion — but gaps must be acknowledged in approval decision)

Coverage analysis is fully defined in COVERAGE_ANALYSIS_GUIDE.md. The validation protocol invokes coverage analysis and includes its output in the validation report.

**Coverage dimensions analyzed (for fiducial datasets):**
- Distance range coverage.
- Orientation type coverage.
- Camera height variation.
- Device coverage.
- Detection outcome balance (successes vs. failures).

**Output:** Coverage matrix table + gap list + synthetic extension recommendations.

---

## 10. Validation Report Structure

Every validation run produces a structured report. The report is the input for human review.

### 10.1 Report File Naming

```
reports/{dataset_version}_validation_report.md
reports/{dataset_version}_validation_report.json
```

Both formats are generated simultaneously.

### 10.2 Markdown Report Template

```markdown
# Validation Report: {dataset_version}

**Generated:** {timestamp}
**Schema version:** canonical_v1
**Record count:** {n}
**Overall result:** PASS | FAIL

---

## Summary

| Layer | Status | Issues Found |
|---|---|---|
| 1. Schema | PASS/FAIL | {count} |
| 2. Completeness | PASS/FAIL | {count} |
| 3. File Integrity | PASS/FAIL | {count} |
| 4. Duplicates | PASS/FAIL | {count} |
| 5. Consistency | PASS/FAIL | {count} |
| 6. Outliers | ADVISORY | {count} |
| 7. Coverage | ADVISORY | {gap_count} gaps |

---

## Blocking Issues

{List each blocking issue with recordId, field, issue type, and recommendation}

## Advisory Findings

### Outliers
{List each outlier finding}

### Coverage Gaps
{Coverage matrix and gap summary}

---

## Recommendations

{Automated recommendations for addressing gaps, outliers, and missing data}

---

## Human Review Required

The following items require explicit human judgment before approval:

1. {item}
2. {item}

---

## Validation Log

Full validation log archived at: logs/{dataset_version}_{timestamp}.log
```

### 10.3 JSON Report Schema

```json
{
  "datasetVersion": "fiducials_aruco_v2",
  "generatedAt": "2026-06-16T14:30:00Z",
  "schemaVersion": "canonical_v1",
  "recordCount": 96,
  "overallResult": "PASS",
  "layerResults": {
    "schema": {"status": "PASS", "issueCount": 0, "issues": []},
    "completeness": {"status": "PASS", "issueCount": 0, "issues": []},
    "fileIntegrity": {"status": "PASS", "issueCount": 0, "issues": []},
    "duplicates": {"status": "PASS", "issueCount": 0, "issues": []},
    "consistency": {"status": "PASS", "issueCount": 0, "issues": []},
    "outliers": {"status": "ADVISORY", "issueCount": 2, "issues": [...]},
    "coverage": {"status": "ADVISORY", "gapCount": 3, "gaps": [...]}
  },
  "recommendations": [],
  "humanReviewItems": []
}
```

---

## 11. Running the Validator

### 11.1 Python Interface (reference)

```python
from factory.validation.validator import Validator

validator = Validator(schema_version="canonical_v1")
result = validator.validate(
    dataset_path="datasets/staged/fiducials_aruco_candidate/",
    dataset_version="fiducials_aruco_v2"
)

print(result.overall_status)   # "PASS" or "FAIL"
result.save_report("reports/")
```

### 11.2 Expected Execution Environments

| Environment | Method |
|---|---|
| Replit | Python script via shell |
| Google Colab | Notebook cell |
| GitHub Actions (future) | CI workflow step |
| Local Python (future) | CLI command |

---

## 12. Validation Failure Response Procedures

| Failure Type | Response |
|---|---|
| Schema errors | Fix source data, re-ingest, re-validate |
| Missing images | Locate and add missing files, or remove records with no recoverable image |
| Duplicates | Investigate source, remove confirmed duplicates, document cause |
| Consistency errors | Review flagged records, correct values or add explanatory notes |
| Outliers (advisory) | Review each flagged record; document decision in approval notes |
| Coverage gaps (advisory) | Plan additional collection or synthetic extension |

---

## 13. Research Debt

| ID | Question |
|---|---|
| RD-002 | Outlier thresholds for geometric fields need empirical calibration |
| RD-003 | Appropriate statistical tests for synthetic vs. real distribution comparison |
| RD-008 | Image content hash duplicate detection (not implemented in MVP) |
| RD-009 | What consistency tolerance should apply to C-03 (marker area vs. dimension product)? |

---

## 14. Human Approval Record

| Field | Value |
|---|---|
| Document | DATA_VALIDATION_PROTOCOL.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
