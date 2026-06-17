# COVERAGE_ANALYSIS_GUIDE.md
# Auriga Data Factory — Coverage Analysis Guide

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This guide defines how the Auriga Data Factory analyzes dataset coverage, identifies gaps, quantifies completeness, and generates actionable recommendations for additional data collection or synthetic extension.

Coverage analysis is not a pass/fail gate — it is an advisory system. A dataset may be approved with known coverage gaps provided those gaps are explicitly acknowledged in the approval record. However, coverage gaps directly inform the Data Factory's automatic recommendations and synthetic generation priorities.

---

## 2. What Coverage Analysis Does

The coverage analyzer answers five questions for every dataset:

1. **Presence:** Which conditions have at least one sample?
2. **Density:** Which conditions have sufficient samples for statistical confidence?
3. **Gaps:** Which conditions have zero samples?
4. **Outlier-dominance:** Are any cells represented only by samples flagged as outliers?
5. **Recommendations:** What additional collection or synthetic extension is advised?

---

## 3. Coverage Dimensions

Coverage is analyzed across multiple dimensions simultaneously. The specific dimensions depend on the dataset family.

### 3.1 Fiducial Dataset Coverage Dimensions

#### Dimension 1: Distance

| Range | Increment | Coverage Target |
|---|---|---|
| 0.5 m – 5.0 m | 0.5 m steps | 10 distance values |

Each 0.5 m step is a coverage cell. A cell is considered:
- **Covered:** ≥ 1 sample exists.
- **Adequately covered:** ≥ N samples (N = Research Debt RD-001).
- **Uncovered:** 0 samples.

**MVP minimum coverage:** At least 5 distinct distance values.

#### Dimension 2: Orientation

| Value | Description |
|---|---|
| `flat` | Camera level, marker perpendicular |
| `angled` | Horizontal angle to marker |
| `tilted` | Camera pitched |
| `overhead` | Camera angled upward |
| `down` | Camera angled downward at ground marker |

**MVP minimum coverage:** At least 2 orientation types.

#### Dimension 3: Camera Height

| Category | Range |
|---|---|
| Low | 60–100 cm |
| Standard | 100–140 cm |
| High | 140–180 cm |

**MVP minimum coverage:** At least 1 height category represented.

#### Dimension 4: Device Coverage

| Category | Description |
|---|---|
| Per device alias | Each distinct deviceAlias is a coverage axis |

A dataset collected on a single device has device coverage = 1. For cross-device generalization studies, multiple devices are required.

**MVP minimum coverage:** At least 1 device.

#### Dimension 5: Detection Outcome Balance

| Category | Description |
|---|---|
| Success (`detectionSuccess = true`) | At least some successful detections |
| Failure (`detectionSuccess = false`) | At least some failed detections |

A dataset with 100% detection success may not adequately characterize edge cases. A dataset with 100% failure is likely a collection error.

**Advisable:** Both outcomes present.

### 3.2 Perspective Validation Coverage Dimensions

| Dimension | Values |
|---|---|
| Environment type | hallway, room |
| Viewpoint | centered, left-offset, right-offset |
| Camera height | low, standard, high |
| Lighting | indoor_artificial, indoor_natural |

### 3.3 Future Dataset Families

Coverage dimensions for Tier 2 and Tier 3 datasets will be defined when those families reach active development.

---

## 4. Coverage Matrix

Coverage is represented as a matrix where:
- **Rows** represent one dimension (e.g., distance).
- **Columns** represent another dimension (e.g., orientation).
- **Cells** contain the sample count for that combination.

### 4.1 Example Coverage Matrix (Fiducial Distance × Orientation)

