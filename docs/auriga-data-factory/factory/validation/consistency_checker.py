"""
Auriga Data Factory — Layer 5: Consistency Checker
Verifies cross-field logical consistency.

See DATA_VALIDATION_PROTOCOL.md Section 7 for rule definitions.
"""

from typing import Any, Dict, List


class ConsistencyChecker:
    """Layer 5: Consistency check (BLOCKING + ADVISORY)."""

    # Physical plausibility bounds for cameraHeightCm (handheld device)
    CAMERA_HEIGHT_MIN_CM = 10
    CAMERA_HEIGHT_MAX_CM = 250

    # Absolute hard limits for distanceMeters
    DISTANCE_MIN_M = 0.1
    DISTANCE_MAX_M = 20.0

    def check(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        issues = []
        for record in records:
            rid = record.get("recordId", "unknown")
            detected = record.get("detectionSuccess")

            # C-01 / C-02: Detection results match pixel data
            if detected is True:
                for px_field in ("markerWidthPx", "markerHeightPx"):
                    val = record.get(px_field)
                    if val is not None and int(val) <= 0:
                        issues.append(self._blocking(rid, px_field, "C-02",
                            f"{px_field} = {val} but detectionSuccess = true. "
                            f"Pixel dimensions must be > 0 when detection succeeded."))

            # C-03: Marker area consistent with width × height (within 20%)
            w = record.get("markerWidthPx")
            h = record.get("markerHeightPx")
            a = record.get("markerAreaPx")
            if all(v is not None for v in (w, h, a)) and w and h:
                expected_area = int(w) * int(h)
                if expected_area > 0:
                    deviation = abs(int(a) - expected_area) / expected_area
                    if deviation > 0.20:
                        issues.append(self._blocking(rid, "markerAreaPx", "C-03",
                            f"markerAreaPx ({a}) deviates {deviation:.1%} from "
                            f"markerWidthPx × markerHeightPx ({expected_area}). "
                            f"Threshold: 20%. See RD-009 for threshold calibration."))

            # C-04: Center coordinates within plausible bounds
            cx = record.get("centerX")
            cy = record.get("centerY")
            if cx is not None and (float(cx) < 0 or float(cx) > 10_000):
                issues.append(self._blocking(rid, "centerX", "C-04",
                    f"centerX = {cx} is outside plausible range [0, 10000]."))
            if cy is not None and (float(cy) < 0 or float(cy) > 10_000):
                issues.append(self._blocking(rid, "centerY", "C-04",
                    f"centerY = {cy} is outside plausible range [0, 10000]."))

            # C-06: All records in dataset share the same datasetVersion
            # (checked at dataset level in orchestrator, not per-record here)

            # C-07: sourceType per-record consistency
            dataset_version = record.get("datasetVersion", "")
            source = record.get("sourceType", "")
            if "synthetic" not in dataset_version and source == "synthetic":
                issues.append(self._blocking(rid, "sourceType", "C-07",
                    f"Record has sourceType='synthetic' but datasetVersion "
                    f"'{dataset_version}' does not indicate a synthetic dataset. "
                    f"Use a dataset version containing '_synthetic_' for synthetic records."))

            # C-08 (Advisory): Camera height plausibility
            ch = record.get("cameraHeightCm")
            if ch is not None:
                fch = float(ch)
                if not (self.CAMERA_HEIGHT_MIN_CM <= fch <= self.CAMERA_HEIGHT_MAX_CM):
                    issues.append(self._advisory(rid, "cameraHeightCm", "C-08",
                        f"cameraHeightCm = {fch} is outside physiologically plausible "
                        f"range [{self.CAMERA_HEIGHT_MIN_CM}, {self.CAMERA_HEIGHT_MAX_CM}] cm "
                        f"for a handheld device."))

            # C-10 (Advisory — from ADVERSARIAL_REVIEW ATTACK-008):
            # Flag distanceMeters with suspicious precision
            dist = record.get("distanceMeters")
            if dist is not None:
                dist_str = str(dist)
                if "." in dist_str:
                    decimal_places = len(dist_str.split(".")[1].rstrip("0"))
                    if decimal_places > 2:
                        issues.append(self._advisory(rid, "distanceMeters", "C-10",
                            f"distanceMeters = {dist} has {decimal_places} decimal places. "
                            f"Tape measure precision is ±0.05 m (2 decimal places max). "
                            f"Values with >2 decimal places may indicate computed rather than measured distances."))

        return issues

    @staticmethod
    def _blocking(record_id, field, rule, detail) -> Dict[str, Any]:
        return {
            "layer": "consistency",
            "severity": "blocking",
            "recordId": record_id,
            "field": field,
            "rule": rule,
            "issue": f"CONSISTENCY_VIOLATION_{rule}",
            "detail": detail,
        }

    @staticmethod
    def _advisory(record_id, field, rule, detail) -> Dict[str, Any]:
        return {
            "layer": "consistency",
            "severity": "advisory",
            "recordId": record_id,
            "field": field,
            "rule": rule,
            "issue": f"CONSISTENCY_ADVISORY_{rule}",
            "detail": detail,
        }
