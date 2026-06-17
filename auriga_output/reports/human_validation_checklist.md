# Human Validation Checklist — Auriga Data Factory

Use this checklist to manually verify the Data Factory implementation
against the Auriga specification.

## 1. Ingestion

- [ ] Can a CSV metadata file be imported using `auriga-factory ingest`?
- [ ] Are all canonical fields populated in the output JSON dataset?
- [ ] Is provenance information recorded (source file, adapter used, timestamp)?
- [ ] Can a directory containing `metadata.csv` + `images/` be ingested?
- [ ] Can a legacy JSON experiment file be imported?
- [ ] Is an ingestion report generated?
- [ ] Does the dataset start in `candidate` state after ingestion?

## 2. Validation

- [ ] Does the validation engine accept a valid dataset without errors?
- [ ] Does the validation engine FAIL a dataset with missing required fields?
- [ ] Does the validation engine FAIL a dataset referencing non-existent image files?
- [ ] Does the validation engine detect duplicate sample IDs?
- [ ] Does the validation engine detect impossible values (e.g. negative distance)?
- [ ] Does the validation engine detect outliers in numeric fields?
- [ ] Does the validation engine WARNING when coverage is sparse?
- [ ] Is a machine-readable JSON report generated?
- [ ] Is a human-readable text/Markdown report generated?
- [ ] Are ALL failures reported — none hidden?

## 3. Coverage Analysis

- [ ] Does the coverage engine report a score for each dimension?
- [ ] Are collection recommendations generated (e.g. "Collect 3 more at 2.5m Down")?
- [ ] Is a coverage heatmap matrix included in the output?
- [ ] Does overall score reflect true dataset completeness?

## 4. Synthetic Generation

- [ ] Can synthetic samples be generated via `auriga-factory generate-synthetic`?
- [ ] Are all synthetic samples labelled `source_type='synthetic'`?
- [ ] Do generated pixel sizes scale correctly with distance (larger at closer range)?
- [ ] Do synthetic samples carry provenance and uncertainty notes?
- [ ] Is RD-DATA-001 referenced in synthetic sample notes?

## 5. Approval Workflow

- [ ] Can a candidate dataset be promoted to `validated` after passing validation?
- [ ] Is promotion to `validated` blocked if validation fails?
- [ ] Can a validated dataset be marked `human_reviewed` with a reviewer name?
- [ ] Is human_reviewed promotion blocked without a non-empty reviewer name?
- [ ] Can a human_reviewed dataset be promoted to `approved`?
- [ ] Is a content checksum stored on approval?
- [ ] Does `verify_integrity` return True immediately after approval?
- [ ] Does `verify_integrity` return False after manually editing an approved dataset?
- [ ] Can an approved dataset be archived?
- [ ] Does `create_new_version` produce a new `candidate` dataset without modifying the approved one?

## 6. Observability

- [ ] Are ingestion events visible in console logs?
- [ ] Are validation events logged with dataset ID?
- [ ] Are promotion events logged with approver name and new state?
- [ ] Are errors logged with exception detail?
- [ ] Does the research debt register list all RD-DATA-* items?
- [ ] Can the research debt register be exported as Markdown?

## 7. Constitutional Constraints

- [ ] Confirm no unique hardware identifiers are stored (check `device_model` and `device_alias` fields).
- [ ] Confirm no network calls are made during ingestion, validation, or approval.
- [ ] Confirm an approved dataset cannot be silently modified (checksum check).
- [ ] Confirm synthetic samples are clearly distinguishable from real samples.

## 8. CLI

- [ ] Does `python -m auriga_data_factory.cli.main --help` display usage?
- [ ] Does `ingest` command produce a JSON dataset file?
- [ ] Does `validate` command produce validation report files?
- [ ] Does `analyse-coverage` command produce coverage report files?
- [ ] Does `generate-synthetic` command produce samples?
- [ ] Does `approve` pipeline work end-to-end?
- [ ] Does `debt-register` command produce the research debt report?
