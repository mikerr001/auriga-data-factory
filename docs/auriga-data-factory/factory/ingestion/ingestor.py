"""
Auriga Data Factory — Base Ingestor
Abstract interface for all ingestion strategies.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result produced by any ingestor implementation."""
    dataset_version: str
    record_count: int
    staged_path: str
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    session_hash: Optional[str] = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def save_staged(self, output_dir: str) -> None:
        """Write staged dataset to output_dir/{dataset_version}/."""
        raise NotImplementedError("Subclasses must implement save_staged.")

    def summary(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"Ingestion {status} | "
            f"version={self.dataset_version} | "
            f"records={self.record_count} | "
            f"warnings={len(self.warnings)} | "
            f"errors={len(self.errors)}"
        )


class BaseIngestor(ABC):
    """
    Abstract base class for all Auriga Data Factory ingestors.

    Implementations must accept raw data from a specific source format
    and normalize it to the Auriga Canonical Schema (canonical_v1).

    Constitutional constraints enforced by all ingestors:
      - Never invent data to fill gaps (null > fabricated values).
      - Never store unique hardware identifiers.
      - Never discard original files.
      - Always generate UUID v4 recordId at ingestion time.
    """

    SCHEMA_VERSION = "canonical_v1"

    @abstractmethod
    def ingest(self, raw_path: str, dataset_version: str) -> IngestionResult:
        """
        Ingest raw data from raw_path and normalize to canonical schema.

        Args:
            raw_path: Directory containing raw data files (CSV, images, notes).
            dataset_version: Version identifier (e.g., 'fiducials_aruco_v3').

        Returns:
            IngestionResult with staged records and any warnings/errors.
        """
        raise NotImplementedError

    def _validate_version_format(self, version: str) -> bool:
        """
        Verify that the dataset version string matches the expected format:
        {family}_{subtype}_v{n}
        Examples: fiducials_aruco_v1, perspective_hallway_v2
        """
        import re
        pattern = r"^[a-z][a-z0-9]*(_[a-z][a-z0-9]*)+_v\d+$"
        return bool(re.match(pattern, version))

    def _compute_session_hash(self, raw_path: str) -> str:
        """
        Compute a SHA-256 hash of the raw session directory contents.
        Used to detect accidental double-ingestion (RD-022).
        """
        import hashlib
        import os

        sha = hashlib.sha256()
        for root, _, files in sorted(os.walk(raw_path)):
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "rb") as f:
                        sha.update(f.read())
                except (OSError, IOError) as e:
                    logger.warning(f"Could not hash file {fpath}: {e}")
        return sha.hexdigest()
