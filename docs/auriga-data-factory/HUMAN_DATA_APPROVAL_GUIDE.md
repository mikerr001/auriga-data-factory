# HUMAN_DATA_APPROVAL_GUIDE.md
# Auriga Data Factory — Human Data Approval Guide

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## 1. Purpose

This guide defines the human approval process for Auriga datasets. It specifies the reviewer's role, the step-by-step approval workflow, the evaluation criteria, the approval decision record format, and the constitutional constraints governing the process.

Human approval is not a formality. It is a scientific checkpoint. Automated validation catches structural and statistical errors, but it cannot assess:

- Whether the collection protocol was followed faithfully.
- Whether measurements were made with sufficient care.
- Whether the environment was appropriate for the claimed conditions.
- Whether unusual circumstances affected the data in ways the collector noted but the validator cannot detect.
- Whether the dataset is fit for its intended downstream purpose.

The human reviewer bridges the gap between automated checks and scientific judgment.

---

## 2. Constitutional Rules Governing Human Approval

- **V-2:** No dataset may be approved without human review.
- **A-1:** AI-generated outputs do not bypass human oversight for constitutional decisions.
- **A-4:** Human reviewers retain final authority over safety, dataset, and constitutional approvals.
- **D-1:** Approved datasets are immutable. The approval decision is permanent.
- **R-4:** Research debt must be documented explicitly. Approval does not erase known limitations.

---

## 3. Roles

### 3.1 Current MVP Configuration

**Project Lead:** The sole approver during the MVP phase. Responsible for all approval decisions.

### 3.2 Future Role Structure

As the project grows, the following role framework is available. All roles may be fulfilled by the Project Lead during solo development.

| Role | Responsibilities |
|---|---|
| **Project Lead** | Final approval authority. Constitutional decisions. |
| **Data Collector** | Executed the collection protocol. Provides session notes. |
| **Data Reviewer** | Reviews validation report and raises concerns. |
| **Domain Expert** | Assesses scientific fitness for specific applications. |
| **Accessibility Tester** | Validates data supporting accessibility features. |
| **Community Contributor** | Collects data under supervised protocols. |

**Important:** Role separation becomes mandatory when the Project Lead did not personally collect the data. A dataset collected and approved by the same person must be flagged in the approval record.

---

## 4. Approval Workflow

### Step 1: Receive Candidate Dataset Notification

The validation pipeline produces a notification when a dataset reaches `candidate` status:

```
DATASET READY FOR HUMAN REVIEW

Dataset version: fiducials_aruco_v3
Validation status: PASS (all blocking checks passed)
Advisory findings: 3 outliers flagged, 2 coverage gaps identified
Report: reports/fiducials_aruco_v3_validation_report.md
Coverage score: 80%

Action required: Review report and issue approval decision.
```

---

### Step 2: Read the Full Validation Report

Open `reports/{dataset_version}_validation_report.md` (or `_report.json`).

Read every section. Do not skim. The report contains:

- Layer-by-layer validation results.
- All advisory outlier findings.
- Coverage gap analysis.
- Automated recommendations.
- Items specifically flagged for human judgment.

**Time budget:** A thorough report review should take 15–30 minutes for a standard fiducial dataset. If you find yourself approving in under 5 minutes, slow down.

---

### Step 3: Complete the Human Review Checklist

Work through the following checklist. Every item must receive an explicit response.

#### Section A — Collection Quality

```
□ A.1  I have read the collection notes for this dataset session.
□ A.2  The collection environment matches the conditions documented in the report.
□ A.3  The measurement instrument used is appropriate for the claimed precision.
□ A.4  The distance measurements are plausible for the stated environment.
□ A.5  The camera height values are plausible for the stated collection posture.
□ A.6  The device model and alias are correctly recorded.
□ A.7  I am aware of any unusual circumstances documented in the session notes.
□ A.8  The collection protocol was followed adequately (or deviations are documented).
```

#### Section B — Validation Results

