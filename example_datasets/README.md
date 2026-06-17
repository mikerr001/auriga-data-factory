# Example Datasets — Auriga Data Factory

This directory contains minimal example datasets that demonstrate the
Data Factory's ingestion, validation, and approval capabilities.

## Contents

| File/Directory | Description |
|----------------|-------------|
| `aruco_lab_experiment/` | Sample ArUco fiducial experiment (CSV + images stub) |
| `aruco_lab_experiment/metadata.csv` | CSV metadata file with 20 sample rows |
| `legacy_experiment.json` | Example legacy JSON experiment for `LegacyExperimentAdapter` |

## Usage

### Ingest the example ArUco dataset

```bash
python -m auriga_data_factory ingest \
    example_datasets/aruco_lab_experiment \
    "ArUco Lab Experiment 1" \
    --adapter auriga_fiducial \
    --output-dir auriga_output
```

### Validate the ingested dataset

```bash
python -m auriga_data_factory validate \
    auriga_output/datasets/ArUco_Lab_Experiment_1_v1.0.0_*.json \
    --skip-images \
    --output-dir auriga_output
```

### Analyse coverage

```bash
python -m auriga_data_factory analyse-coverage \
    auriga_output/datasets/ArUco_Lab_Experiment_1_v1.0.0_*.json \
    --output-dir auriga_output
```

### Generate synthetic samples

```bash
python -m auriga_data_factory generate-synthetic \
    "Synthetic Perspective Set 1" \
    --distances 0.5 1.0 1.5 2.0 2.5 3.0 \
    --orientations Down Up Left Right \
    --samples-per-cell 5 \
    --output-dir auriga_output
```

### Run the full approval pipeline

```bash
python -m auriga_data_factory approve \
    example_datasets/aruco_lab_experiment \
    "ArUco Lab Experiment 1" \
    --adapter auriga_fiducial \
    --reviewer "Dr. A. Smith" \
    --approver "Prof. B. Jones" \
    --output-dir auriga_output
```

### Export the research debt register

```bash
python -m auriga_data_factory debt-register --output-dir auriga_output
```
