"""
Auriga Data Factory — Command-Line Interface
=============================================
Provides a unified CLI for all Data Factory operations.

Usage::

    python -m auriga_data_factory.cli.main --help
    python -m auriga_data_factory.cli.main ingest --help

Commands:
    ingest              Import a dataset from CSV or directory.
    validate            Run the validation engine on a dataset file.
    analyse-coverage    Run coverage analysis on a dataset file.
    generate-synthetic  Generate synthetic samples.
    promote             Advance a dataset through the approval workflow.
    approve             Run the full automated pipeline: ingest → validate → review → approve.
    debt-register       Export the research debt register.
    verify-integrity    Check an approved dataset has not been modified.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from ..ingestion.engine import IngestionEngine
from ..validation.engine import ValidationEngine
from ..coverage.engine import CoverageEngine
from ..synthetic.generator import SyntheticGenerator
from ..approval.workflow import ApprovalWorkflow, ApprovalError
from ..reports.generator import ReportGenerator
from ..observability.research_debt import ResearchDebtRegister
from ..schema.canonical import CanonicalDataset


def _add_output_dir(parser: argparse.ArgumentParser) -> None:
    """Add the --output-dir option to a subcommand parser."""
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("auriga_output"),
        help="Base directory for all output files (default: auriga_output/).",
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="auriga-factory",
        description="Auriga Data Factory — research infrastructure CLI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Auriga Data Factory 1.0.0",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── ingest ──────────────────────────────────────────────────────── #
    p_ingest = sub.add_parser("ingest", help="Import a dataset.")
    p_ingest.add_argument("source", type=Path, help="CSV file or dataset directory.")
    p_ingest.add_argument("name", help="Human-readable dataset name.")
    p_ingest.add_argument(
        "--adapter",
        default="auriga_fiducial",
        choices=["csv", "auriga_fiducial", "legacy"],
        help="Ingestion adapter to use (default: auriga_fiducial).",
    )
    p_ingest.add_argument("--version", default="1.0.0", dest="dataset_version",
                          help="Dataset version string.")
    p_ingest.add_argument("--notes", default="", help="Free-text notes.")
    _add_output_dir(p_ingest)

    # ── validate ────────────────────────────────────────────────────── #
    p_val = sub.add_parser("validate", help="Validate a dataset JSON file.")
    p_val.add_argument("dataset_file", type=Path, help="Path to the dataset JSON file.")
    p_val.add_argument("--skip-images", action="store_true",
                       help="Skip image file existence checks.")
    _add_output_dir(p_val)

    # ── analyse-coverage ────────────────────────────────────────────── #
    p_cov = sub.add_parser("analyse-coverage", help="Analyse dataset coverage.")
    p_cov.add_argument("dataset_file", type=Path, help="Path to the dataset JSON file.")
    _add_output_dir(p_cov)

    # ── generate-synthetic ──────────────────────────────────────────── #
    p_syn = sub.add_parser("generate-synthetic",
                            help="Generate synthetic samples and save as dataset.")
    p_syn.add_argument("name", help="Name for the synthetic dataset.")
    p_syn.add_argument("--distances", nargs="+", type=float,
                       default=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
                       help="Distance values (metres) to generate.")
    p_syn.add_argument("--orientations", nargs="+",
                       default=["Down", "Up", "Left"],
                       help="Orientation labels.")
    p_syn.add_argument("--samples-per-cell", type=int, default=5,
                       help="Samples per (distance × orientation) cell.")
    p_syn.add_argument("--seed", type=int, default=None, help="Random seed.")
    _add_output_dir(p_syn)

    # ── promote ─────────────────────────────────────────────────────── #
    p_promo = sub.add_parser("promote", help="Promote a dataset through the approval workflow.")
    p_promo.add_argument("dataset_file", type=Path)
    p_promo.add_argument(
        "target_state",
        choices=["validated", "human_reviewed", "approved", "archived"],
    )
    p_promo.add_argument("--reviewer", default="", help="Reviewer name (for human_reviewed).")
    p_promo.add_argument("--approver", default="", help="Approver name (for approved).")
    p_promo.add_argument("--notes", default="")
    _add_output_dir(p_promo)

    # ── approve (full pipeline) ──────────────────────────────────────── #
    p_approve = sub.add_parser(
        "approve",
        help="Run the full pipeline: ingest → validate → human_review → approve.",
    )
    p_approve.add_argument("source", type=Path)
    p_approve.add_argument("name")
    p_approve.add_argument("--adapter", default="auriga_fiducial")
    p_approve.add_argument("--reviewer", required=True)
    p_approve.add_argument("--approver", required=True)
    p_approve.add_argument("--notes", default="")
    _add_output_dir(p_approve)

    # ── debt-register ───────────────────────────────────────────────── #
    p_debt = sub.add_parser("debt-register", help="Export the research debt register.")
    _add_output_dir(p_debt)

    # ── verify-integrity ────────────────────────────────────────────── #
    p_verify = sub.add_parser("verify-integrity",
                               help="Verify an approved dataset has not been modified.")
    p_verify.add_argument("dataset_file", type=Path)
    _add_output_dir(p_verify)

    return parser


# ─────────────────────────── Command handlers ────────────────────────────── #

def cmd_ingest(args: argparse.Namespace) -> int:
    """Handle the `ingest` command."""
    engine = IngestionEngine(
        output_dir=args.output_dir / "datasets",
        default_version=args.dataset_version,
    )
    reporter = ReportGenerator(output_dir=args.output_dir / "reports")

    print(f"Ingesting '{args.source}' as '{args.name}' using adapter '{args.adapter}'...")
    dataset = engine.ingest(
        source=args.source,
        name=args.name,
        adapter=args.adapter,
        version=args.dataset_version,
        notes=args.notes,
    )
    report_path = reporter.save_ingestion_report(dataset)
    print(f"✓ Ingested {dataset.sample_count} samples. State: {dataset.state}")
    print(f"  Report: {report_path}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle the `validate` command."""
    dataset = CanonicalDataset.load(args.dataset_file)
    engine = ValidationEngine(check_image_existence=not args.skip_images)
    reporter = ReportGenerator(output_dir=args.output_dir / "reports")

    print(f"Validating '{dataset.name}' v{dataset.version} ({dataset.sample_count} samples)...")
    report = engine.validate(dataset)

    paths = reporter.save_validation_report(report, dataset)
    print(report.as_text())
    print(f"\nReports saved:")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")

    return 0 if not report.failed else 1


