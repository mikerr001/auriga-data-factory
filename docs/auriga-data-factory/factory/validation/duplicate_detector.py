"""
Auriga Data Factory — Layer 4: Duplicate Detector
Identifies duplicate records by ID, filename, and near-duplicate matching.
"""

from collections import defaultdict
from typing import Any, Dict, List


class DuplicateDetector:
    """Layer 4: Duplicate detection (BLOCKING)."""

    def check(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        issues = []

        # Strategy A: Exact recordId duplicates
        id_index: Dict[str, List[str]] = defaultdict(list)
        for i, record in enumerate(records):
            rid = record.get("recordId", f"row_{i}")
            id_index[rid].append(str(i))

        for rid, row_indices in id_index.items():
            if len(row_indices) > 1:
                issues.append({
                    "layer": "duplicates",
                    "severity": "blocking",
                    "duplicateType": "identical_recordId",
                    "affectedRecords": [rid],
                    "affectedRows": row_indices,
                    "issue": "DUPLICATE_RECORD_ID",
                    "detail": f"recordId '{rid}' appears {len(row_indices)} times (rows: {', '.join(row_indices)}).",
                    "recommendation": "recordIds must be unique. Re-ingest the dataset to generate fresh UUIDs."
                })

        # Strategy B: Identical filename duplicates
        filename_index: Dict[str, List[str]] = defaultdict(list)
        for i, record in enumerate(records):
            fn = record.get("filename", "")
            src = record.get("sourceType", "real")
            if fn:
                key = f"{fn}::{src}"
                filename_index[key].append(record.get("recordId", f"row_{i}"))

        for key, record_ids in filename_index.items():
            if len(record_ids) > 1:
                filename = key.split("::")[0]
                issues.append({
                    "layer": "duplicates",
                    "severity": "blocking",
                    "duplicateType": "identical_filename",
                    "affectedRecords": record_ids,
                    "issue": "DUPLICATE_FILENAME",
                    "detail": f"Filename '{filename}' referenced by {len(record_ids)} records: {record_ids}.",
                    "recommendation": (
                        "Verify whether these represent the same physical capture. "
                        "Remove the duplicate record or rename the file if they are distinct captures."
                    )
                })

        # Strategy C: Near-duplicate detection (advisory within blocking layer)
        seen_near: Dict[tuple, str] = {}
        for record in records:
            rid = record.get("recordId", "unknown")
            dist = record.get("distanceMeters")
            ori = record.get("orientation")
            height = record.get("cameraHeightCm")
            alias = record.get("deviceAlias")
            ts = record.get("captureTimestamp", "")

            if all(v is not None for v in (dist, ori, height, alias)):
                near_key = (
                    round(float(dist), 1) if dist else None,
                    ori,
                    round(float(height), 0) if height else None,
                    alias,
                    ts[:16] if ts else None,  # minute-level timestamp bucket
                )
                if near_key in seen_near:
                    issues.append({
                        "layer": "duplicates",
                        "severity": "advisory",
                        "duplicateType": "near_duplicate",
                        "affectedRecords": [seen_near[near_key], rid],
                        "issue": "NEAR_DUPLICATE_RECORD",
                        "detail": (
                            f"Records '{seen_near[near_key]}' and '{rid}' share identical "
                            f"distance/orientation/height/device/timestamp-minute. "
                            f"Possible double-capture."
                        ),
                        "recommendation": "Review both records. Remove one if they are accidental duplicates."
                    })
                else:
                    seen_near[near_key] = rid

        return issues
