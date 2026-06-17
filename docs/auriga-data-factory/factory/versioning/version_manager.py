"""
Auriga Data Factory — Version Manager
Manages dataset lifecycle, promotion, immutability, and registry.

See DATA_VERSIONING_GUIDE.md for full specification.

IMPORTANT (from ADVERSARIAL_REVIEW.md ATTACK-004):
  Immutability here is a DETECTIVE control (checksum verification after the fact),
  NOT a preventive control (filesystem-level write locking).
  The checksum manifest detects tampering; it does not prevent it.
  See Research Debt RD-023 for future preventive immutability options.
"""

import hashlib
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VALID_STATES = {"raw", "staged", "validated", "candidate", "approved", "rejected", "distributed"}
VERSION_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z][a-z0-9]*)+_v\d+$")


class VersionManager:
    """
    Manages Auriga dataset versions across the full lifecycle.

    Registry file: registry/dataset_registry.json
    Approved datasets: datasets/approved/{version}/
    Rejected datasets: datasets/rejected/{version}/
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.registry_path = os.path.join(base_dir, "registry", "dataset_registry.json")
        self._ensure_registry()

    # ------------------------------------------------------------------
    # Registry management
    # ------------------------------------------------------------------

    def _ensure_registry(self) -> None:
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        if not os.path.exists(self.registry_path):
            with open(self.registry_path, "w") as f:
                json.dump({"datasets": []}, f, indent=2)

    def _load_registry(self) -> Dict[str, Any]:
        with open(self.registry_path, "r") as f:
            return json.load(f)

    def _save_registry(self, registry: Dict[str, Any]) -> None:
        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)

    def get_entry(self, dataset_version: str) -> Optional[Dict[str, Any]]:
        registry = self._load_registry()
        for entry in registry["datasets"]:
            if entry["datasetVersion"] == dataset_version:
                return entry
        return None

    def get_status(self, dataset_version: str) -> Optional[str]:
        entry = self.get_entry(dataset_version)
        return entry["status"] if entry else None

    def register(
        self,
        dataset_version: str,
        family: str,
        source_type: str,
        schema_version: str = "canonical_v1",
        supersedes: Optional[str] = None,
    ) -> None:
        """Register a new dataset version in the registry (raw state)."""
        if not VERSION_PATTERN.match(dataset_version):
            raise ValueError(
                f"Invalid version format: '{dataset_version}'. "
                f"Expected: {{family}}_{{subtype}}_v{{n}}"
            )

        if self.get_entry(dataset_version):
            raise ValueError(f"Dataset version '{dataset_version}' is already registered.")

        entry = {
            "datasetVersion": dataset_version,
            "family": family,
            "status": "raw",
            "sourceType": source_type,
            "schemaVersion": schema_version,
            "recordCount": None,
            "createdDate": datetime.now(timezone.utc).isoformat(),
            "validatedDate": None,
            "approvedDate": None,
            "approver": None,
            "approvalNotes": None,
            "checksum": None,
            "checksumAlgorithm": "sha256",
            "reportPath": None,
            "exportPath": None,
            "supersedes": supersedes,
            "supersededBy": None,
            "knownLimitations": [],
            "researchDebtItems": [],
            "distributedTo": [],
        }

        registry = self._load_registry()
        registry["datasets"].append(entry)
        self._save_registry(registry)

        # Mark superseded version
        if supersedes:
            self._mark_superseded(supersedes, dataset_version)

        logger.info(f"Registered dataset: {dataset_version}")

    def _mark_superseded(self, old_version: str, new_version: str) -> None:
        registry = self._load_registry()
        for entry in registry["datasets"]:
            if entry["datasetVersion"] == old_version:
                entry["supersededBy"] = new_version
                break
        self._save_registry(registry)

    def update_status(self, dataset_version: str, new_status: str) -> None:
        if new_status not in VALID_STATES:
            raise ValueError(f"Invalid status: '{new_status}'. Valid: {VALID_STATES}")

        entry = self.get_entry(dataset_version)
        if not entry:
            raise KeyError(f"Dataset '{dataset_version}' not found in registry.")

        if entry["status"] == "approved":
            raise PermissionError(
                f"Cannot change status of approved dataset '{dataset_version}'. "
                f"Approved datasets are immutable (DATA_VERSIONING_GUIDE.md P1)."
            )

        registry = self._load_registry()
        for e in registry["datasets"]:
            if e["datasetVersion"] == dataset_version:
                e["status"] = new_status
                if new_status == "validated":
                    e["validatedDate"] = datetime.now(timezone.utc).isoformat()
                break
        self._save_registry(registry)

    # ------------------------------------------------------------------
    # Approval and immutability
    # ------------------------------------------------------------------

    def promote_to_approved(
        self,
        dataset_version: str,
        staged_path: str,
        approval_record: Dict[str, Any],
        record_count: int,
        known_limitations: Optional[List[str]] = None,
        research_debt_items: Optional[List[str]] = None,
    ) -> str:
        """
        Promote a candidate dataset to approved (immutable) status.

        1. Copies dataset to datasets/approved/{version}/
        2. Generates SHA-256 checksum manifest
        3. Updates registry entry
        4. Returns the approved dataset path

        Note: Immutability is a detective control. See ADVERSARIAL_REVIEW.md ATTACK-004
              and Research Debt RD-023.
        """
        entry = self.get_entry(dataset_version)
        if not entry:
            raise KeyError(f"Dataset '{dataset_version}' not found in registry.")

        if entry["status"] not in ("candidate", "validated"):
            raise ValueError(
                f"Dataset '{dataset_version}' has status '{entry['status']}'. "
                f"Only 'candidate' or 'validated' datasets can be approved."
            )

        approved_path = os.path.join(self.base_dir, "datasets", "approved", dataset_version)

        if os.path.exists(approved_path):
            raise FileExistsError(
                f"Approved path already exists: {approved_path}. "
                f"This dataset version may already be approved."
            )

        # Copy dataset to approved/
        shutil.copytree(staged_path, approved_path)

        # Generate checksum manifest
        checksum_manifest = self._generate_checksum_manifest(approved_path, dataset_version)
        manifest_path = os.path.join(approved_path, "checksum_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(checksum_manifest, f, indent=2)

        overall_checksum = checksum_manifest["manifestChecksum"]

        # Update registry
        registry = self._load_registry()
        for e in registry["datasets"]:
            if e["datasetVersion"] == dataset_version:
                e["status"] = "approved"
                e["recordCount"] = record_count
                e["approvedDate"] = datetime.now(timezone.utc).isoformat()
                e["approver"] = approval_record.get("reviewer", "Project Lead")
                e["approvalNotes"] = approval_record.get("notes", "")
                e["checksum"] = overall_checksum
                e["knownLimitations"] = known_limitations or []
                e["researchDebtItems"] = research_debt_items or []
                break
        self._save_registry(registry)

        logger.info(
            f"Dataset '{dataset_version}' promoted to APPROVED. "
            f"Checksum: {overall_checksum}. Path: {approved_path}"
        )
        return approved_path

    def verify_integrity(self, dataset_version: str) -> bool:
        """
        Verify an approved dataset's files match stored checksums.

        Returns True if all checksums match.
        Logs mismatches but does not raise (returns False on failure).

        This is the detective immutability control (RD-023).
        """
        approved_path = os.path.join(self.base_dir, "datasets", "approved", dataset_version)
        manifest_path = os.path.join(approved_path, "checksum_manifest.json")

        if not os.path.exists(manifest_path):
            logger.error(f"No checksum manifest found at {manifest_path}")
            return False

        with open(manifest_path) as f:
            manifest = json.load(f)

        all_ok = True
        for rel_path, expected in manifest.get("files", {}).items():
            full_path = os.path.join(approved_path, rel_path)
            if not os.path.exists(full_path):
                logger.error(f"INTEGRITY FAIL: File missing: {full_path}")
                all_ok = False
                continue
            actual = "sha256:" + self._sha256_file(full_path)
            if actual != expected:
                logger.error(
                    f"INTEGRITY FAIL: Checksum mismatch for {rel_path}. "
                    f"Expected: {expected}. Got: {actual}."
                )
                all_ok = False

        if all_ok:
            logger.info(f"Integrity verified: {dataset_version}")
        return all_ok

    def register_distribution(
        self,
        dataset_version: str,
        requesting_repository: str,
        distribution_date: str,
        purpose: str,
        export_format: str,
    ) -> None:
        """Record that a dataset was distributed to a downstream consumer."""
        registry = self._load_registry()
        for entry in registry["datasets"]:
            if entry["datasetVersion"] == dataset_version:
                entry["distributedTo"].append({
                    "repository": requesting_repository,
                    "distributedDate": distribution_date,
                    "purpose": purpose,
                    "exportFormat": export_format,
                })
                entry["status"] = "distributed"
                break
        self._save_registry(registry)
        logger.info(f"Recorded distribution of '{dataset_version}' to '{requesting_repository}'.")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _generate_checksum_manifest(
        self, approved_path: str, dataset_version: str
    ) -> Dict[str, Any]:
        file_checksums = {}
        for root, _, files in sorted(os.walk(approved_path)):
            for fname in sorted(files):
                if fname == "checksum_manifest.json":
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, approved_path)
                file_checksums[rel_path] = "sha256:" + self._sha256_file(full_path)

        manifest = {
            "datasetVersion": dataset_version,
            "algorithm": "sha256",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "files": file_checksums,
        }

        manifest_str = json.dumps(manifest, sort_keys=True)
        manifest["manifestChecksum"] = (
            "sha256:" + hashlib.sha256(manifest_str.encode()).hexdigest()
        )
        return manifest

    @staticmethod
    def _sha256_file(path: str) -> str:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def list_approved(self) -> List[Dict[str, Any]]:
        registry = self._load_registry()
        return [e for e in registry["datasets"] if e["status"] in ("approved", "distributed")]
