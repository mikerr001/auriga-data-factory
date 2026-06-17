"""
Auriga Data Factory — Layer 6: Outlier Detector
Identifies statistically unusual values using IQR method + domain hard limits.

See DATA_VALIDATION_PROTOCOL.md Section 8 for full specification.

WARNING: Thresholds are design estimates pending empirical calibration.
         See Research Debt RD-002.
"""

import statistics
from typing import Any, Dict, List, Optional, Tuple

# Domain-specific hard limits (ADVISORY — not blocking)
HARD_LIMITS: Dict[str, Tuple[float, float]] = {
    "distanceMeters": (0.1, 20.0),
    "cameraHeightCm": (10.0, 250.0),
    "markerWidthPx": (1.0, 4000.0),
    "markerHeightPx": (1.0, 4000.0),
}

# Fields to analyze with IQR (minimum 10 samples required)
IQR_FIELDS = [
    "distanceMeters", "markerWidthPx", "markerHeightPx",
    "markerAreaPx", "cameraHeightCm", "bearingDegrees",
]

IQR_MULTIPLIER = 1.5
MIN_SAMPLES_FOR_IQR = 10


class OutlierDetector:
    """
    Layer 6: Outlier detection (ADVISORY — does not block promotion).

    Constitutional note: Outlier findings must be presented to human
    reviewers. They must not be silently suppressed.
    """

    def check(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []

        # Hard limit checks (per-record, no minimum sample requirement)
        for record in records:
            rid = record.get("recordId", "unknown")
            for field_name, (low, high) in HARD_LIMITS.items():
                val = record.get(field_name)
                if val is None:
                    continue
                try:
                    fval = float(val)
                except (TypeError, ValueError):
                    continue
                if fval < low or fval > high:
                    findings.append(self._finding(
                        rid, field_name, fval, "hard_limit",
                        f"{field_name} = {fval} is outside absolute domain bounds [{low}, {high}]. "
                        f"Review image or collection record for this sample.",
                    ))

        # IQR-based outlier detection (requires MIN_SAMPLES_FOR_IQR)
        for field_name in IQR_FIELDS:
            values_with_ids = [
                (record.get("recordId", f"row_{i}"), record.get(field_name))
                for i, record in enumerate(records)
                if record.get(field_name) is not None
            ]

            if len(values_with_ids) < MIN_SAMPLES_FOR_IQR:
                continue

            ids = [x[0] for x in values_with_ids]
            vals = [float(x[1]) for x in values_with_ids]

            q1, q3 = self._iqr_bounds(vals)
            iqr = q3 - q1
            lower_fence = q1 - IQR_MULTIPLIER * iqr
            upper_fence = q3 + IQR_MULTIPLIER * iqr

            for rid, val in zip(ids, vals):
                if val < lower_fence or val > upper_fence:
                    # Skip if already flagged by hard limit check
                    already_flagged = any(
                        f["recordId"] == rid and f["field"] == field_name
                        for f in findings
                    )
                    if not already_flagged:
                        findings.append(self._finding(
                            rid, field_name, val, "iqr",
                            f"{field_name} = {val} is outside IQR fence "
                            f"[{lower_fence:.2f}, {upper_fence:.2f}] "
                            f"(Q1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}). "
                            f"See Research Debt RD-002 — thresholds are design estimates.",
                        ))

        return findings

    @staticmethod
    def _iqr_bounds(values: List[float]) -> Tuple[float, float]:
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[(3 * n) // 4]
        return q1, q3

    @staticmethod
    def _finding(record_id, field, value, bound_type, detail) -> Dict[str, Any]:
        return {
            "layer": "outliers",
            "severity": "advisory",
            "recordId": record_id,
            "field": field,
            "value": value,
            "boundType": bound_type,
            "issue": "STATISTICAL_OUTLIER",
            "detail": detail,
            "recommendation": (
                "Review this record. If it represents a genuine measurement, retain with notes. "
                "If it is a collection artifact, consider removing before approval."
            ),
        }
