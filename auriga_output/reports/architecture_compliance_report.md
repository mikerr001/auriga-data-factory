# Architecture Compliance Report — Auriga Data Factory

Generated automatically. Maps each specification requirement to its implementation.

## Primary Objectives

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Dataset Ingestion Engine | ✓ IMPLEMENTED | `auriga_data_factory/ingestion/engine.py` |
| CSV + image directory support | ✓ IMPLEMENTED | `ingestion/adapters.py::CSVAdapter` |
| Auriga fiducial dataset support | ✓ IMPLEMENTED | `ingestion/adapters.py::AurigaFiducialAdapter` |
| Legacy experimental dataset support | ✓ IMPLEMENTED | `ingestion/adapters.py::LegacyExperimentAdapter` |
| Adapter interface for extensibility | ✓ IMPLEMENTED | `ingestion/adapters.py::BaseAdapter` |
| Canonical dataset objects | ✓ IMPLEMENTED | `schema/canonical.py::CanonicalDataset` |
| Ingestion reports | ✓ IMPLEMENTED | `reports/generator.py::save_ingestion_report` |
| Provenance preservation | ✓ IMPLEMENTED | `CanonicalSample.provenance` field |
| Canonical schema with all required fields | ✓ IMPLEMENTED | `schema/canonical.py::CanonicalSample` |
| Versioned schema | ✓ IMPLEMENTED | `schema/versioning.py::DatasetVersion` |
| Forward-compatible schema | ✓ IMPLEMENTED | `CanonicalSample.from_dict` (unknown keys dropped) |
| Automated Validation Engine | ✓ IMPLEMENTED | `validation/engine.py::ValidationEngine` |
| Schema validation | ✓ IMPLEMENTED | `ValidationEngine._check_schema` |
| Missing image detection | ✓ IMPLEMENTED | `ValidationEngine._check_missing_images` |
| Duplicate detection | ✓ IMPLEMENTED | `ValidationEngine._check_duplicates` |
| Impossible measurement detection | ✓ IMPLEMENTED | `ValidationEngine._check_impossible_measurements` |
| Outlier identification | ✓ IMPLEMENTED | `ValidationEngine._check_outliers` |
| Coverage completeness checks | ✓ IMPLEMENTED | `ValidationEngine._check_coverage_completeness` |
| Referential integrity checks | ✓ IMPLEMENTED | `ValidationEngine._check_referential_integrity` |
| PASS/WARNING/FAIL categorisation | ✓ IMPLEMENTED | `validation/results.py::ValidationStatus` |
| Machine-readable reports | ✓ IMPLEMENTED | `ValidationReport.to_dict()` → JSON |
| Human-readable reports | ✓ IMPLEMENTED | `ValidationReport.as_text()` + Markdown |
| Coverage Analysis Engine | ✓ IMPLEMENTED | `coverage/engine.py::CoverageEngine` |
| Distance coverage | ✓ IMPLEMENTED | `CoverageEngine._analyse_distance` |
| Orientation coverage | ✓ IMPLEMENTED | `CoverageEngine._analyse_orientation` |
| Device coverage | ✓ IMPLEMENTED | `CoverageEngine._analyse_device` |
| Sample distribution balance | ✓ IMPLEMENTED | `CoverageEngine._analyse_balance` |
| Coverage heatmaps | ✓ IMPLEMENTED | `CoverageEngine._build_heatmap` |
| Collection recommendations | ✓ IMPLEMENTED | `CoverageEngine._generate_recommendations` |
| Coverage scores | ✓ IMPLEMENTED | `coverage/results.py::CoverageScore` |
| Synthetic Geometry Generator | ✓ IMPLEMENTED | `synthetic/generator.py::SyntheticGenerator` |
| No GANs / no diffusion models | ✓ COMPLIANT | Perspective projection only |
| Perspective scaling model | ✓ IMPLEMENTED | `generator.py::_perspective_pixel_size` |
| Bearing change model | ✓ IMPLEMENTED | `SyntheticGenerator.generate_bearing_variants` |
| Camera height variation | ✓ IMPLEMENTED | `SyntheticGenerator.generate_height_variants` |
| Synthetic labelling | ✓ IMPLEMENTED | `source_type='synthetic'` on all generated samples |
| Dataset Approval Workflow | ✓ IMPLEMENTED | `approval/workflow.py::ApprovalWorkflow` |
| candidate → validated | ✓ IMPLEMENTED | `promote_to_validated` (requires validation PASS) |
| validated → human_reviewed | ✓ IMPLEMENTED | `promote_to_human_reviewed` (requires reviewer name) |
| human_reviewed → approved | ✓ IMPLEMENTED | `promote_to_approved` (checksum locked) |
| approved → archived | ✓ IMPLEMENTED | `ApprovalWorkflow.archive` |
| Immutable approved datasets | ✓ IMPLEMENTED | Checksum + `verify_integrity` |
| Modification produces new version | ✓ IMPLEMENTED | `ApprovalWorkflow.create_new_version` |
| Observability / structured logging | ✓ IMPLEMENTED | `observability/logger.py::AurigaLogger` |
| Ingestion events | ✓ IMPLEMENTED | `AurigaLogger.ingestion` |
| Validation events | ✓ IMPLEMENTED | `AurigaLogger.validation` |
| Promotion events | ✓ IMPLEMENTED | `AurigaLogger.promotion` |
| Research debt identifiers | ✓ IMPLEMENTED | `observability/research_debt.py::ResearchDebtRegister` |

## Constitutional Constraints

| Constraint | Status | Enforcement |
|------------|--------|-------------|
| Never store unique hardware identifiers | ✓ COMPLIANT | `device_alias` used, not hardware ID |
| Never transmit to cloud by default | ✓ COMPLIANT | All I/O is local file system only |
| Never modify approved datasets | ✓ COMPLIANT | `create_new_version` required; checksum locks |
| Never bypass human approval | ✓ COMPLIANT | `promote_to_approved` requires prior human_reviewed state |
| Never hide validation failures | ✓ COMPLIANT | All failures surface in `ValidationReport` |
| Always preserve provenance | ✓ COMPLIANT | `provenance` field on every sample and dataset |
| Always distinguish real vs synthetic | ✓ COMPLIANT | `source_type` enum; `is_synthetic` property |
| Always document uncertainty | ✓ COMPLIANT | RD-DATA-001 in synthetic notes and debt register |