```
Distance (m) | flat | angled | tilted | down | overhead | TOTAL
-------------|------|--------|--------|------|----------|------
0.5          |   8  |   4    |   2    |   3  |    0     |  17
1.0          |  10  |   5    |   3    |   4  |    0     |  22
1.5          |   9  |   4    |   2    |   3  |    0     |  18
2.0          |   8  |   3    |   1    |   2  |    0     |  14
2.5          |   7  |   3    |   0    |   2  |    0     |  12
3.0          |   6  |   2    |   0    |   1  |    0     |   9
3.5          |   4  |   1    |   0    |   0  |    0     |   5
4.0          |   3  |   0    |   0    |   0  |    0     |   3
4.5          |   0  |   0    |   0    |   0  |    0     |   0  ← GAP
5.0          |   0  |   0    |   0    |   0  |    0     |   0  ← GAP
-------------|------|--------|--------|------|----------|------
TOTAL        |  55  |  22    |   8    |  15  |    0     | 100
```

**Gap cells:** `orientation = overhead` (all distances), `distance = 4.5m`, `distance = 5.0m`.

**Gap severity:** Distance gaps at 4.5m and 5.0m are high-priority for the Virtual Fiducial distance range. Overhead gap is lower priority for MVP (ground-plane navigation is primary focus).

### 4.2 Coverage Status Symbols

| Symbol | Meaning |
|---|---|
| ✓ | Adequately covered (≥ target N) |
| ~ | Minimally covered (1 to N-1 samples) |
| ✗ | Uncovered (0 samples) |
| ⚠ | Covered only by outlier-flagged samples |

---

## 5. Gap Classification

Identified gaps are classified by severity to help prioritize collection effort.

### 5.1 Severity Levels

| Level | Definition | Action |
|---|---|---|
| **Critical** | Gap affects the primary hypothesis being tested | Must be addressed before downstream use |
| **High** | Gap affects a dimension required for validation | Should be addressed before v-final release |
| **Medium** | Gap reduces statistical confidence but doesn't invalidate results | Note in limitations; plan for next version |
| **Low** | Gap affects a dimension not yet in scope | Document; defer to future version |

### 5.2 Gap Severity Assignment (Fiducial Datasets)

| Gap Type | Default Severity | Rationale |
|---|---|---|
| Missing distance values in 0.5–3.0 m range | Critical | Core Virtual Fiducial operating range |
| Missing distance values in 3.0–5.0 m range | High | Extended operating range |
| Missing orientations (flat, down) | High | Primary orientation types for ground navigation |
| Missing orientations (angled, tilted) | Medium | Secondary types |
| Missing orientations (overhead) | Low | Suspended hazards are Tier 2 |
| Single device only | Medium | Cross-device generalization is important but not MVP blocker |
| No detection failures | Medium | Edge case characterization |
| No detection successes | Critical | Dataset is likely corrupted |

---

## 6. Automatic Recommendations

For each identified gap, the coverage analyzer generates a recommendation. Recommendations fall into two categories:

### 6.1 Real Data Collection Recommendations

Format:
```
RECOMMENDATION [RC-001]
Type: Real Data Collection
Priority: High
Gap: No samples at distanceMeters = 4.5m, orientation = flat
Action: Collect at least 5 samples at 4.5m flat orientation using Device-A.
Protocol: Follow DATA_INGESTION_GUIDE.md Section 4.
```

### 6.2 Synthetic Extension Recommendations

Format:
```
RECOMMENDATION [RS-001]
Type: Synthetic Extension
Priority: High
Gap: No samples at distanceMeters = 4.5m, all orientations
Rationale: Physical collection at 4.5m is feasible but has not yet occurred.
           Synthetic extension using GeometryGenerator is advisable to support
           interim validation while real data is collected.
Action: Run GeometryGenerator with target distances [4.5, 5.0],
        orientations [flat, down], using calibrated focal_length_px
        from fiducials_aruco_v2.
Expected output: 10–20 synthetic records.
Validation: Compare distribution against fiducials_aruco_v2.
```

### 6.3 Recommendation Priority Queue

The coverage analyzer produces a prioritized list of recommendations, ordered by:
1. Gap severity (Critical first).
2. Collection feasibility (easier collections first within same severity).
3. Research impact (hypotheses under active testing first).

---

## 7. Coverage Score

