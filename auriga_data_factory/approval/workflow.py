"""
Auriga Data Factory — Dataset Approval Workflow
================================================
Manages the lifecycle promotion of datasets through states:

    candidate → validated → human_reviewed → approved → archived

Constitutional rules enforced here:
    - Automated validation MUST pass before promotion past 'validated'.
    - Human sign-off MUST occur before transition to 'approved'.
    - Approved datasets MUST become immutable (checksum locked).
    - Any modification MUST produce a new version.
    - Approval MUST NEVER be bypassed.
    - Validation failures MUST NEVER be hidden.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..schema.canonical import CanonicalDataset, DatasetState
from ..schema.versioning import DatasetVersion
from ..validation.engine import ValidationEngine
from ..validation.results import ValidationStatus
from ..observability.logger import get_logger

logger = get_logger("auriga.approval.workflow")


class ApprovalError(Exception):
    """Raised when a dataset promotion violates workflow rules."""


# Valid state transitions.
_VALID_TRANSITIONS: Dict[str, set] = {
    DatasetState.CANDIDATE.value:      {DatasetState.VALIDATED.value},
    DatasetState.VALIDATED.value:      {DatasetState.HUMAN_REVIEWED.value},
    DatasetState.HUMAN_REVIEWED.value: {DatasetState.APPROVED.value},
    DatasetState.APPROVED.value:       {DatasetState.ARCHIVED.value},
    DatasetState.ARCHIVED.value:       set(),
}


class ApprovalWorkflow:
    """
    Orchestrates dataset state transitions with constitutional guardrails.

    Parameters
    ----------
    validation_engine:
        The :class:`ValidationEngine` instance to use for automated checks.
        If ``None``, a default instance (with image existence disabled) is used.
    approval_dir:
        Optional directory where approval records are persisted.
    """

    def __init__(
        self,
        validation_engine: Optional[ValidationEngine] = None,
        approval_dir: Optional[Path] = None,
    ) -> None:
        self._validation_engine = validation_engine or ValidationEngine(
            check_image_existence=False
        )
        self.approval_dir = Path(approval_dir) if approval_dir else None

    # ------------------------------------------------------------------ #
    # Promotion helpers                                                     #
    # ------------------------------------------------------------------ #

    def promote_to_validated(self, dataset: CanonicalDataset) -> CanonicalDataset:
        """
        Run automated validation and, if it passes, advance state to 'validated'.

        Parameters
        ----------
        dataset:
            Dataset in 'candidate' state.

        Returns
        -------
        CanonicalDataset
            The mutated dataset with state='validated'.

        Raises
        ------
        ApprovalError
            If the dataset is not in 'candidate' state, or validation fails.
        """
        self._assert_state(dataset, DatasetState.CANDIDATE)

        logger.promotion(
            f"Running automated validation for '{dataset.name}' v{dataset.version}.",
            dataset_id=dataset.dataset_id,
        )

        report = self._validation_engine.validate(dataset)

        if report.failed:
            # NEVER hide failures — always surface them.
            fail_messages = [
                r.message for r in report.results
                if r.status == ValidationStatus.FAIL
            ]
            raise ApprovalError(
                f"Automated validation FAILED for dataset '{dataset.name}'. "
                f"Promotion to 'validated' blocked. "
                f"Failures: {'; '.join(fail_messages)}"
            )

        dataset.state = DatasetState.VALIDATED.value
        dataset.provenance["validation_report"] = report.to_dict()

        logger.promotion(
            f"Dataset '{dataset.name}' promoted to VALIDATED "
            f"(warnings={report.warning_count}).",
            dataset_id=dataset.dataset_id,
            new_state=DatasetState.VALIDATED.value,
            warnings=report.warning_count,
        )
        return dataset

    def promote_to_human_reviewed(
        self,
        dataset: CanonicalDataset,
        reviewer: str,
        review_notes: str = "",
    ) -> CanonicalDataset:
        """
        Record a human review and advance state to 'human_reviewed'.

        Parameters
        ----------
        dataset:
            Dataset in 'validated' state.
        reviewer:
            Name or alias of the reviewer (no unique hardware IDs).
        review_notes:
            Free-text notes from the reviewer.

        Returns
        -------
        CanonicalDataset

        Raises
        ------
        ApprovalError
            If the dataset is not in 'validated' state.
        """
        self._assert_state(dataset, DatasetState.VALIDATED)

        if not reviewer.strip():
            raise ApprovalError("Reviewer name must not be empty.")

        dataset.state = DatasetState.HUMAN_REVIEWED.value
        dataset.provenance["human_review"] = {
            "reviewer": reviewer,
            "review_notes": review_notes,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.promotion(
            f"Dataset '{dataset.name}' marked HUMAN_REVIEWED by '{reviewer}'.",
            dataset_id=dataset.dataset_id,
            reviewer=reviewer,
            new_state=DatasetState.HUMAN_REVIEWED.value,
        )
        return dataset

    def promote_to_approved(
        self,
        dataset: CanonicalDataset,
        approved_by: str,
        approval_notes: str = "",
    ) -> CanonicalDataset:
        """
        Lock the dataset as approved and immutable.

        This method:
            1. Verifies the dataset is human-reviewed.
            2. Computes and stores the content checksum.
            3. Records the approver and timestamp.
            4. Persists an approval record if ``approval_dir`` is set.

        Constitutional rule: NEVER bypass this method to set state='approved'.

        Parameters
        ----------
        dataset:
            Dataset in 'human_reviewed' state.
        approved_by:
            Name or alias of the final approver.
        approval_notes:
            Free-text notes.

        Returns
        -------
        CanonicalDataset
            Immutably locked dataset.

        Raises
        ------
        ApprovalError
            If state is incorrect or approver is empty.
        """
        self._assert_state(dataset, DatasetState.HUMAN_REVIEWED)

        if not approved_by.strip():
            raise ApprovalError("Approver name must not be empty.")

        # Lock: compute and store checksum.
        dataset.checksum = dataset.compute_checksum()
        dataset.state = DatasetState.APPROVED.value
        dataset.approved_by = approved_by
        dataset.approved_at = datetime.now(timezone.utc).isoformat()
        dataset.provenance["approval"] = {
            "approved_by": approved_by,
            "approved_at": dataset.approved_at,
            "checksum": dataset.checksum,
            "approval_notes": approval_notes,
        }

        logger.promotion(
            f"Dataset '{dataset.name}' APPROVED by '{approved_by}'. "
            f"Checksum: {dataset.checksum[:16]}…",
            dataset_id=dataset.dataset_id,
            approved_by=approved_by,
            checksum=dataset.checksum,
            new_state=DatasetState.APPROVED.value,
        )

        if self.approval_dir:
            self._persist_approval_record(dataset, approval_notes)

        return dataset

    def archive(self, dataset: CanonicalDataset, reason: str = "") -> CanonicalDataset:
        """
        Archive an approved dataset.

        Parameters
        ----------
        dataset:
            Dataset in 'approved' state.
        reason:
            Human-readable reason for archival.

        Returns
        -------
        CanonicalDataset
        """
        self._assert_state(dataset, DatasetState.APPROVED)

        dataset.state = DatasetState.ARCHIVED.value
        dataset.provenance["archival"] = {
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        }

        logger.promotion(
            f"Dataset '{dataset.name}' ARCHIVED. Reason: {reason or 'unspecified'}.",
            dataset_id=dataset.dataset_id,
            new_state=DatasetState.ARCHIVED.value,
        )
        return dataset

    # ------------------------------------------------------------------ #
    # Modification (creates a new version)                                  #
    # ------------------------------------------------------------------ #

    def create_new_version(
        self,
        approved_dataset: CanonicalDataset,
        bump: str = "patch",
    ) -> CanonicalDataset:
        """
        Create a new mutable candidate dataset from an approved dataset.

        Constitutional rule:
            Any modification to an approved dataset MUST produce a new version.
            The original approved dataset is NOT modified.

        Parameters
        ----------
        approved_dataset:
            The approved (immutable) source dataset.
        bump:
            Version component to increment: ``'major'``, ``'minor'``, or ``'patch'``.

        Returns
        -------
        CanonicalDataset
            A new dataset in 'candidate' state with an incremented version.

        Raises
        ------
        ApprovalError
            If the source dataset is not approved.
        """
        if approved_dataset.state != DatasetState.APPROVED.value:
            raise ApprovalError(
                "create_new_version requires an approved dataset. "
                f"Got state: '{approved_dataset.state}'."
            )

        ver = DatasetVersion.from_string(approved_dataset.version)
        if bump == "major":
            new_ver = ver.bump_major()
        elif bump == "minor":
            new_ver = ver.bump_minor()
        else:
            new_ver = ver.bump_patch()

        new_dataset = CanonicalDataset.from_dict(
            copy.deepcopy(approved_dataset.to_dict())
        )
        new_dataset.state = DatasetState.CANDIDATE.value
        new_dataset.version = str(new_ver)
        new_dataset.checksum = None
        new_dataset.approved_by = None
        new_dataset.approved_at = None
        new_dataset.provenance["derived_from"] = {
            "parent_dataset_id": approved_dataset.dataset_id,
            "parent_version": approved_dataset.version,
            "derived_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.promotion(
            f"New version {new_ver} created from approved "
            f"'{approved_dataset.name}' v{approved_dataset.version}.",
            parent_id=approved_dataset.dataset_id,
            new_version=str(new_ver),
        )
        return new_dataset

    # ------------------------------------------------------------------ #
    # Integrity verification                                               #
    # ------------------------------------------------------------------ #

    def verify_integrity(self, dataset: CanonicalDataset) -> bool:
        """
        Verify that an approved dataset has not been tampered with.

        Returns True if the stored checksum matches the current content.
        Returns False if the checksum does not match or is missing.
        """
        if dataset.state != DatasetState.APPROVED.value:
            logger.warning(
                f"Integrity check on non-approved dataset '{dataset.name}' "
                f"(state={dataset.state}). Skipping."
            )
            return True  # Only approved datasets carry checksums.

        result = dataset.verify_checksum()
        if not result:
            logger.error(
                f"INTEGRITY FAILURE: Dataset '{dataset.name}' checksum mismatch! "
                "Dataset may have been modified after approval.",
                dataset_id=dataset.dataset_id,
            )
        else:
            logger.info(
                f"Integrity OK: '{dataset.name}' v{dataset.version}.",
                dataset_id=dataset.dataset_id,
            )
        return result

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _assert_state(dataset: CanonicalDataset, expected: DatasetState) -> None:
        """Raise ApprovalError if the dataset is not in the expected state."""
        if dataset.state != expected.value:
            raise ApprovalError(
                f"Expected dataset state '{expected.value}', "
                f"got '{dataset.state}' for dataset '{dataset.name}'."
            )

    def _persist_approval_record(
        self,
        dataset: CanonicalDataset,
        approval_notes: str,
    ) -> None:
        """Write an approval record JSON file to approval_dir."""
        if not self.approval_dir:
            return
        self.approval_dir.mkdir(parents=True, exist_ok=True)
        safe_name = dataset.name.replace(" ", "_").replace("/", "-")
        filename = f"approval_{safe_name}_v{dataset.version}_{dataset.dataset_id[:8]}.json"
        record = {
            "dataset_id": dataset.dataset_id,
            "dataset_name": dataset.name,
            "version": dataset.version,
            "state": dataset.state,
            "approved_by": dataset.approved_by,
            "approved_at": dataset.approved_at,
            "checksum": dataset.checksum,
            "approval_notes": approval_notes,
            "sample_count": dataset.sample_count,
        }
        path = self.approval_dir / filename
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=2)
        logger.promotion(
            f"Approval record persisted: {path}",
            dataset_id=dataset.dataset_id,
        )
