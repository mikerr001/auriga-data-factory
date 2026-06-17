"""
Auriga Data Factory — Ingestion Adapters
=========================================
Pluggable adapter interfaces for importing heterogeneous dataset formats
into the canonical representation.

Supported adapters:
    - :class:`CSVAdapter`:            CSV metadata + image directory.
    - :class:`AurigaFiducialAdapter`: Existing Auriga fiducial experiment format.
    - :class:`LegacyExperimentAdapter`: Legacy experimental datasets.

New adapters must subclass :class:`BaseAdapter` and implement ``ingest()``.
"""

from __future__ import annotations

import csv
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..schema.canonical import CanonicalSample, SourceType, FiducialType
from ..observability.logger import get_logger

logger = get_logger("auriga.ingestion.adapters")


# ─────────────────────────────── Base adapter ────────────────────────────── #

class BaseAdapter(ABC):
    """
    Abstract base class for all ingestion adapters.

    Subclasses implement :meth:`ingest` to produce a list of
    :class:`CanonicalSample` objects and a provenance dictionary.
    """

    @abstractmethod
    def ingest(self, source: Path, **kwargs: Any) -> Tuple[List[CanonicalSample], Dict[str, Any]]:
        """
        Import data from ``source`` and return canonical samples + provenance.

        Parameters
        ----------
        source:
            Path to the dataset root (directory or single file).
        **kwargs:
            Adapter-specific options.

        Returns
        -------
        samples:
            List of :class:`CanonicalSample` objects.
        provenance:
            Dictionary describing origin, import parameters, and any warnings.
        """

    @staticmethod
    def _make_sample_id(prefix: str = "S") -> str:
        """Generate a unique sample ID."""
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────── CSV adapter ─────────────────────────────── #

# Expected column name aliases: maps canonical field → list of accepted CSV headers.
_CSV_COLUMN_MAP: Dict[str, List[str]] = {
    "sample_id":        ["sample_id", "sampleID", "id"],
    "filename":         ["filename", "file_name", "image_filename"],
    "image_path":       ["image_path", "imagePath", "path"],
    "fiducial_type":    ["fiducial_type", "fiducialType", "marker_type"],
    "object_name":      ["object_name", "objectName", "target"],
    "distance_meters":  ["distance_meters", "distanceMeters", "distance_m", "distance"],
    "orientation":      ["orientation", "camera_orientation"],
    "camera_height_cm": ["camera_height_cm", "cameraHeightCm", "height_cm"],
    "device_model":     ["device_model", "deviceModel", "device"],
    "device_alias":     ["device_alias", "deviceAlias", "alias"],
    "marker_width_px":  ["marker_width_px", "markerWidthPx", "width_px"],
    "marker_height_px": ["marker_height_px", "markerHeightPx", "height_px"],
    "marker_area_px":   ["marker_area_px", "markerAreaPx", "area_px"],
    "center_x":         ["center_x", "centerX", "cx"],
    "center_y":         ["center_y", "centerY", "cy"],
    "detection_success":["detection_success", "detectionSuccess", "detected"],
    "capture_timestamp":["capture_timestamp", "captureTimestamp", "timestamp"],
    "source_type":      ["source_type", "sourceType"],
    "notes":            ["notes", "comment", "comments"],
}


def _resolve_column(row: Dict[str, str], canonical_field: str) -> Optional[str]:
    """Return the first matching value from a CSV row for a canonical field."""
    for alias in _CSV_COLUMN_MAP.get(canonical_field, [canonical_field]):
        if alias in row:
            return row[alias]
    return None


