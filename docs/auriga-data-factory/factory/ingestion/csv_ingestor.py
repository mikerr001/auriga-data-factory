"""
Auriga Data Factory — CSV Ingestor
Ingests CSV metadata + image files into the Auriga Canonical Schema.

Primary MVP ingestor. Handles:
  - Auriga canonical CSV format
  - Legacy browser-based collector format (with field mapping)

See DATA_INGESTION_GUIDE.md for collection protocol and CSV field definitions.
"""

import csv
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .ingestor import BaseIngestor, IngestionResult
from .normalizer import Normalizer

logger = logging.getLogger(__name__)

# Fields that must be present in every ingested record.
REQUIRED_FIELDS = [
    "datasetVersion",
    "sourceType",
    "captureTimestamp",
    "filename",
    "imagePath",
    "fiducialType",
    "distanceMeters",
    "orientation",
    "cameraHeightCm",
    "deviceModel",
    "deviceAlias",
    "detectionSuccess",
]

# Fields explicitly prohibited by Auriga constitutional rules.
PROHIBITED_FIELDS = [
    "deviceSerialNumber",
    "imei",
    "androidId",
    "macAddress",
    "hardwareFingerprint",
    "collectorName",
    "collectorEmail",
    "collectorPhone",
    "subjectName",
    "gpsCoordinates",
    "homeAddress",
]

# Legacy browser-collector column → canonical field mapping.
LEGACY_COLUMN_MAP = {
    "width": "markerWidthPx",
    "height": "markerHeightPx",
    "area": "markerAreaPx",
    "detected": "detectionSuccess",
    "distance": "distanceMeters",
    "camera_height": "cameraHeightCm",
    "device": "deviceModel",
    "timestamp": "captureTimestamp",
}


class CsvIngestor(BaseIngestor):
    """
    Ingestor for CSV metadata + image directory bundles.

    Expected raw_path structure:
        {raw_path}/
        ├── metadata.csv
        ├── images/
        │   └── *.jpg / *.png
        ├── collection_notes.md   (optional)
        └── device_record.md      (optional)
    """

    def __init__(self, legacy_mode: bool = False):
        """
        Args:
            legacy_mode: If True, applies legacy browser-collector field mapping
                         before canonical normalization.
        """
        self.legacy_mode = legacy_mode
        self.normalizer = Normalizer()

    def ingest(self, raw_path: str, dataset_version: str) -> IngestionResult:
        """
        Ingest a CSV + images directory into canonical schema records.

        Returns an IngestionResult. Call result.save_staged() to persist.
        """
        warnings: List[str] = []
        errors: List[str] = []

        # --- Version format check ---
        if not self._validate_version_format(dataset_version):
            errors.append(
                f"Invalid dataset version format: '{dataset_version}'. "
                f"Expected format: {{family}}_{{subtype}}_v{{n}} "
                f"(e.g., fiducials_aruco_v3)."
            )
            return IngestionResult(
                dataset_version=dataset_version,
                record_count=0,
                staged_path="",
                warnings=warnings,
                errors=errors,
            )

        # --- Session hash (RD-022: detect double-ingestion) ---
        session_hash = self._compute_session_hash(raw_path)
        logger.info(f"Session hash for {raw_path}: {session_hash}")

        # --- Locate metadata CSV ---
        csv_path = os.path.join(raw_path, "metadata.csv")
        if not os.path.exists(csv_path):
            errors.append(f"metadata.csv not found in {raw_path}.")
            return IngestionResult(
                dataset_version=dataset_version,
                record_count=0,
                staged_path="",
                warnings=warnings,
                errors=errors,
                session_hash=session_hash,
            )

        # --- Read CSV rows ---
        raw_rows: List[Dict[str, Any]] = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_rows.append(dict(row))

        if not raw_rows:
            errors.append("metadata.csv contains no data rows.")
            return IngestionResult(
                dataset_version=dataset_version,
                record_count=0,
                staged_path="",
                warnings=warnings,
                errors=errors,
                session_hash=session_hash,
            )

        # --- Apply legacy mapping if needed ---
        if self.legacy_mode:
            raw_rows, legacy_warns = self._apply_legacy_mapping(raw_rows)
            warnings.extend(legacy_warns)

        # --- Detect prohibited fields ---
        all_columns = set(raw_rows[0].keys()) if raw_rows else set()
        found_prohibited = all_columns.intersection(PROHIBITED_FIELDS)
        if found_prohibited:
            errors.append(
                f"Prohibited fields found in CSV: {sorted(found_prohibited)}. "
                f"See CONSTITUTION.md rules P-2 through P-5. "
                f"Remove these fields before ingestion."
            )

        # --- Detect unknown fields (warn, do not drop) ---
        known_fields = set(REQUIRED_FIELDS) | {
            "markerWidthPx", "markerHeightPx", "markerAreaPx",
            "centerX", "centerY", "markerPhysicalSizeMm",
            "bearingDegrees", "pitchDegrees", "yawDegrees",
            "lightingCondition", "environmentType",
            "syntheticParameters", "notes", "markerId",
        }
        unknown_fields = all_columns - known_fields - {"recordId"}
        if unknown_fields:
            warnings.append(
                f"Unknown fields detected (retained, not dropped): "
                f"{sorted(unknown_fields)}. "
                f"If these are new canonical fields, update DATASET_SPECIFICATIONS.md."
            )

        if errors:
            return IngestionResult(
                dataset_version=dataset_version,
                record_count=0,
                staged_path="",
                warnings=warnings,
                errors=errors,
                session_hash=session_hash,
            )

        # --- Normalize each row ---
        normalized: List[Dict[str, Any]] = []
        for i, row in enumerate(raw_rows):
            record, row_warns, row_errors = self.normalizer.normalize_row(
                row=row,
                dataset_version=dataset_version,
                row_index=i,
            )
            warnings.extend(row_warns)
            errors.extend(row_errors)
            normalized.append(record)

        staged_path = f"datasets/staged/{dataset_version}/"

        result = IngestionResult(
            dataset_version=dataset_version,
            record_count=len(normalized),
            staged_path=staged_path,
            warnings=warnings,
            errors=errors,
            session_hash=session_hash,
        )
        # Attach normalized records for downstream use
        result._records = normalized  # type: ignore[attr-defined]

        logger.info(result.summary())
        return result

    def _apply_legacy_mapping(
        self, rows: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        Remap legacy browser-collector column names to canonical field names.
        Returns (remapped_rows, warnings).
        """
        warns: List[str] = []
        remapped = []
        applied_mappings = set()

        for row in rows:
            new_row = {}
            for key, value in row.items():
                canonical_key = LEGACY_COLUMN_MAP.get(key, key)
                if canonical_key != key:
                    applied_mappings.add(f"{key} → {canonical_key}")
                new_row[canonical_key] = value
            remapped.append(new_row)

        if applied_mappings:
            warns.append(
                f"Legacy field mappings applied: {sorted(applied_mappings)}. "
                f"Verify these mappings against DATA_INGESTION_GUIDE.md Section 7.2."
            )

        return remapped, warns