```
□ B.1  All blocking validation checks passed.
□ B.2  I have reviewed each outlier-flagged record and made a disposition decision.
□ B.3  I understand the coverage gaps and accept them or have a plan to address them.
□ B.4  The detection success rate is consistent with my expectations for these conditions.
□ B.5  I have reviewed the distance-pixel correlation direction (should be inverse).
□ B.6  No records have been omitted from the validation report.
```

#### Section C — Synthetic / Hybrid (complete only for synthetic or hybrid datasets)

```
□ C.1  I have reviewed the generation parameters in syntheticParameters fields.
□ C.2  The synthetic data was generated from appropriate calibrated inputs.
□ C.3  I have reviewed the synthetic vs. real distribution comparison.
□ C.4  Intentional distribution deviations (e.g., extended range) are documented.
□ C.5  I am confident the synthetic data is physically plausible.
```

#### Section D — Fitness for Purpose

```
□ D.1  I understand which downstream repositories or analyses will use this dataset.
□ D.2  The dataset is fit for its stated intended purpose.
□ D.3  Any significant limitations for the intended use are documented in the report.
□ D.4  Known limitations are acknowledged in my approval decision.
□ D.5  No safety-relevant concerns exist in this dataset that are undocumented.
```

#### Section E — Research Integrity

```
□ E.1  Hypotheses supported by this dataset are clearly distinguished from validated findings.
□ E.2  Research debt items surfaced during collection or validation are documented.
□ E.3  I have not approved this dataset to meet a deadline at the expense of quality.
□ E.4  I would be comfortable if this approval record were reviewed by a future researcher.
```

---

### Step 4: Assess Each Advisory Item

For every outlier flagged and every coverage gap identified, record an explicit disposition:

**Outlier assessment format:**

| Record ID | Field | Value | My Assessment | Action |
|---|---|---|---|---|
| uuid-001 | markerWidthPx | 4850 | Detection artifact — lens reflection visible in image | Remove from approved version |
| uuid-002 | distanceMeters | 0.08 | Genuine close-range test — plausible | Retain with note |

**Coverage gap assessment format:**

| Gap | My Assessment | Action |
|---|---|---|
| No samples at 4.5 m | Valid gap — not yet collected | Document. Plan collection for v4. |
| No overhead orientation | Out of scope for MVP | Document. Defer to Tier 2. |

---

### Step 5: Issue Approval Decision

Four decisions are available:

#### APPROVE

All blocking checks passed. Advisory findings reviewed and dispositioned. Dataset is fit for its intended purpose. Known limitations acknowledged.

**Triggers:** Dataset moves to `approved` status and becomes immutable.

#### CONDITIONAL APPROVAL

The dataset passes all blocking checks and the reviewer approves it, but specifies conditions that must be addressed in the next version.

**Example:**
> "Approved. However, the 3 outlier records at ≥4500 px marker width must be investigated before v4 is collected. These records are retained in the approved dataset but flagged in the registry."

**Triggers:** Dataset moves to `approved` status. Conditions are recorded in the registry and in RESEARCH_DEBT.md.

#### REJECT — RETURN FOR REPROCESSING

Blocking issues were discovered during human review that were not caught by automated validation. Or the reviewer has specific grounds to question the collection circumstances.

**Example:**
> "Rejected. Review of session notes reveals the 2.0 m samples were collected in a reflective glass corridor that was not documented as such. The distance-pixel relationship at 2.0 m shows anomalous values that may be artifacts of specular reflection. Recollect 2.0 m samples in a standard hallway environment."

**Triggers:** Dataset remains in `validated` state. Rejection reason logged. Dataset may be reprocessed and resubmitted as a new candidate.

#### REJECT — ARCHIVE

The dataset has fundamental problems that cannot be corrected through reprocessing. It is archived for reference value only and will not be promoted to approved.

**Triggers:** Dataset moved to `datasets/rejected/` with full rejection documentation.

---

### Step 6: Complete the Approval Record

Fill in the approval record in `reports/{dataset_version}_report.md` Section 10, and in `registry/dataset_registry.json`.

