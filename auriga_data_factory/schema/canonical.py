"""
Auriga Data Factory — Canonical Dataset Schema
===============================================
Defines the versioned canonical representation for all Auriga datasets.

Design principles:
    - All required fields are explicit; optional fields use ``Optional``.
    - The schema is forward-compatible: new fields may be added with defaults
      without breaking existing serialised records.
    - ``SourceType`` distinguishes real from synthetic data (constitutional rule).
    - ``DatasetState`` governs the approval lifecycle.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─────────────────────────────── Enumerations ────────────────────────────── #

class SourceType(str, Enum):
    """Origin type of a sample — constitutional requirement to distinguish."""
    REAL = "real"
    SYNTHETIC = "synthetic"
    AUGMENTED = "augmented"  # real base + synthetic transform


class FiducialType(str, Enum):
    """Supported fiducial marker families."""
    ARUCO = "aruco"
    APRILTAG = "apriltag"
    QRCODE = "qrcode"
    OTHER = "other"


class DatasetState(str, Enum):
    """
    Lifecycle states for a :class:`CanonicalDataset`.

    Transitions (valid progressions):
        candidate → validated → human_reviewed → approved
        approved  → archived
        Any state → candidate  (version bump on modification)
    """
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    HUMAN_REVIEWED = "human_reviewed"
    APPROVED = "approved"
    ARCHIVED = "archived"


# ──────────────────────────────── Sample ─────────────────────────────────── #

@dataclass
class CanonicalSample:
    """
    One measurement record within a canonical dataset.

    All field names match the specification exactly. Fields marked Optional
    may be absent in legacy or synthetic records.

    Parameters
    ----------
    sample_id:
        Unique identifier for this sample within the dataset.
    filename:
        Basename of the associated image file.
    image_path:
        Absolute or dataset-relative path to the image file.
    fiducial_type:
        Fiducial marker family (see :class:`FiducialType`).
    object_name:
        Logical name of the fiducial object/target.
    distance_meters:
        Ground-truth distance from camera to marker (metres).
    orientation:
        Camera or marker orientation label, e.g. ``"Down"``, ``"Up"``,
        ``"Left"``, ``"Right"``, ``"Angled"``.
    camera_height_cm:
        Height of the camera above the surface (centimetres).
    device_model:
        Human-readable device model string (no unique IDs — constitutional rule).
    device_alias:
        Anonymous alias for the capture device (e.g. ``"DeviceA"``).
    marker_width_px:
        Detected marker width in pixels.
    marker_height_px:
        Detected marker height in pixels.
    marker_area_px:
        Detected marker area in pixels².
    center_x:
        X coordinate of the marker centre in the image (pixels).
    center_y:
        Y coordinate of the marker centre in the image (pixels).
    detection_success:
        Whether the fiducial was successfully detected.
    capture_timestamp:
        ISO-8601 UTC timestamp of image capture.
    source_type:
        Whether this sample is real, synthetic, or augmented.
    notes:
        Free-text annotations.
    schema_version:
        Version of the canonical schema used when this record was created.
    """

    # Required fields from specification
    sample_id: str
    filename: str
    image_path: str
    fiducial_type: str
    object_name: str
    distance_meters: float
    orientation: str
    camera_height_cm: float
    device_model: str
    device_alias: str
    marker_width_px: float
    marker_height_px: float
    marker_area_px: float
    center_x: float
    center_y: float
    detection_success: bool
    capture_timestamp: str
    source_type: str
    notes: str = ""

    # Versioning and provenance
    schema_version: str = "1.0.0"
    dataset_version: Optional[str] = None
    ingestion_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    provenance: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalise enum fields to string values for serialisation safety.
        if isinstance(self.source_type, SourceType):
            self.source_type = self.source_type.value
        if isinstance(self.fiducial_type, FiducialType):
            self.fiducial_type = self.fiducial_type.value

    @property
    def is_synthetic(self) -> bool:
        """Return True if this sample was synthetically generated."""
        return self.source_type in (SourceType.SYNTHETIC.value, SourceType.AUGMENTED.value)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanonicalSample":
        """Deserialise from a plain dictionary, ignoring unknown keys."""
        known_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def content_hash(self) -> str:
        """Return a SHA-256 hash of the sample's measurement fields."""
        payload = {
            "sample_id": self.sample_id,
            "filename": self.filename,
            "distance_meters": self.distance_meters,
            "orientation": self.orientation,
            "camera_height_cm": self.camera_height_cm,
            "marker_width_px": self.marker_width_px,
            "marker_height_px": self.marker_height_px,
            "center_x": self.center_x,
            "center_y": self.center_y,
        }
        raw = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()


