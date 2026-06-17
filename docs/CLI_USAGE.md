# Auriga Data Factory — CLI Usage Guide

## Installation

```bash
# From the repository root:
pip install -e .
# Or run directly without installing:
python -m auriga_data_factory <command> [options]
```

## Global Options

```
--output-dir PATH    Base directory for all output files (default: auriga_output/)
--version            Show version and exit
--help               Show help and exit
```

---

## Commands

### `ingest` — Import a dataset

Import a CSV file or Auriga fiducial experiment directory into a canonical dataset.

```bash
python -m auriga_data_factory ingest <source> <name> [options]
```

**Arguments:**
- `source` — Path to CSV file or directory containing `metadata.csv`
- `name`   — Human-readable name for the dataset

**Options:**
```
--adapter {csv,auriga_fiducial,legacy}   Ingestion adapter (default: auriga_fiducial)
--version VERSION                         Dataset version string (default: 1.0.0)
--notes TEXT                             Free-text notes
```

**Examples:**
```bash
# Import an Auriga fiducial directory
python -m auriga_data_factory ingest \
    experiments/aruco_lab_v1/ \
    "ArUco Lab Experiment v1" \
    --adapter auriga_fiducial

# Import a plain CSV file
python -m auriga_data_factory ingest \
    data/measurements.csv \
    "Manual Measurements" \
    --adapter csv

# Import a legacy JSON experiment
python -m auriga_data_factory ingest \
    data/old_experiment.json \
    "Legacy Series A" \
    --adapter legacy
```

**Output:**
- `auriga_output/datasets/<name>_v<version>_<id>.json` — canonical dataset
- `auriga_output/reports/ingestion_<id>_<timestamp>.json` — ingestion report

---

### `validate` — Run validation checks

Run all seven validation checks on an existing canonical dataset file.

```bash
python -m auriga_data_factory validate <dataset_file> [options]
```

**Options:**
```
--skip-images    Skip image file existence checks (useful when images are remote)
```

**Examples:**
```bash
python -m auriga_data_factory validate \
    auriga_output/datasets/ArUco_Lab_v1.0.0_abc12345.json

python -m auriga_data_factory validate \
    auriga_output/datasets/ArUco_Lab_v1.0.0_abc12345.json \
    --skip-images
```

**Output:**
- `auriga_output/reports/validation_<id>_<timestamp>.json` — machine-readable
- `auriga_output/reports/validation_<id>_<timestamp>.md`   — human-readable Markdown
- `auriga_output/reports/validation_<id>_<timestamp>.txt`  — plain text summary

**Exit codes:** `0` = PASS or WARNING, `1` = FAIL

---

### `analyse-coverage` — Coverage analysis

Analyse how completely the dataset covers the expected (distance × orientation) space.

```bash
python -m auriga_data_factory analyse-coverage <dataset_file>
```

**Output:**
- JSON, Markdown, and text coverage reports
- Coverage heatmap (in JSON)
- Specific collection recommendations

---

### `generate-synthetic` — Generate synthetic samples

Generate synthetic samples using the perspective projection model.

```bash
python -m auriga_data_factory generate-synthetic <name> [options]
```

**Options:**
```
--distances FLOAT [FLOAT ...]    Distance values in metres (default: 0.5 1.0 1.5 2.0 2.5 3.0)
--orientations STR [STR ...]     Orientation labels (default: Down Up Left)
--samples-per-cell INT           Samples per cell (default: 5)
--seed INT                       Random seed for reproducibility
```

**Example:**
```bash
python -m auriga_data_factory generate-synthetic \
    "Synthetic Perspective Set 1" \
    --distances 0.5 1.0 1.5 2.0 2.5 3.0 4.0 5.0 \
    --orientations Down Up Left Right Angled \
    --samples-per-cell 10 \
    --seed 42
```

**Note:** All generated samples are labelled `source_type='synthetic'` and carry
uncertainty documentation referencing `RD-DATA-001`.

---

### `promote` — Advance dataset state

Manually advance a dataset through the approval workflow.

```bash
python -m auriga_data_factory promote <dataset_file> <target_state> [options]
```

**Target states:** `validated`, `human_reviewed`, `approved`, `archived`

**Options:**
```
--reviewer TEXT    Reviewer name (required for human_reviewed)
--approver TEXT    Approver name (required for approved)
--notes TEXT       Free-text notes
```

**Examples:**
```bash
# Validate
python -m auriga_data_factory promote dataset.json validated

# Human review
python -m auriga_data_factory promote dataset.json human_reviewed \
    --reviewer "Dr. A. Smith"

# Approve
python -m auriga_data_factory promote dataset.json approved \
    --approver "Prof. B. Jones" \
    --notes "Reviewed at lab meeting 2026-06-17."

# Archive
python -m auriga_data_factory promote dataset.json archived \
    --notes "Superseded by v2.0.0."
```

---

### `approve` — Full pipeline

Run the complete ingest → validate → human_review → approve pipeline in one step.

```bash
python -m auriga_data_factory approve <source> <name> \
    --reviewer REVIEWER \
    --approver APPROVER \
    [options]
```

**Example:**
```bash
python -m auriga_data_factory approve \
    experiments/aruco_lab_v1/ \
    "ArUco Lab Experiment v1" \
    --adapter auriga_fiducial \
    --reviewer "Dr. A. Smith" \
    --approver "Prof. B. Jones" \
    --notes "Approved for use in model training."
```

---

### `debt-register` — Export research debt

Export the research debt register as JSON and Markdown.

```bash
python -m auriga_data_factory debt-register
```

---

### `verify-integrity` — Check approved dataset

Verify that an approved dataset has not been modified since approval.

```bash
python -m auriga_data_factory verify-integrity <dataset_file>
```

**Exit codes:** `0` = integrity OK, `1` = checksum mismatch (tampering detected)

---

## Running Unit Tests

```bash
python -m pytest auriga_data_factory/tests/ -v
# or without pytest:
python -m unittest discover -s auriga_data_factory/tests -v
```