**Approval record fields:**

```json
{
  "datasetVersion": "fiducials_aruco_v3",
  "reviewerRole": "Project Lead",
  "reviewDate": "2026-06-16",
  "decision": "APPROVED",
  "approvalNotes": "All checks passed. Two coverage gaps at 4.5m and 5.0m noted and accepted. Plan to extend with real collection in v4. Outlier at record uuid-001 assessed as detection artifact (reflection) and retained with note.",
  "checklistCompleted": true,
  "knownLimitationsAcknowledged": true,
  "researchDebtAcknowledged": true,
  "conditions": [],
  "self_collected": true
}
```

---

### Step 7: Trigger Immutability

After completing the approval record:

```python
from factory.versioning.version_manager import VersionManager

vm = VersionManager()
vm.promote_to_approved(
    dataset_version="fiducials_aruco_v3",
    approval_record={
        "decision": "APPROVED",
        "reviewDate": "2026-06-16",
        "approver": "Project Lead",
        "notes": "..."
    }
)
# Dataset is now immutable in datasets/approved/fiducials_aruco_v3/
# checksum_manifest.json generated and stored
# registry/dataset_registry.json updated
```

---

## 5. Approval Quality Standards

### What Good Approval Looks Like

A well-conducted approval:
- Reviews every finding, not just the summary.
- Documents reasoning for each advisory disposition.
- Acknowledges limitations honestly even when approving.
- Surfaces any concerns as research debt even when approving.
- Takes enough time to be considered rather than ceremonial.

### What Poor Approval Looks Like

Signs that an approval may be inadequate:
- Approval granted without reviewing session notes.
- Advisory findings dismissed without written rationale.
- Coverage gaps accepted without a documented plan.
- Approval completed in under 5 minutes for a 100-record dataset.
- Limitations omitted from approval notes to avoid documenting problems.

**Constitutional rule:** An approval issued carelessly is a scientific liability. Future Auriga phases will depend on the integrity of approved datasets. If a dataset later reveals problems that a careful review would have caught, the approval record becomes a point of failure in the scientific record.

---

## 6. Special Case — Self-Collected Data

When the Project Lead both collected and approves a dataset:

1. The `self_collected: true` flag must be set in the approval record.
2. Particular attention must be paid to Section A items — the collector's memory of "how it felt" to collect the data may bias the review.
3. A cooling-off period of at least 24 hours between collection and approval is recommended.
4. If any anomaly is noted, err toward documenting it rather than dismissing it from memory.

---

## 7. Handling Uncertainty

When you are genuinely uncertain about an advisory finding, the correct action is:

1. Document the uncertainty in the approval notes.
2. Create a research debt entry for the open question.
3. Proceed with approval if the uncertainty does not affect fitness for purpose.
4. Reject if the uncertainty affects safety-relevant or hypothesis-critical data.

**Principle:** Honest uncertainty is better than false confidence. An approved dataset with documented open questions is scientifically healthier than an approved dataset where known questions were suppressed.

---

## 8. Approval Record Retention

- Approval records are permanent. They are never deleted.
- Approval records are committed to the GitHub repository alongside the approved dataset.
- Approval records from rejected datasets are also retained in `datasets/rejected/`.

---

## 9. Future Multi-Reviewer Expansion

When future reviewers beyond the Project Lead participate:

- Each reviewer completes the checklist independently.
- Conflicting assessments are reconciled through documented discussion.
- The Project Lead has final approval authority.
- Community contributors may review but not approve.
- Conflict resolution notes are recorded in the approval record.

---

## 10. Research Debt

| ID | Question |
|---|---|
| RD-020 | Should a minimum cooling-off period between collection and approval be enforced? |
| RD-021 | Should a peer review mechanism be introduced before approval for safety-relevant datasets? |

---

## 11. Human Approval Record

| Field | Value |
|---|---|
| Document | HUMAN_DATA_APPROVAL_GUIDE.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
| Notes | — |