class CSVAdapter(BaseAdapter):
    """
    Import a dataset from a CSV metadata file and an optional image directory.

    The CSV may use any of the column name aliases defined in ``_CSV_COLUMN_MAP``.
    Missing optional fields are filled with sensible defaults.

    Parameters
    ----------
    image_dir:
        Directory containing image files. If ``None``, image presence
        will not be verified.
    dataset_version:
        Version string to attach to all imported samples.
    """

    def __init__(
        self,
        image_dir: Optional[Path] = None,
        dataset_version: str = "1.0.0",
    ) -> None:
        self.image_dir = Path(image_dir) if image_dir else None
        self.dataset_version = dataset_version

    def ingest(
        self,
        source: Path,
        **kwargs: Any,
    ) -> Tuple[List[CanonicalSample], Dict[str, Any]]:
        """
        Import samples from a CSV file.

        Parameters
        ----------
        source:
            Path to the CSV metadata file.
        """
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"CSV source file not found: {source}")

        samples: List[CanonicalSample] = []
        warnings: List[str] = []
        skipped: int = 0

        logger.ingestion(f"Starting CSV import from: {source}")

        with open(source, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row_num, row in enumerate(reader, start=2):  # row 1 = header
                try:
                    sample = self._parse_row(row, row_num)
                    samples.append(sample)
                except (ValueError, KeyError) as exc:
                    msg = f"Row {row_num}: skipped — {exc}"
                    warnings.append(msg)
                    logger.warning(msg, row=row_num)
                    skipped += 1

        logger.ingestion(
            f"CSV import complete: {len(samples)} samples imported, {skipped} skipped.",
            source=str(source),
        )

        provenance = {
            "adapter": "CSVAdapter",
            "source_file": str(source),
            "image_dir": str(self.image_dir) if self.image_dir else None,
            "import_timestamp": self._now_iso(),
            "rows_imported": len(samples),
            "rows_skipped": skipped,
            "warnings": warnings,
        }
        return samples, provenance

    def _parse_row(self, row: Dict[str, str], row_num: int) -> CanonicalSample:
        """Parse one CSV row into a :class:`CanonicalSample`."""

        def get(field: str, default: Any = None) -> Optional[str]:
            val = _resolve_column(row, field)
            return val.strip() if val and val.strip() else default

        def get_float(field: str, default: float = 0.0) -> float:
            val = get(field)
            if val is None:
                return default
            try:
                return float(val)
            except ValueError:
                return default

        def get_bool(field: str, default: bool = False) -> bool:
            val = get(field, "").lower()
            return val in ("true", "1", "yes", "success")

        sample_id = get("sample_id") or self._make_sample_id()
        filename = get("filename", "")
        image_path = get("image_path", "")

        # Resolve image path relative to image_dir if available.
        if self.image_dir and filename:
            candidate = self.image_dir / filename
            if candidate.exists():
                image_path = str(candidate)

        source_type_raw = get("source_type", SourceType.REAL.value)

        return CanonicalSample(
            sample_id=sample_id,
            filename=filename,
            image_path=image_path,
            fiducial_type=get("fiducial_type", FiducialType.ARUCO.value),
            object_name=get("object_name", "unknown"),
            distance_meters=get_float("distance_meters"),
            orientation=get("orientation", "unknown"),
            camera_height_cm=get_float("camera_height_cm"),
            device_model=get("device_model", "unknown"),
            device_alias=get("device_alias", "unknown"),
            marker_width_px=get_float("marker_width_px"),
            marker_height_px=get_float("marker_height_px"),
            marker_area_px=get_float("marker_area_px"),
            center_x=get_float("center_x"),
            center_y=get_float("center_y"),
            detection_success=get_bool("detection_success"),
            capture_timestamp=get("capture_timestamp", self._now_iso()),
            source_type=source_type_raw,
            notes=get("notes", ""),
            dataset_version=self.dataset_version,
            provenance={"csv_row": row_num},
        )


# ─────────────────────────── Auriga fiducial adapter ─────────────────────── #

class AurigaFiducialAdapter(BaseAdapter):
    """
    Import an existing Auriga fiducial experiment dataset.

    Expects either:
    * A single CSV file (delegates to :class:`CSVAdapter`), or
    * A directory containing ``metadata.csv`` and an ``images/`` subdirectory.

    Parameters
    ----------
    dataset_version:
        Version string to attach to all imported samples.
    """

    def __init__(self, dataset_version: str = "1.0.0") -> None:
        self.dataset_version = dataset_version

    def ingest(
        self,
        source: Path,
        **kwargs: Any,
    ) -> Tuple[List[CanonicalSample], Dict[str, Any]]:
        """
        Import an Auriga fiducial experiment from a directory or CSV file.
        """
        source = Path(source)
        logger.ingestion(f"AurigaFiducialAdapter: ingesting from {source}")

        if source.is_file() and source.suffix.lower() == ".csv":
            csv_path = source
            image_dir = source.parent / "images"
        elif source.is_dir():
            # Look for metadata.csv or any CSV file.
            csv_candidates = list(source.glob("*.csv"))
            if not csv_candidates:
                raise FileNotFoundError(
                    f"No CSV metadata file found in directory: {source}"
                )
            csv_path = csv_candidates[0]
            image_dir = source / "images"
        else:
            raise ValueError(f"Source must be a CSV file or directory: {source}")

        image_dir = image_dir if image_dir.exists() else None

        adapter = CSVAdapter(
            image_dir=image_dir,
            dataset_version=self.dataset_version,
        )
        samples, prov = adapter.ingest(csv_path, **kwargs)

        prov["adapter"] = "AurigaFiducialAdapter"
        prov["original_source"] = str(source)
        return samples, prov


# ─────────────────────────── Legacy experiment adapter ───────────────────── #

class LegacyExperimentAdapter(BaseAdapter):
    """
    Import a legacy Auriga experimental dataset stored as a JSON file.

    This adapter handles older JSON schemas and translates them to the
    canonical representation, preserving provenance of the original format.
    """

    def ingest(
        self,
        source: Path,
        **kwargs: Any,
    ) -> Tuple[List[CanonicalSample], Dict[str, Any]]:
        """Import samples from a legacy JSON experiment file."""
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Legacy JSON source not found: {source}")

        logger.ingestion(f"LegacyExperimentAdapter: ingesting from {source}")

        with open(source, encoding="utf-8") as fh:
            data = json.load(fh)

        samples: List[CanonicalSample] = []
        raw_samples = data.get("samples", data.get("records", []))

        for idx, raw in enumerate(raw_samples):
            sample = CanonicalSample(
                sample_id=raw.get("id", self._make_sample_id("L")),
                filename=raw.get("filename", raw.get("image", "")),
                image_path=raw.get("image_path", raw.get("path", "")),
                fiducial_type=raw.get("fiducial_type", FiducialType.ARUCO.value),
                object_name=raw.get("object_name", raw.get("target", "unknown")),
                distance_meters=float(raw.get("distance", raw.get("distance_meters", 0.0))),
                orientation=raw.get("orientation", "unknown"),
                camera_height_cm=float(raw.get("height_cm", raw.get("camera_height_cm", 0.0))),
                device_model=raw.get("device", raw.get("device_model", "unknown")),
                device_alias=raw.get("alias", raw.get("device_alias", "DeviceUnknown")),
                marker_width_px=float(raw.get("width_px", raw.get("marker_width_px", 0.0))),
                marker_height_px=float(raw.get("height_px", raw.get("marker_height_px", 0.0))),
                marker_area_px=float(raw.get("area_px", raw.get("marker_area_px", 0.0))),
                center_x=float(raw.get("cx", raw.get("center_x", 0.0))),
                center_y=float(raw.get("cy", raw.get("center_y", 0.0))),
                detection_success=bool(raw.get("detected", raw.get("detection_success", False))),
                capture_timestamp=raw.get("timestamp", raw.get("capture_timestamp", self._now_iso())),
                source_type=raw.get("source_type", SourceType.REAL.value),
                notes=raw.get("notes", "Imported from legacy format."),
                dataset_version=self.dataset_version if hasattr(self, 'dataset_version') else "1.0.0",
                provenance={"legacy_index": idx, "legacy_source": str(source)},
            )
            samples.append(sample)

        provenance = {
            "adapter": "LegacyExperimentAdapter",
            "source_file": str(source),
            "import_timestamp": self._now_iso(),
            "rows_imported": len(samples),
            "original_schema": data.get("schema_version", "unknown"),
        }
        return samples, provenance
