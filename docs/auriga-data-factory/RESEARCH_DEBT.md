# RESEARCH_DEBT.md
# Auriga Data Factory — Research Debt Register

**Version:** 1.0.0
**Status:** Living document — updated as questions are resolved or added
**Repository:** auriga-data-factory

---

## Purpose

This register tracks all open research questions, unvalidated design estimates, and deferred decisions within the Auriga Data Factory. Every entry here represents a place where uncertainty exists and future empirical work or deliberate architectural decisions are needed.

Research debt is not failure. It is honesty about the boundary between what is known and what is assumed.

**Rule:** An entry in this register must never be treated as a resolved question until evidence-based resolution is documented and the entry is marked `RESOLVED`.

---

## Register

| ID | Question | Source Document | Priority | Status | Resolution |
|---|---|---|---|---|---|
| RD-001 | What minimum sample count per condition is sufficient for statistical validity in fiducial datasets? | DATASET_SPECIFICATIONS, COVERAGE_ANALYSIS | High | **OPEN** | — |
| RD-002 | Outlier detection thresholds for geometric fields (pixel dimensions, distances) need empirical calibration against real Auriga data | DATA_VALIDATION_PROTOCOL | High | **OPEN** | — |
| RD-003 | Which statistical tests (KS test, Mann-Whitney U, etc.) are appropriate for synthetic vs. real distribution comparison? | SYNTHETIC_GENERATION_GUIDE | Medium | **OPEN** | — |
| RD-004 | Should hybrid datasets receive separate validation treatment from pure real datasets? | DATASET_SPECIFICATIONS | Medium | **OPEN** | — |
| RD-005 | Coverage gap severity scoring and dimension weights (Distance 0.50, Orientation 0.25, etc.) are design estimates needing empirical calibration | COVERAGE_ANALYSIS_GUIDE | Medium | **OPEN** | — |
| RD-006 | Should a semantic versioning policy (major/minor/patch) replace simple sequential numbering for datasets? | DATA_VERSIONING_GUIDE | Low | **OPEN** | — |
| RD-007 | Should the dataset registry be migrated from JSON to SQLite as the dataset count grows? | DATA_VERSIONING_GUIDE | Low | **OPEN** | — |
| RD-008 | Image content hash duplicate detection is not implemented in MVP. Should it be added? | DATA_VALIDATION_PROTOCOL | Medium | **OPEN** | — |
| RD-009 | What consistency tolerance should apply to the marker area vs. dimension product check (C-03)? Currently set at 20% — is this appropriate? | DATA_VALIDATION_PROTOCOL | Medium | **OPEN** | — |
| RD-010 | AugmentationGenerator, RenderingGenerator, MLGenerator — define conditions and requirements for future implementation | SYNTHETIC_GENERATION_GUIDE | Low | **OPEN** | — |
| RD-011 | Noise standard deviation (std=0.03) for FiducialAppearanceModel is an uncalibrated estimate. Must be calibrated against real Auriga data before synthetic datasets are used downstream | SYNTHETIC_GENERATION_GUIDE | **Critical** | **OPEN** | — |
| RD-012 | Focal length — should it be treated as a constant per device model or as a calibrated-per-session parameter? What variation exists across sessions with the same device? | SYNTHETIC_GENERATION_GUIDE, DATA_FACTORY_ARCHITECTURE | High | **OPEN** | — |
| RD-013 | How should lens distortion be modelled in the GeometryGenerator? Current model assumes ideal optics | SYNTHETIC_GENERATION_GUIDE | High | **OPEN** | — |
| RD-014 | Should the coverage score incorporate detection success rate as a separate coverage dimension? | COVERAGE_ANALYSIS_GUIDE | Low | **OPEN** | — |
| RD-015 | Should the ingestor support JSON metadata as a first-class input format alongside CSV? | DATA_INGESTION_GUIDE | Medium | **OPEN** | — |
| RD-016 | Strategy for recovering timestamps from image EXIF data when CSV timestamps are missing | DATA_INGESTION_GUIDE | Low | **OPEN** | — |
| RD-017 | Should image filenames be enforced strictly by the ingestor (reject non-conforming) or normalised automatically? | DATA_INGESTION_GUIDE | Low | **OPEN** | — |
| RD-018 | Should future exports support a streaming or API-based distribution model rather than file bundles? | EXPORT_PIPELINE_GUIDE | Low | **OPEN** | — |
| RD-019 | Should the Colab bundle auto-generate analysis code specific to each dataset family? | EXPORT_PIPELINE_GUIDE | Low | **OPEN** | — |
| RD-020 | Should a minimum 24-hour cooling-off period between collection and approval be enforced programmatically? | HUMAN_DATA_APPROVAL_GUIDE | Low | **OPEN** | — |
| RD-021 | Should a peer review mechanism be introduced for safety-relevant datasets before approval? | HUMAN_DATA_APPROVAL_GUIDE | Medium | **OPEN** | — |
| RD-022 | Add session hash check to the ingestor to prevent accidental double-ingestion of the same collection session | ADVERSARIAL_REVIEW (ATTACK-003) | High | **OPEN** | — |
| RD-023 | Evaluate filesystem-level write protection or git-based immutability for approved datasets | ADVERSARIAL_REVIEW (ATTACK-004) | Medium | **OPEN** | — |
| RD-024 | Export pipeline — define rate limiting and access control for future multi-contributor context | ADVERSARIAL_REVIEW (ATTACK-007) | Low | **OPEN** | — |
| RD-025 | Large image datasets should not live in Git directly. Define Git LFS or separate storage strategy before first dataset exceeds ~500 MB | ADVERSARIAL_REVIEW (ATTACK-010) | Medium | **OPEN** | — |
| RD-026 | Add `markerId` as an optional canonical schema field to support per-ID detection analysis | ADVERSARIAL_REVIEW (ATTACK-001) | Medium | **OPEN** | — |

---

## Resolution Protocol

When a research debt item is resolved:

1. Update the `Status` to `RESOLVED`.
2. Document the resolution in the `Resolution` column.
3. Update the relevant source document(s) to reflect the resolved decision.
4. If the resolution changes a constitutional rule, update CONSTITUTION.md.
5. Commit the updated register to GitHub with a note in the commit message.

---

## Human Approval Record

| Field | Value |
|---|---|
| Document | RESEARCH_DEBT.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
