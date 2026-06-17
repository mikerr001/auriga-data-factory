"""
Auriga Data Factory — Export Pipeline
Packages approved datasets for downstream consumption.

See EXPORT_PIPELINE_GUIDE.md for full specification.

Constitutional rule: Only datasets with status='approved' may be exported.
"""

import csv
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExportPipeline:
    """
    Packages approved datasets into export bundles for downstream consumers.

    Export formats:
      - canonical_json: JSON metadata + images directory + manifest
      - csv:            CSV metadata only (no images)
      - colab_bundle:   Zip of CSV + JSON + images + starter notebook
    """

    def __init__(self, base_dir: str = ".", export_dir: str = "exports"):
        self.base_dir = base_dir
        self.export_dir = os.path.join(base_dir, export_dir)
        os.makedirs(self.export_dir, exist_ok=True)

    def _verify_approved(self, dataset_version: str) -> str:
        """Return path to approved dataset, raising if not approved."""
        from factory.versioning.version_manager import VersionManager
        vm = VersionManager(base_dir=self.base_dir)
        status = vm.get_status(dataset_version)
        if status not in ("approved", "distributed"):
            raise PermissionError(
                f"Cannot export dataset '{dataset_version}' with status '{status}'. "
                f"Only approved datasets may be exported. "
                f"See EXPORT_PIPELINE_GUIDE.md Section 2."
            )
        return os.path.join(self.base_dir, "datasets", "approved", dataset_version)

    def export_canonical_json(self, dataset_version: str) -> str:
        """Export as canonical JSON bundle (primary format)."""
        approved_path = self._verify_approved(dataset_version)
        bundle_dir = os.path.join(self.export_dir, f"{dataset_version}_bundle")

        if os.path.exists(bundle_dir):
            logger.warning(f"Export bundle already exists at {bundle_dir}. Skipping.")
            return bundle_dir

        shutil.copytree(approved_path, bundle_dir)
        self._write_release_notes(dataset_version, bundle_dir)

        # Write JSON version of metadata if only CSV exists
        csv_path = os.path.join(bundle_dir, "metadata.csv")
        json_path = os.path.join(bundle_dir, "metadata.json")
        if os.path.exists(csv_path) and not os.path.exists(json_path):
            self._csv_to_json(csv_path, json_path)

        logger.info(f"Canonical JSON bundle exported: {bundle_dir}")
        return bundle_dir

    def export_csv(self, dataset_version: str) -> str:
        """Export CSV metadata only (no images)."""
        approved_path = self._verify_approved(dataset_version)
        csv_dir = os.path.join(self.export_dir, f"{dataset_version}_csv")
        os.makedirs(csv_dir, exist_ok=True)

        src_csv = os.path.join(approved_path, "metadata.csv")
        if os.path.exists(src_csv):
            shutil.copy2(src_csv, os.path.join(csv_dir, "metadata.csv"))

        shutil.copy2(
            os.path.join(approved_path, "checksum_manifest.json"),
            os.path.join(csv_dir, "checksum_manifest.json"),
        )
        self._write_release_notes(dataset_version, csv_dir)

        logger.info(f"CSV export: {csv_dir}")
        return csv_dir

    def export_colab_bundle(self, dataset_version: str) -> str:
        """Export as a Colab-compatible zip bundle."""
        bundle_dir = self.export_canonical_json(dataset_version)
        starter_notebook = self._generate_starter_notebook(dataset_version)
        nb_path = os.path.join(bundle_dir, "starter_notebook.ipynb")
        with open(nb_path, "w") as f:
            json.dump(starter_notebook, f, indent=2)

        zip_path = os.path.join(self.export_dir, f"{dataset_version}_colab.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(bundle_dir):
                for fname in files:
                    full = os.path.join(root, fname)
                    arcname = os.path.relpath(full, bundle_dir)
                    zf.write(full, arcname)

        logger.info(f"Colab bundle exported: {zip_path}")
        return zip_path

    def _write_release_notes(self, dataset_version: str, dest_dir: str) -> None:
        notes = (
            f"# Release Notes — {dataset_version}\n\n"
            f"**Release date:** {datetime.now(timezone.utc).date().isoformat()}\n"
            f"**Produced by:** Auriga Data Factory v1.0.0\n\n"
            f"## How to cite\n\n"
            f"Project Auriga Data Factory, {dataset_version}. auriga-data-factory repository.\n\n"
            f"## Downstream consumer obligations\n\n"
            f"1. Record the dataset version this repository depends on.\n"
            f"2. Verify checksums before use.\n"
            f"3. Monitor for superseding versions.\n"
            f"4. Document your own known limitations relative to this dataset.\n"
        )
        with open(os.path.join(dest_dir, "RELEASE_NOTES.md"), "w") as f:
            f.write(notes)

    @staticmethod
    def _csv_to_json(csv_path: str, json_path: str) -> None:
        with open(csv_path, newline="", encoding="utf-8") as f:
            records = list(csv.DictReader(f))
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    @staticmethod
    def _generate_starter_notebook(dataset_version: str) -> Dict[str, Any]:
        """Generate a basic Colab notebook stub for the exported dataset."""
        return {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": [f"# Auriga Dataset: {dataset_version}\n\nStarter notebook."]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": [
                        "import pandas as pd\n",
                        f"df = pd.read_csv('metadata.csv')\n",
                        "print(f'Records: {len(df)}')\n",
                        "df.head()",
                    ]
                },
            ],
        }