# ──────────────────────────────── Dataset ────────────────────────────────── #

@dataclass
class CanonicalDataset:
    """
    A versioned collection of :class:`CanonicalSample` records with lifecycle
    state and provenance metadata.

    Parameters
    ----------
    dataset_id:
        Unique dataset identifier (UUID-based).
    name:
        Human-readable dataset name.
    version:
        Semantic version string, e.g. ``"1.0.0"``.
    state:
        Current lifecycle state (see :class:`DatasetState`).
    samples:
        List of canonical samples.
    provenance:
        Dictionary recording the origin, import parameters, and history.
    created_at:
        UTC timestamp of dataset creation.
    approved_by:
        Name or alias of the human who approved the dataset (if applicable).
    approved_at:
        UTC timestamp of approval (if applicable).
    checksum:
        SHA-256 checksum of the full dataset content (set at approval).
    """

    name: str
    version: str = "1.0.0"
    state: str = DatasetState.CANDIDATE.value
    samples: List[CanonicalSample] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    dataset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    checksum: Optional[str] = None
    schema_version: str = "1.0.0"
    notes: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.state, DatasetState):
            self.state = self.state.value

    # ------------------------------------------------------------------ #
    # Properties                                                            #
    # ------------------------------------------------------------------ #

    @property
    def sample_count(self) -> int:
        """Total number of samples in this dataset."""
        return len(self.samples)

    @property
    def real_sample_count(self) -> int:
        """Number of real (non-synthetic) samples."""
        return sum(1 for s in self.samples if not s.is_synthetic)

    @property
    def synthetic_sample_count(self) -> int:
        """Number of synthetic samples."""
        return sum(1 for s in self.samples if s.is_synthetic)

    @property
    def is_approved(self) -> bool:
        """Return True if the dataset is in the approved state."""
        return self.state == DatasetState.APPROVED.value

    # ------------------------------------------------------------------ #
    # Serialisation                                                         #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary (samples included)."""
        d = {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "version": self.version,
            "state": self.state,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "checksum": self.checksum,
            "notes": self.notes,
            "provenance": self.provenance,
            "sample_count": self.sample_count,
            "real_sample_count": self.real_sample_count,
            "synthetic_sample_count": self.synthetic_sample_count,
            "samples": [s.to_dict() for s in self.samples],
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CanonicalDataset":
        """Deserialise from a plain dictionary."""
        samples_raw = data.pop("samples", [])
        # Remove computed/read-only fields not in __init__
        for drop in ("sample_count", "real_sample_count", "synthetic_sample_count"):
            data.pop(drop, None)
        known_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in known_fields}
        dataset = cls(**filtered)
        dataset.samples = [CanonicalSample.from_dict(s) for s in samples_raw]
        return dataset

    def save(self, path: Path) -> None:
        """Write the dataset to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, default=str)

    @classmethod
    def load(cls, path: Path) -> "CanonicalDataset":
        """Load a dataset from a JSON file."""
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    # ------------------------------------------------------------------ #
    # Integrity                                                             #
    # ------------------------------------------------------------------ #

    def compute_checksum(self) -> str:
        """
        Compute a SHA-256 checksum over all sample content hashes.

        This checksum is stored at approval time and used to detect
        unauthorised post-approval modification.
        """
        sample_hashes = sorted(s.content_hash() for s in self.samples)
        combined = json.dumps(
            {
                "dataset_id": self.dataset_id,
                "version": self.version,
                "sample_hashes": sample_hashes,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha256(combined).hexdigest()

    def verify_checksum(self) -> bool:
        """
        Verify the stored checksum matches the current content.

        Returns False if the dataset has been modified after approval.
        """
        if self.checksum is None:
            return False
        return self.checksum == self.compute_checksum()
