# Auriga Data Factory — Architecture Overview

## Philosophy

The Data Factory is the source of truth for all Auriga datasets. It embodies
the Project Auriga philosophy: scientific rigour, privacy, explainability,
reproducibility, and observability.

## Module Structure

```
auriga_data_factory/
├── __init__.py          # Package identity and constitutional summary
├── __main__.py          # python -m auriga_data_factory entry point
│
├── schema/              # Canonical data representations
│   ├── canonical.py     # CanonicalSample, CanonicalDataset, enums
│   └── versioning.py    # DatasetVersion (semantic versioning)
│
├── ingestion/           # Dataset import pipeline
│   ├── engine.py        # IngestionEngine — orchestrator
│   └── adapters.py      # CSVAdapter, AurigaFiducialAdapter, LegacyExperimentAdapter
│                        # BaseAdapter — extension point for custom formats
│
├── validation/          # Automated validation pipeline
│   ├── engine.py        # ValidationEngine — 7 checks
│   └── results.py       # ValidationResult, ValidationReport, ValidationStatus
│
├── coverage/            # Coverage analysis
│   ├── engine.py        # CoverageEngine — 4 dimensions
│   └── results.py       # CoverageReport, CoverageScore
│
├── synthetic/           # Geometry-based synthetic generation
│   └── generator.py     # SyntheticGenerator (perspective, bearing, height)
│
├── approval/            # Lifecycle workflow
│   └── workflow.py      # ApprovalWorkflow — constitutional guardrails
│
├── observability/       # Structured logging and research debt
│   ├── logger.py        # AurigaLogger, get_logger
│   └── research_debt.py # ResearchDebt, ResearchDebtRegister
│
├── reports/             # Report generation
│   └── generator.py     # ReportGenerator — JSON, Markdown, text outputs
│
├── cli/                 # Command-line interfaces
│   └── main.py          # All CLI commands
│
└── tests/               # Unit test suite
    ├── test_schema.py
    ├── test_ingestion.py
    ├── test_validation.py
    ├── test_coverage.py
    ├── test_synthetic.py
    ├── test_approval.py
    ├── test_observability.py
    └── test_reports.py
```

## Data Flow

```
External Data Source
    │
    ▼
IngestionEngine ──► BaseAdapter subclass
    │               (CSV / AurigaFiducial / Legacy / Custom)
    ▼
CanonicalDataset (state=candidate)
    │
    ▼
ValidationEngine ──► ValidationReport (PASS/WARNING/FAIL per check)
    │
    ▼  (all checks pass)
DatasetState: validated
    │
    ▼  (human reviewer records sign-off)
DatasetState: human_reviewed
    │
    ▼  (approver records approval)
DatasetState: approved ──► checksum locked ──► immutable
    │
    ▼  (optional)
DatasetState: archived
```

## Constitutional Constraints (enforced in code)

| Constraint | Enforcement Location |
|------------|---------------------|
| No hardware IDs | `device_alias` field only; no hardware ID field exists |
| No cloud transmission | All I/O uses `pathlib.Path` (local filesystem only) |
| Approved = immutable | `ApprovalWorkflow.promote_to_approved` locks checksum |
| Human approval required | `promote_to_approved` requires prior `human_reviewed` state |
| Failures never hidden | `ValidationEngine.validate` catches all exceptions as FAIL results |
| Provenance preserved | `CanonicalSample.provenance` dict; `CanonicalDataset.provenance` dict |
| Real vs synthetic distinguished | `SourceType` enum; `is_synthetic` property |
| Uncertainty documented | Synthetic notes always reference `RD-DATA-001` |

## Research Debt Summary

| ID | Subsystem | Summary |
|----|-----------|---------|
| RD-DATA-001 | synthetic | Perspective model does not capture lens distortion or sensor noise |
| RD-DATA-002 | coverage | Coverage thresholds are heuristic; need empirical calibration |
| RD-DATA-003 | validation | IQR outlier multiplier (1.5) needs domain-expert calibration |
| RD-DATA-004 | approval | File-based approval lacks cryptographic non-repudiation |
