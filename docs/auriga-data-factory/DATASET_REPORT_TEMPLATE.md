# DATASET_REPORT_TEMPLATE.md
# Auriga Data Factory — Dataset Report Template

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This document provides the canonical template for all Auriga dataset reports. A dataset report is generated at the conclusion of the validation and coverage analysis pipeline. It is the primary input for the human reviewer's approval decision.

Every approved dataset must have a corresponding completed report archived in `reports/`.

---

## 2. How to Use This Template

1. Copy this template to `reports/{dataset_version}_report.md`.
2. Replace all `{placeholder}` values with actual dataset-specific content.
3. Do not delete any section. If a section is not applicable, write "N/A — [reason]".
4. The report is considered complete when all `{placeholder}` values have been replaced.
5. The completed report must be reviewed by the project lead before approval is granted.

---

---

# DATASET REPORT
# {dataset_version}

**Report generated:** {YYYY-MM-DD HH:MM:SS UTC}
**Report version:** 1.0
**Schema version:** canonical_v1
**Report status:** DRAFT | READY FOR REVIEW | APPROVED | REJECTED

---

## Section 1 — Dataset Identity

| Field | Value |
|---|---|
| Dataset version | `{dataset_version}` |
| Dataset family | `{family}` |
| Dataset subtype | `{subtype}` |
| Source type | `real` / `synthetic` / `hybrid` |
| Record count | `{n}` |
| Image count | `{n}` |
| Creation date | `{YYYY-MM-DD}` |
| Collector / Generator | `{name or system}` |
| Collection environment | `{hallway / room / outdoor / lab / generated}` |
| Supersedes | `{previous version or "none"}` |
| Superseded by | `{newer version or "none"}` |

---

## Section 2 — Collection Summary

*(For real and hybrid datasets. For synthetic-only, write "N/A — synthetically generated.")*

### 2.1 Collection Conditions

| Condition | Details |
|---|---|
| Date(s) of collection | `{date range}` |
| Location description | `{general indoor/outdoor description — no precise GPS}` |
| Lighting conditions | `{indoor_artificial / indoor_natural / mixed}` |
| Environment type | `{hallway / room / outdoor / lab}` |
| Physical marker used | `{fiducial type, size in mm}` |
| Measurement instrument | `{e.g., measuring tape, laser measure}` |
| Measurement precision | `{e.g., ±0.05 m}` |
| Device(s) used | `{device model(s) and alias(es)}` |

### 2.2 Collection Protocol Followed

| Protocol Document | Version | Followed? |
|---|---|---|
| DATA_INGESTION_GUIDE.md | `{version}` | Yes / No / Partially |

**Deviations from protocol:** *(List any deviations, or "None")*

---

## Section 3 — Validation Results

### 3.1 Overall Validation Status

**RESULT: PASS / FAIL**

### 3.2 Layer-by-Layer Results

| Layer | Status | Issues Found |
|---|---|---|
| 1. Schema Validation | PASS / FAIL | `{n}` |
| 2. Completeness Check | PASS / FAIL | `{n}` |
| 3. File Integrity | PASS / FAIL | `{n}` |
| 4. Duplicate Detection | PASS / FAIL | `{n}` |
| 5. Consistency Check | PASS / FAIL | `{n}` |
| 6. Outlier Detection | ADVISORY | `{n}` flagged |
| 7. Coverage Analysis | ADVISORY | `{n}` gaps identified |

### 3.3 Blocking Issues Found

*(List all blocking issues. If none: "None — all blocking checks passed.")*

| Issue ID | Layer | Record ID | Field | Description | Resolution |
|---|---|---|---|---|---|
| `{ID}` | `{layer}` | `{uuid}` | `{field}` | `{description}` | `{how it was resolved}` |

### 3.4 Advisory Findings — Outliers

*(List all outlier-flagged records. If none: "None.")*

| Record ID | Field | Value | Bound | Human Assessment |
|---|---|---|---|---|
| `{uuid}` | `{field}` | `{value}` | `{bound}` | `{keep / investigate / remove}` |

### 3.5 Full Validation Report Reference

Full JSON validation report: `reports/{dataset_version}_validation_report.json`

---

## Section 4 — Coverage Analysis

### 4.1 Overall Coverage Score

**Coverage Score: {score}%** *(Good / Partial / Insufficient)*

### 4.2 Coverage Matrix — Distance × Orientation

*(Paste generated coverage matrix here)*

```
Distance (m) | flat | angled | tilted | down | overhead | TOTAL
-------------|------|--------|--------|------|----------|------
{values}
```

Symbol key: ✓ = adequate | ~ = minimal | ✗ = uncovered | ⚠ = outlier-only

### 4.3 Identified Coverage Gaps

| Gap ID | Dimension | Missing Value | Severity | Status |
|---|---|---|---|---|
| `{G-001}` | `{dimension}` | `{value}` | Critical / High / Medium / Low | Open / Deferred / Addressed |

