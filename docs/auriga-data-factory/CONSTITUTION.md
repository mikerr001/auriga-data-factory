# CONSTITUTION.md
# Auriga Data Factory — Constitutional Rules

**Version:** 1.0.0
**Status:** Draft — Pending Human Approval
**Repository:** auriga-data-factory

---

## Preamble

This document records the constitutional constraints governing all operations within the Auriga Data Factory and, by extension, all AI agents, contributors, and downstream repositories that interact with it.

These rules exist because Project Auriga is simultaneously:
- An assistive technology for visually impaired users (safety-critical).
- A scientific research effort (integrity-critical).
- A privacy-preserving platform (privacy-critical).
- An offline, explainable system (trustworthiness-critical).

Constitutional rules reflect decisions that have been made deliberately, with awareness of their tradeoffs, and which must not be overridden by convenience, speed, or automated reasoning alone.

**Amendment process:** Constitutional rules may only be changed through explicit documented review by the Project Lead. AI agents may propose amendments but may not enact them unilaterally.

---

## Section 1 — Privacy and Data Governance

**P-1** Never upload user-collected environmental imagery to third-party cloud services by default.

**P-2** Never transmit place memories, spatial signatures, navigation histories, or environmental representations off-device without explicit user opt-in and constitutional review.

**P-3** Never store personally identifying information that is not strictly necessary for system function.

**P-4** Never record device serial numbers, IMEI numbers, Android IDs, MAC addresses, or hardware fingerprints in any dataset.

**P-5** Never record collector names, email addresses, contact information, precise home addresses, or unrelated personal metadata within datasets. Use project roles or aliases only.

**P-6** Place memories shall remain on-device by default. This is not a convenience — it is a constitutional commitment to users who trust Auriga with their physical environments.

---

## Section 2 — Safety

**S-1** Never present Auriga as a replacement for professional mobility aids or orientation and mobility training.

**S-2** Never communicate certainty when the system possesses only probabilistic estimates.

**S-3** Safety-critical outputs must expose confidence estimates whenever feasible.

**S-4** Never suppress uncertainty in environments where perception quality is degraded.

**S-5** Never encourage users to engage in unsafe behavior based solely on Auriga's recommendations.

**S-6** Any dataset or model used to support safety-relevant outputs must carry explicit documentation of its known limitations and failure modes.

---

## Section 3 — Engineering Philosophy

**E-1** Offline operation shall remain the default architectural assumption.

**E-2** Never introduce mandatory cloud dependencies without constitutional review.

**E-3** Never optimize solely for benchmark performance at the expense of explainability.

**E-4** Whenever feasible, favor interpretable geometric approaches before introducing opaque alternatives.

**E-5** Any departure from explainable methods must document the rationale, expected benefits, and known risks.

**E-6** Low-end commodity devices shall remain a supported target throughout MVP development. Never design a critical workflow that requires hardware beyond a standard smartphone camera.

**E-7** Never assume access to specialized sensors such as LiDAR, depth cameras, or IMU arrays as required inputs.

---

## Section 4 — Research Integrity

**R-1** Never report hypotheses as established facts.

**R-2** Distinguish clearly between: validated findings, working assumptions, exploratory ideas, and unresolved research questions. These categories must not be conflated.

**R-3** Never modify approved datasets retroactively. Corrections require new versions.

**R-4** Research debt must be documented explicitly and tracked. It may not be silently deferred.

**R-5** Every phase must include both automated and human validation.

**R-6** Every release must include a known-limitations section.

**R-7** Experimental features must be clearly identified as experimental.

**R-8** Never hide known problems simply to accelerate development. Known limitations, assumptions, and research debt shall be documented explicitly and revisited systematically.

---

## Section 5 — Data Collection and Validation

**D-1** Approved datasets are immutable. No modification after approval.

**D-2** Corrections to approved datasets shall create new versions, never overwrite prior versions.

**D-3** Provenance metadata must never be removed from datasets.

**D-4** Known data limitations must be documented, not concealed.

**D-5** Synthetic samples must never be unlabelled or mixed with real samples without explicit hybrid dataset classification.

**D-6** No dataset may be approved without passing automated validation.

**D-7** No dataset may be approved without human review.

**D-8** Validation failures may not be reclassified as successes without documented justification.

**D-9** Validation logs must be archived. They may not be silently discarded.

---

## Section 6 — Observability and Transparency

**O-1** Never discard validation logs without an archival rationale.

**O-2** Major architectural decisions shall generate corresponding research debt entries where uncertainty remains.

**O-3** Failures shall be documented rather than hidden.

**O-4** Validation failures shall not be reclassified as successes without documented justification.

**O-5** Agents performing self-validation must expose their reasoning and assumptions.

---

## Section 7 — AI Development Governance

**A-1** AI-generated outputs shall not bypass human oversight for constitutional decisions.

**A-2** AI agents may propose architectural changes but shall not redefine constitutional rules autonomously.

**A-3** Self-correction mechanisms should be attempted before escalation to human reviewers.

**A-4** Human reviewers retain final authority over approvals affecting safety, datasets, and constitutional standards.

**A-5** AI agents must distinguish between what has been validated and what has been assumed.

**A-6** AI-generated documentation must be reviewed by the Project Lead before it carries constitutional weight.

---

## Section 8 — Accessibility Mission

**AC-1** Accessibility objectives shall take precedence over aesthetic considerations.

**AC-2** Never design critical workflows that exclude users with limited connectivity or low-end devices.

**AC-3** The system is intended to augment a user's environmental awareness, never to replace human judgment in safety-critical situations.

---

## Section 9 — General Principles

**G-1** If a design decision improves convenience at the expense of user privacy, user safety, scientific integrity, or explainability, the burden of proof rests on the proposed change.

**G-2** When uncertainty exists regarding whether an action violates the spirit of these rules, the more conservative interpretation shall prevail until formal review is completed.

**G-3** The measure of Auriga's quality is not benchmark performance but trustworthy, explainable service to users who depend on it.

---

## Amendment Log

| Amendment | Date | Description | Approved by |
|---|---|---|---|
| Initial constitution | 2026-06-16 | First version established | Pending human approval |

---

## Human Approval Record

| Field | Value |
|---|---|
| Document | CONSTITUTION.md |
| Version | 1.0.0 |
| Prepared by | Auriga Data Factory Design Agent |
| Prepared date | 2026-06-16 |
| Reviewed by | — |
| Review date | — |
| Decision | **PENDING HUMAN APPROVAL** |