def cmd_analyse_coverage(args: argparse.Namespace) -> int:
    """Handle the `analyse-coverage` command."""
    dataset = CanonicalDataset.load(args.dataset_file)
    engine = CoverageEngine()
    reporter = ReportGenerator(output_dir=args.output_dir / "reports")

    print(f"Analysing coverage for '{dataset.name}' v{dataset.version}...")
    report = engine.analyse(dataset)

    paths = reporter.save_coverage_report(report)
    print(report.as_text())
    print(f"\nReports saved:")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")

    return 0


def cmd_generate_synthetic(args: argparse.Namespace) -> int:
    """Handle the `generate-synthetic` command."""
    gen = SyntheticGenerator(seed=args.seed)
    engine = IngestionEngine(output_dir=args.output_dir / "datasets")

    samples = gen.generate_perspective_scaling(
        distances=args.distances,
        orientations=args.orientations,
        samples_per_cell=args.samples_per_cell,
    )

    from ..schema.canonical import CanonicalDataset, DatasetState
    dataset = CanonicalDataset(
        name=args.name,
        version="1.0.0",
        state=DatasetState.CANDIDATE.value,
        samples=samples,
        provenance={"generator": "SyntheticGenerator", "model": "perspective_scaling"},
        notes="Synthetically generated dataset.",
    )

    if engine.output_dir:
        engine._persist(dataset)

    reporter = ReportGenerator(output_dir=args.output_dir / "reports")
    reporter.save_ingestion_report(dataset)

    print(f"✓ Generated {len(samples)} synthetic samples for '{args.name}'.")
    print(f"  State: {dataset.state}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    """Handle the `promote` command."""
    dataset = CanonicalDataset.load(args.dataset_file)
    workflow = ApprovalWorkflow(
        approval_dir=args.output_dir / "approvals",
    )
    reporter = ReportGenerator(output_dir=args.output_dir / "reports")

    try:
        if args.target_state == "validated":
            dataset = workflow.promote_to_validated(dataset)
            val_report = dataset.provenance.get("validation_report")
            print(f"✓ Dataset promoted to VALIDATED.")
        elif args.target_state == "human_reviewed":
            if not args.reviewer:
                print("ERROR: --reviewer required for human_reviewed state.", file=sys.stderr)
                return 1
            dataset = workflow.promote_to_human_reviewed(dataset, args.reviewer, args.notes)
            print(f"✓ Dataset marked HUMAN_REVIEWED by '{args.reviewer}'.")
        elif args.target_state == "approved":
            if not args.approver:
                print("ERROR: --approver required for approved state.", file=sys.stderr)
                return 1
            dataset = workflow.promote_to_approved(dataset, args.approver, args.notes)
            print(f"✓ Dataset APPROVED by '{args.approver}'. Checksum: {dataset.checksum[:16]}…")
        elif args.target_state == "archived":
            dataset = workflow.archive(dataset, args.notes)
            print(f"✓ Dataset ARCHIVED.")
    except ApprovalError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Overwrite the dataset file with updated state.
    dataset.save(args.dataset_file)
    print(f"  Dataset saved: {args.dataset_file}")
    return 0


def cmd_approve_pipeline(args: argparse.Namespace) -> int:
    """Handle the `approve` full-pipeline command."""
    print(f"Running full approval pipeline for '{args.source}' → '{args.name}'...")

    engine = IngestionEngine(output_dir=args.output_dir / "datasets")
    workflow = ApprovalWorkflow(
        approval_dir=args.output_dir / "approvals",
    )
    reporter = ReportGenerator(output_dir=args.output_dir / "reports")

    # Step 1: Ingest.
    print("Step 1/4: Ingesting...")
    dataset = engine.ingest(source=args.source, name=args.name, adapter=args.adapter)
    reporter.save_ingestion_report(dataset)

    # Step 2: Validate.
    print("Step 2/4: Validating...")
    try:
        dataset = workflow.promote_to_validated(dataset)
    except ApprovalError as exc:
        val_rpt_data = dataset.provenance.get("validation_report", {})
        print(f"ERROR: Validation failed — {exc}", file=sys.stderr)
        return 1

    # Step 3: Human review.
    print(f"Step 3/4: Recording human review by '{args.reviewer}'...")
    dataset = workflow.promote_to_human_reviewed(dataset, args.reviewer, args.notes)

    # Step 4: Approve.
    print(f"Step 4/4: Approving by '{args.approver}'...")
    dataset = workflow.promote_to_approved(dataset, args.approver, args.notes)

    output_path = args.output_dir / "datasets" / f"{args.name.replace(' ', '_')}_APPROVED.json"
    dataset.save(output_path)

    reporter.save_architecture_compliance_report()
    reporter.save_human_validation_checklist()

    print(f"\n✓ Full pipeline complete.")
    print(f"  State      : {dataset.state}")
    print(f"  Checksum   : {dataset.checksum[:32]}…")
    print(f"  Dataset    : {output_path}")
    return 0


def cmd_debt_register(args: argparse.Namespace) -> int:
    """Handle the `debt-register` command."""
    register = ResearchDebtRegister()
    reporter = ReportGenerator(output_dir=args.output_dir / "reports")
    paths = reporter.save_research_debt_register(register)
    print(f"✓ Research debt register exported:")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")
    print(f"\n  {len(register.unresolved())} unresolved item(s).")
    return 0


def cmd_verify_integrity(args: argparse.Namespace) -> int:
    """Handle the `verify-integrity` command."""
    dataset = CanonicalDataset.load(args.dataset_file)
    workflow = ApprovalWorkflow()
    ok = workflow.verify_integrity(dataset)
    if ok:
        print(f"✓ Integrity OK: '{dataset.name}' v{dataset.version}")
    else:
        print(f"✗ INTEGRITY FAILURE: '{dataset.name}' v{dataset.version} — checksum mismatch!")
    return 0 if ok else 1


# ─────────────────────────── Entry point ─────────────────────────────────── #

def main(argv=None) -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dispatch = {
        "ingest":             cmd_ingest,
        "validate":           cmd_validate,
        "analyse-coverage":   cmd_analyse_coverage,
        "generate-synthetic": cmd_generate_synthetic,
        "promote":            cmd_promote,
        "approve":            cmd_approve_pipeline,
        "debt-register":      cmd_debt_register,
        "verify-integrity":   cmd_verify_integrity,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
