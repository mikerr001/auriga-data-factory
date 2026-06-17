# Auriga Data Factory

Research laboratory for the [Project Auriga](https://github.com/your-org/auriga) spatial intelligence ecosystem.

Responsible for ingesting, validating, generating, versioning, and distributing datasets used throughout Auriga's development.

---

## Documents

| Document | Purpose |
|---|---|
| [DATA_FACTORY_ARCHITECTURE.md](docs/DATA_FACTORY_ARCHITECTURE.md) | System design, subsystems, data flow, constitutional rules |
| [DATASET_SPECIFICATIONS.md](docs/DATASET_SPECIFICATIONS.md) | Dataset families, canonical schema, field definitions |
| [DATA_VERSIONING_GUIDE.md](docs/DATA_VERSIONING_GUIDE.md) | Versioning conventions, lifecycle, immutability |
| [DATA_VALIDATION_PROTOCOL.md](docs/DATA_VALIDATION_PROTOCOL.md) | 7-layer validation pipeline |
| [SYNTHETIC_GENERATION_GUIDE.md](docs/SYNTHETIC_GENERATION_GUIDE.md) | Mathematical synthetic data generation |
| [COVERAGE_ANALYSIS_GUIDE.md](docs/COVERAGE_ANALYSIS_GUIDE.md) | Gap detection and collection recommendations |
| [DATASET_REPORT_TEMPLATE.md](docs/DATASET_REPORT_TEMPLATE.md) | Approval report template |
| [DATA_INGESTION_GUIDE.md](docs/DATA_INGESTION_GUIDE.md) | Collection protocols, CSV format, legacy migration |
| [EXPORT_PIPELINE_GUIDE.md](docs/EXPORT_PIPELINE_GUIDE.md) | Export formats and downstream consumer contracts |
| [HUMAN_DATA_APPROVAL_GUIDE.md](docs/HUMAN_DATA_APPROVAL_GUIDE.md) | Approval workflow and checklist |
| [CONSTITUTION.md](docs/CONSTITUTION.md) | 45 constitutional rules governing all operations |
| [ADVERSARIAL_REVIEW.md](docs/ADVERSARIAL_REVIEW.md) | Self-attack log, risks, and human validation checklist |
| [RESEARCH_DEBT.md](docs/RESEARCH_DEBT.md) | 26 open research questions |

## Quick Start

```python
from factory.ingestion import CsvIngestor
from factory.validation import Validator
from factory.coverage import CoverageAnalyzer
from factory.versioning import VersionManager

# Ingest
ingestor = CsvIngestor()
result = ingestor.ingest("datasets/raw/fiducials_aruco_v3/", "fiducials_aruco_v3")

# Validate
validator = Validator()
validation = validator.validate(result._records, "fiducials_aruco_v3")
validation.save_report("reports/")

# Coverage
analyzer = CoverageAnalyzer()
coverage = analyzer.analyze(result._records, "fiducials_aruco_v3")
print(coverage.summary())
```

## Constitutional Position

All operations are governed by [CONSTITUTION.md](docs/CONSTITUTION.md).

Key rules:
- Approved datasets are **immutable**.
- **No personally identifying information** is stored.
- Synthetic data is always **labelled** and never silently mixed with real data.
- **No dataset may be approved** without automated validation and human review.
- **No cloud dependencies** in MVP. Runs in Replit, Colab, or local Python.

## Status

**Version:** 1.0.0 — All documents pending human approval.