The coverage analyzer computes a Coverage Score for each analyzed dimension and an Overall Coverage Score for the dataset.

### 7.1 Per-Dimension Coverage Score

```
dimension_score = (covered_cells / total_cells) × 100
```

Where `covered_cells` = cells with ≥ 1 sample.

### 7.2 Weighted Overall Coverage Score

```
overall_score = Σ (dimension_score × dimension_weight)
```

**Dimension weights (fiducial datasets — MVP):**

| Dimension | Weight |
|---|---|
| Distance | 0.50 |
| Orientation | 0.25 |
| Camera height | 0.15 |
| Device | 0.10 |

**Interpretation:**

| Score | Interpretation |
|---|---|
| 90–100% | Excellent coverage |
| 70–89% | Good coverage — minor gaps noted |
| 50–69% | Partial coverage — significant gaps |
| < 50% | Insufficient coverage — not recommended for approval without synthetic extension |

**Constitutional note:** The coverage score is advisory. A dataset with a score below 50% may still be approved if the human reviewer provides explicit documented justification. The score does not automatically block approval.

### 7.3 Research Debt

RD-005 — Coverage gap severity scoring methodology and dimension weights are design estimates. They require empirical calibration as Auriga datasets mature.

---

## 8. Coverage Report Format

```markdown
# Coverage Analysis Report: {dataset_version}

**Generated:** {timestamp}
**Dataset family:** {family}
**Record count:** {n}
**Overall Coverage Score:** {score}%

---

## Coverage Matrices

### Distance × Orientation

{matrix table}

### Distance × Camera Height

{matrix table}

---

## Gap Summary

| Gap ID | Dimension | Missing Value | Severity | Recommendation |
|---|---|---|---|---|
| G-001 | distance | 4.5m | High | RC-001, RS-001 |
| G-002 | orientation | overhead | Low | Defer to Tier 2 |

---

## Recommendations

### Real Data Collection

{RC-001 through RC-N}

### Synthetic Extension

{RS-001 through RS-N}

---

## Coverage Score Breakdown

| Dimension | Score | Weight | Weighted Score |
|---|---|---|---|
| Distance | 80% | 0.50 | 40.0% |
| Orientation | 60% | 0.25 | 15.0% |
| Camera height | 100% | 0.15 | 15.0% |
| Device | 100% | 0.10 | 10.0% |
| **Overall** | | | **80.0%** |
```

---

## 9. Python Reference Structure

```python
# factory/coverage/coverage_analyzer.py
from typing import Dict, List

class CoverageAnalyzer:
    """
    Analyzes a validated dataset for coverage gaps and generates recommendations.
    """

    def __init__(self, dataset_family: str):
        self.dataset_family = dataset_family
        self.dimension_config = self._load_dimension_config(dataset_family)

    def analyze(self, records: List[Dict]) -> dict:
        """
        Returns a coverage analysis result containing:
        - coverage_matrices: dict of matrices by dimension pair
        - gaps: list of identified gaps with severity
        - recommendations: prioritized list of collection/generation actions
        - coverage_score: overall weighted coverage score
        """
        matrices = self._build_coverage_matrices(records)
        gaps = self._identify_gaps(matrices)
        recommendations = self._generate_recommendations(gaps)
        score = self._compute_coverage_score(matrices)

        return {
            "datasetVersion": records[0]["datasetVersion"] if records else "unknown",
            "recordCount": len(records),
            "coverageMatrices": matrices,
            "gaps": gaps,
            "recommendations": recommendations,
            "coverageScore": score
        }
```

---

## 10. Research Debt

| ID | Question |
|---|---|
| RD-001 | Minimum sample count N per condition for statistical validity |
| RD-005 | Coverage gap severity scoring and dimension weighting need empirical calibration |
| RD-014 | Should the coverage score incorporate detection success rate as a separate dimension? |

---

## 11. Human Approval Record

| Field | Value |
|---|---|
| Document | COVERAGE_ANALYSIS_GUIDE.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
