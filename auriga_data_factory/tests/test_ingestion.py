"""
Unit tests — Ingestion module
==============================
Tests for CSV adapter, Auriga fiducial adapter, and ingestion engine.
"""

import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ..ingestion.adapters import CSVAdapter, AurigaFiducialAdapter, LegacyExperimentAdapter
from ..ingestion.engine import IngestionEngine
from ..schema.canonical import CanonicalDataset, DatasetState, SourceType


# ─────────────────────────── Helpers ─────────────────────────────────────── #

def write_sample_csv(path: Path, rows: list) -> None:
    """Write a sample CSV file with canonical column names."""
    fieldnames = [
        "sample_id", "filename", "image_path", "fiducial_type", "object_name",
        "distance_meters", "orientation", "camera_height_cm", "device_model",
        "device_alias", "marker_width_px", "marker_height_px", "marker_area_px",
        "center_x", "center_y", "detection_success", "capture_timestamp",
        "source_type", "notes",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


SAMPLE_ROW = {
    "sample_id": "S-001",
    "filename": "img001.jpg",
    "image_path": "",
    "fiducial_type": "aruco",
    "object_name": "target_A",
    "distance_meters": "1.5",
    "orientation": "Down",
    "camera_height_cm": "120",
    "device_model": "TestPhone",
    "device_alias": "DeviceA",
    "marker_width_px": "80",
    "marker_height_px": "80",
    "marker_area_px": "6400",
    "center_x": "960",
    "center_y": "540",
    "detection_success": "true",
    "capture_timestamp": "2026-06-17T10:00:00+00:00",
    "source_type": "real",
    "notes": "",
}


# ─────────────────────────── CSV Adapter ─────────────────────────────────── #

class TestCSVAdapter(unittest.TestCase):

    def test_import_single_row(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            write_sample_csv(csv_path, [SAMPLE_ROW])
            adapter = CSVAdapter(image_dir=None)
            samples, prov = adapter.ingest(csv_path)
            self.assertEqual(len(samples), 1)
            self.assertEqual(samples[0].sample_id, "S-001")
            self.assertAlmostEqual(samples[0].distance_meters, 1.5)

    def test_import_multiple_rows(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            rows = [dict(SAMPLE_ROW, sample_id=f"S-{i:03d}") for i in range(10)]
            write_sample_csv(csv_path, rows)
            adapter = CSVAdapter()
            samples, prov = adapter.ingest(csv_path)
            self.assertEqual(len(samples), 10)

    def test_provenance_recorded(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            write_sample_csv(csv_path, [SAMPLE_ROW])
            adapter = CSVAdapter()
            samples, prov = adapter.ingest(csv_path)
            self.assertEqual(prov["adapter"], "CSVAdapter")
            self.assertIn("import_timestamp", prov)

    def test_missing_file_raises(self):
        adapter = CSVAdapter()
        with self.assertRaises(FileNotFoundError):
            adapter.ingest(Path("/nonexistent/path/metadata.csv"))

    def test_detection_success_parsed(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            row = dict(SAMPLE_ROW, detection_success="true")
            write_sample_csv(csv_path, [row])
            adapter = CSVAdapter()
            samples, _ = adapter.ingest(csv_path)
            self.assertTrue(samples[0].detection_success)

    def test_synthetic_source_type(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            row = dict(SAMPLE_ROW, source_type="synthetic")
            write_sample_csv(csv_path, [row])
            adapter = CSVAdapter()
            samples, _ = adapter.ingest(csv_path)
            self.assertEqual(samples[0].source_type, SourceType.SYNTHETIC.value)
            self.assertTrue(samples[0].is_synthetic)

    def test_auto_generates_sample_id_if_missing(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            row = dict(SAMPLE_ROW, sample_id="")
            write_sample_csv(csv_path, [row])
            adapter = CSVAdapter()
            samples, _ = adapter.ingest(csv_path)
            self.assertTrue(len(samples[0].sample_id) > 0)

    def test_empty_csv_returns_no_samples(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            write_sample_csv(csv_path, [])
            adapter = CSVAdapter()
            samples, prov = adapter.ingest(csv_path)
            self.assertEqual(len(samples), 0)
            self.assertEqual(prov["rows_imported"], 0)


# ─────────────────────────── Auriga Adapter ──────────────────────────────── #

class TestAurigaFiducialAdapter(unittest.TestCase):

    def test_import_from_directory(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            csv_path = tmp_path / "metadata.csv"
            write_sample_csv(csv_path, [SAMPLE_ROW])
            adapter = AurigaFiducialAdapter()
            samples, prov = adapter.ingest(tmp_path)
            self.assertEqual(len(samples), 1)
            self.assertEqual(prov["adapter"], "AurigaFiducialAdapter")

    def test_import_from_csv_file(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            write_sample_csv(csv_path, [SAMPLE_ROW])
            adapter = AurigaFiducialAdapter()
            samples, prov = adapter.ingest(csv_path)
            self.assertEqual(len(samples), 1)

    def test_no_csv_in_dir_raises(self):
        with TemporaryDirectory() as tmp:
            adapter = AurigaFiducialAdapter()
            with self.assertRaises(FileNotFoundError):
                adapter.ingest(Path(tmp))


# ─────────────────────────── Legacy Adapter ──────────────────────────────── #

class TestLegacyExperimentAdapter(unittest.TestCase):

    def _write_legacy_json(self, path: Path, n: int = 3) -> None:
        data = {
            "schema_version": "0.5",
            "samples": [
                {
                    "id": f"L-{i:03d}",
                    "filename": f"img{i:03d}.jpg",
                    "path": f"/data/img{i:03d}.jpg",
                    "distance": 1.0 + i * 0.5,
                    "orientation": "Down",
                    "height_cm": 120.0,
                    "device": "OldPhone/0.9",
                    "alias": "DeviceB",
                    "width_px": 70.0,
                    "height_px": 70.0,
                    "area_px": 4900.0,
                    "cx": 960.0,
                    "cy": 540.0,
                    "detected": True,
                    "timestamp": "2025-01-01T00:00:00+00:00",
                }
                for i in range(n)
            ],
        }
        with open(path, "w") as fh:
            json.dump(data, fh)

    def test_import_legacy_json(self):
        with TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "legacy.json"
            self._write_legacy_json(json_path, n=5)
            adapter = LegacyExperimentAdapter()
            samples, prov = adapter.ingest(json_path)
            self.assertEqual(len(samples), 5)
            self.assertEqual(prov["adapter"], "LegacyExperimentAdapter")

    def test_legacy_provenance_recorded(self):
        with TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "legacy.json"
            self._write_legacy_json(json_path, n=2)
            adapter = LegacyExperimentAdapter()
            samples, _ = adapter.ingest(json_path)
            self.assertIn("legacy_index", samples[0].provenance)


# ─────────────────────────── Ingestion Engine ────────────────────────────── #

class TestIngestionEngine(unittest.TestCase):

    def test_ingest_produces_candidate_dataset(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            rows = [dict(SAMPLE_ROW, sample_id=f"S-{i:03d}") for i in range(5)]
            write_sample_csv(csv_path, rows)

            engine = IngestionEngine(output_dir=Path(tmp) / "datasets")
            dataset = engine.ingest(source=csv_path, name="Test", adapter="csv")

            self.assertIsInstance(dataset, CanonicalDataset)
            self.assertEqual(dataset.state, DatasetState.CANDIDATE.value)
            self.assertEqual(dataset.sample_count, 5)

    def test_ingest_persists_file(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            write_sample_csv(csv_path, [SAMPLE_ROW])
            out_dir = Path(tmp) / "datasets"

            engine = IngestionEngine(output_dir=out_dir)
            engine.ingest(source=csv_path, name="Persist Test", adapter="csv")

            files = list(out_dir.glob("*.json"))
            self.assertEqual(len(files), 1)

    def test_unknown_adapter_raises(self):
        with TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "metadata.csv"
            write_sample_csv(csv_path, [SAMPLE_ROW])
            engine = IngestionEngine()
            with self.assertRaises(ValueError):
                engine.ingest(source=csv_path, name="Bad", adapter="nonexistent_adapter")

    def test_custom_adapter_registration(self):
        from ..ingestion.adapters import BaseAdapter
        from typing import Any, Dict, List, Tuple

        class DummyAdapter(BaseAdapter):
            def ingest(self, source, **kwargs) -> Tuple[List, Dict[str, Any]]:
                return [], {"adapter": "DummyAdapter"}

        engine = IngestionEngine()
        engine.register_adapter("dummy", DummyAdapter)
        with TemporaryDirectory() as tmp:
            dataset = engine.ingest(
                source=Path(tmp), name="Dummy", adapter="dummy"
            )
            self.assertEqual(dataset.sample_count, 0)


if __name__ == "__main__":
    unittest.main()
