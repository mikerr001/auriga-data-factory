"""
Unit tests — Approval Workflow
================================
Tests for the full approval lifecycle including constitutional guardrails.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ..schema.canonical import CanonicalDataset, DatasetState, SourceType, FiducialType
from ..schema.canonical import CanonicalSample
from ..approval.workflow import ApprovalWorkflow, ApprovalError
from ..validation.engine import ValidationEngine


def make_valid_dataset() -> CanonicalDataset:
    """
    Return a valid candidate dataset ready for the approval pipeline.

    Deliberately covers ≥3 distances and ≥3 samples per orientation so
    coverage_completeness returns at most a WARNING (not FAIL).
    The ValidationEngine used in ApprovalWorkflow is configured with
    min_samples_per_orientation=1 and min_distance_values=1 for unit tests.
    """
    samples = []
    distances = [1.0, 2.0, 3.0, 4.0, 5.0]
    orientations = ["Down", "Up", "Left", "Right", "Angled"]
    idx = 0
    for d in distances:
        for o in orientations:
            for k in range(3):
                px = max(5.0, 80.0 / d)
                samples.append(CanonicalSample(
                    sample_id=f"S-{idx:04d}",
                    filename=f"img{idx:04d}.jpg",
                    image_path="",
                    fiducial_type=FiducialType.ARUCO.value,
                    object_name="target",
                    distance_meters=d,
                    orientation=o,
                    camera_height_cm=120.0,
                    device_model="TestPhone",
                    device_alias="DeviceA",
                    marker_width_px=px,
                    marker_height_px=px,
                    marker_area_px=px * px,
                    center_x=960.0,
                    center_y=540.0,
                    detection_success=True,
                    capture_timestamp="2026-06-17T10:00:00+00:00",
                    source_type=SourceType.REAL.value,
                ))
                idx += 1
    return CanonicalDataset(name="Valid Dataset", samples=samples)


class TestApprovalWorkflow(unittest.TestCase):

    def setUp(self):
        self.workflow = ApprovalWorkflow(
            validation_engine=ValidationEngine(
                check_image_existence=False,
                min_samples_per_orientation=3,
                min_distance_values=3,
            )
        )

    # ── promote_to_validated ──────────────────────────────────────────── #

    def test_promote_to_validated_passes_clean_dataset(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        self.assertEqual(ds.state, DatasetState.VALIDATED.value)

    def test_promote_to_validated_blocked_if_not_candidate(self):
        ds = make_valid_dataset()
        ds.state = DatasetState.VALIDATED.value  # already validated
        with self.assertRaises(ApprovalError):
            self.workflow.promote_to_validated(ds)

    def test_promote_to_validated_blocked_on_validation_failure(self):
        ds = make_valid_dataset()
        # Introduce a fatal flaw.
        ds.samples[0].distance_meters = -999.0
        with self.assertRaises(ApprovalError):
            self.workflow.promote_to_validated(ds)

    # ── promote_to_human_reviewed ─────────────────────────────────────── #

    def test_promote_to_human_reviewed(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="Dr. Smith")
        self.assertEqual(ds.state, DatasetState.HUMAN_REVIEWED.value)
        self.assertEqual(ds.provenance["human_review"]["reviewer"], "Dr. Smith")

    def test_promote_to_human_reviewed_requires_reviewer_name(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        with self.assertRaises(ApprovalError):
            self.workflow.promote_to_human_reviewed(ds, reviewer="")

    def test_promote_to_human_reviewed_blocked_if_not_validated(self):
        ds = make_valid_dataset()  # still candidate
        with self.assertRaises(ApprovalError):
            self.workflow.promote_to_human_reviewed(ds, reviewer="Dr. Smith")

    # ── promote_to_approved ───────────────────────────────────────────── #

    def test_full_approval_pipeline(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="Dr. Smith")
        ds = self.workflow.promote_to_approved(ds, approved_by="Prof. Jones")
        self.assertEqual(ds.state, DatasetState.APPROVED.value)
        self.assertEqual(ds.approved_by, "Prof. Jones")
        self.assertIsNotNone(ds.checksum)

    def test_approved_dataset_checksum_is_valid(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="Reviewer")
        ds = self.workflow.promote_to_approved(ds, approved_by="Approver")
        self.assertTrue(ds.verify_checksum())

    def test_approval_requires_approver_name(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="Reviewer")
        with self.assertRaises(ApprovalError):
            self.workflow.promote_to_approved(ds, approved_by="")

    def test_approval_blocked_without_human_review(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        with self.assertRaises(ApprovalError):
            self.workflow.promote_to_approved(ds, approved_by="Approver")

    # ── Immutability / integrity ──────────────────────────────────────── #

    def test_integrity_passes_unmodified_dataset(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="R")
        ds = self.workflow.promote_to_approved(ds, approved_by="A")
        self.assertTrue(self.workflow.verify_integrity(ds))

    def test_integrity_fails_after_tampering(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="R")
        ds = self.workflow.promote_to_approved(ds, approved_by="A")
        # Simulate unauthorised modification.
        ds.samples[0].distance_meters = 999.0
        self.assertFalse(self.workflow.verify_integrity(ds))

    # ── Archive ───────────────────────────────────────────────────────── #

    def test_archive_approved_dataset(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="R")
        ds = self.workflow.promote_to_approved(ds, approved_by="A")
        ds = self.workflow.archive(ds, reason="No longer needed.")
        self.assertEqual(ds.state, DatasetState.ARCHIVED.value)

    def test_archive_blocked_if_not_approved(self):
        ds = make_valid_dataset()
        with self.assertRaises(ApprovalError):
            self.workflow.archive(ds)

    # ── create_new_version ────────────────────────────────────────────── #

    def test_create_new_version_from_approved(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="R")
        ds = self.workflow.promote_to_approved(ds, approved_by="A")
        new_ds = self.workflow.create_new_version(ds)
        self.assertEqual(new_ds.state, DatasetState.CANDIDATE.value)
        self.assertIsNone(new_ds.checksum)
        self.assertNotEqual(new_ds.version, ds.version)

    def test_create_new_version_does_not_modify_approved(self):
        ds = make_valid_dataset()
        ds = self.workflow.promote_to_validated(ds)
        ds = self.workflow.promote_to_human_reviewed(ds, reviewer="R")
        ds = self.workflow.promote_to_approved(ds, approved_by="A")
        original_checksum = ds.checksum
        _ = self.workflow.create_new_version(ds)
        # Original must be unchanged.
        self.assertEqual(ds.checksum, original_checksum)
        self.assertEqual(ds.state, DatasetState.APPROVED.value)

    def test_create_new_version_blocked_if_not_approved(self):
        ds = make_valid_dataset()
        with self.assertRaises(ApprovalError):
            self.workflow.create_new_version(ds)

    # ── Approval record persistence ───────────────────────────────────── #

    def test_approval_record_saved_to_disk(self):
        with TemporaryDirectory() as tmp:
            workflow = ApprovalWorkflow(
                validation_engine=ValidationEngine(check_image_existence=False),
                approval_dir=Path(tmp) / "approvals",
            )
            ds = make_valid_dataset()
            ds = workflow.promote_to_validated(ds)
            ds = workflow.promote_to_human_reviewed(ds, reviewer="R")
            ds = workflow.promote_to_approved(ds, approved_by="A")
            records = list((Path(tmp) / "approvals").glob("*.json"))
            self.assertEqual(len(records), 1)


if __name__ == "__main__":
    unittest.main()
