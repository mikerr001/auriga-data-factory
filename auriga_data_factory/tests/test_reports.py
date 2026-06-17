"""
Unit tests — Reports module
=============================
Tests for the report generator (JSON, Markdown, and text outputs).
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ..schema.canonical import CanonicalDataset, CanonicalSample, SourceType, FiducialType
from ..validation.engine import ValidationEngine
from ..coverage.engine import CoverageEngine
from ..reports.generator import ReportGenerator
from ..observability.research_debt import ResearchDebtRegister


def _make_minimal_dataset() -> CanonicalDataset:
    samples = [
        CanonicalSample(
            sample_id=f"S-{i:03d}",
            filename=f"img{i:03d}.jpg",
            image_path="",
            fiducial_type=FiducialType.ARUCO.value,
            object_name="target",
            distance_meters=float(i + 1),
            orientation="Down",
            camera_height_cm=120.0,
            device_model="TestPhone",
            device_alias="DeviceA",
            marker_width_px=80.0,
            marker_height_px=80.0,
            marker_area_px=6400.0,
            center_x=960.0,
            center_y=540.0,
            detection_success=True,
            capture_timestamp="2026-06-17T10:00:00+00:00",
            source_type=SourceType.REAL.value,
        )
        for i in range(5)
    ]
    return CanonicalDataset(name="Report Test Dataset", samples=samples)


class TestReportGenerator(unittest.TestCase):

    def test_save_validation_report_creates_files(self):
        with TemporaryDirectory() as tmp:
            ds = _make_minimal_dataset()
            engine = ValidationEngine(check_image_existence=False)
            report = engine.validate(ds)
            generator = ReportGenerator(output_dir=Path(tmp))
            paths = generator.save_validation_report(report, ds)
            for fmt in ("json", "markdown", "text"):
                self.assertIn(fmt, paths)
                self.assertTrue(paths[fmt].exists())

    def test_validation_json_is_valid(self):
        with TemporaryDirectory() as tmp:
            ds = _make_minimal_dataset()
            engine = ValidationEngine(check_image_existence=False)
            report = engine.validate(ds)
            generator = ReportGenerator(output_dir=Path(tmp))
            paths = generator.save_validation_report(report, ds)
            with open(paths["json"]) as fh:
                data = json.load(fh)
            self.assertIn("overall_status", data)
            self.assertIn("results", data)

    def test_save_coverage_report_creates_files(self):
        with TemporaryDirectory() as tmp:
            ds = _make_minimal_dataset()
            engine = CoverageEngine()
            report = engine.analyse(ds)
            generator = ReportGenerator(output_dir=Path(tmp))
            paths = generator.save_coverage_report(report)
            for fmt in ("json", "markdown", "text"):
                self.assertIn(fmt, paths)
                self.assertTrue(paths[fmt].exists())

    def test_save_research_debt_register_creates_files(self):
        with TemporaryDirectory() as tmp:
            register = ResearchDebtRegister()
            generator = ReportGenerator(output_dir=Path(tmp))
            paths = generator.save_research_debt_register(register)
            self.assertTrue(paths["markdown"].exists())
            self.assertTrue(paths["json"].exists())

    def test_save_architecture_compliance_report(self):
        with TemporaryDirectory() as tmp:
            generator = ReportGenerator(output_dir=Path(tmp))
            path = generator.save_architecture_compliance_report()
            self.assertTrue(path.exists())
            content = path.read_text()
            self.assertIn("Architecture Compliance Report", content)
            self.assertIn("IMPLEMENTED", content)

    def test_save_human_validation_checklist(self):
        with TemporaryDirectory() as tmp:
            generator = ReportGenerator(output_dir=Path(tmp))
            path = generator.save_human_validation_checklist()
            self.assertTrue(path.exists())
            content = path.read_text()
            self.assertIn("Human Validation Checklist", content)
            self.assertIn("[ ]", content)

    def test_save_ingestion_report(self):
        with TemporaryDirectory() as tmp:
            ds = _make_minimal_dataset()
            generator = ReportGenerator(output_dir=Path(tmp))
            path = generator.save_ingestion_report(ds)
            self.assertTrue(path.exists())
            with open(path) as fh:
                data = json.load(fh)
            self.assertEqual(data["report_type"], "ingestion")
            self.assertEqual(data["sample_count"], 5)


if __name__ == "__main__":
    unittest.main()