### 4.4 Coverage Recommendations

*(From automated recommendation engine)*

**Real Data Collection:**

```
{RC-001 text}
{RC-002 text}
```

**Synthetic Extension:**

```
{RS-001 text}
{RS-002 text}
```

---

## Section 5 — Statistical Summary

*(For datasets with ≥ 10 records. For smaller datasets, note "Insufficient records for statistical summary.")*

### 5.1 Numeric Field Statistics

| Field | Count | Mean | Std Dev | Min | Q1 | Median | Q3 | Max |
|---|---|---|---|---|---|---|---|---|
| distanceMeters | `{n}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` |
| markerWidthPx | `{n}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` |
| markerHeightPx | `{n}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` |
| cameraHeightCm | `{n}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` | `{val}` |

### 5.2 Categorical Field Distributions

| Field | Value | Count | % |
|---|---|---|---|
| orientation | flat | `{n}` | `{%}` |
| orientation | angled | `{n}` | `{%}` |
| orientation | down | `{n}` | `{%}` |
| detectionSuccess | true | `{n}` | `{%}` |
| detectionSuccess | false | `{n}` | `{%}` |
| deviceAlias | Device-A | `{n}` | `{%}` |

### 5.3 Distance-Pixel Size Correlation

*(For fiducial datasets with ≥ 10 records with detectionSuccess = true)*

| Metric | Value |
|---|---|
| Pearson correlation (distance vs. markerWidthPx) | `{r}` |
| Direction | `{negative = expected / positive = anomaly}` |
| Interpretation | `{normal inverse relationship / anomaly detected}` |

---

## Section 6 — Synthetic vs. Real Comparison

*(Complete this section for synthetic and hybrid datasets only.)*

*(For real datasets: "N/A — this is a real dataset.")*

### 6.1 Base Real Dataset

| Field | Value |
|---|---|
| Real dataset version compared against | `{version}` |
| Comparison date | `{date}` |

### 6.2 Distribution Comparison Summary

| Field | Real Mean | Synthetic Mean | Δ% | Assessment |
|---|---|---|---|---|
| markerWidthPx | `{val}` | `{val}` | `{%}` | Acceptable / Review |
| markerHeightPx | `{val}` | `{val}` | `{%}` | Acceptable / Review |
| distanceMeters | `{val}` | `{val}` | `{%}` | Acceptable / Expected |

### 6.3 Comparison Conclusion

*(Summarise whether synthetic distribution is consistent with real distribution. Document any intentional deviations.)*

---

## Section 7 — Known Limitations

*(Be complete. Known limitations do not prevent approval. Hidden limitations do.)*

| # | Limitation | Impact | Mitigation Plan |
|---|---|---|---|
| 1 | `{description}` | `{impact}` | `{plan or "None — document as research debt"}` |

---

## Section 8 — Research Debt Items

*(List all open research questions surfaced by this dataset's collection or analysis.)*

| ID | Question | Priority |
|---|---|---|
| `{RD-XXX}` | `{question}` | High / Medium / Low |

---

## Section 9 — Integrity

| Field | Value |
|---|---|
| Checksum algorithm | SHA-256 |
| Metadata file checksum | `{sha256:...}` |
| Image directory checksum | `{sha256:...}` |
| Manifest file | `datasets/approved/{dataset_version}/checksum_manifest.json` |

---

## Section 10 — Human Review Decision

### 10.1 Items Requiring Explicit Human Judgment

*(The automated system has identified the following items that require human assessment before approval. Each item must receive a documented response.)*

| # | Item | Human Decision | Notes |
|---|---|---|---|
| 1 | `{item}` | Acceptable / Investigate / Block approval | `{notes}` |

### 10.2 Approval Decision

| Field | Value |
|---|---|
| Reviewer | `{project lead name / alias}` |
| Review date | `{YYYY-MM-DD}` |
| Decision | **APPROVED** / **REJECTED** / **CONDITIONAL APPROVAL** |
| Approval notes | `{freeform notes}` |
| Conditions (if conditional) | `{list conditions}` |
| Known limitations acknowledged | Yes / No |
| Research debt acknowledged | Yes / No |

### 10.3 Approval Signature

> I confirm that I have reviewed this dataset report, assessed the automated validation results, reviewed the advisory findings, and made a considered judgment about this dataset's fitness for its intended purpose. I understand that approving this dataset makes it immutable and that it will be used as a scientific input by downstream Auriga repositories.

**Approved by:** ______________________

**Date:** ______________________

---

## Section 11 — Distribution Record

*(Completed after approval and distribution)*

| Repository | Distribution Date | Purpose | Version Consumed |
|---|---|---|---|
| `{repo}` | `{date}` | `{purpose}` | `{version}` |

---

*End of Dataset Report Template*
