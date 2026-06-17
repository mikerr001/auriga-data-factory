"""
Auriga Data Factory — Layer 2: Completeness Checker
Detects null, empty, and logically invalid values in required fields.
"""

from typing import Any, Dict, List, Optional


class CompletenessChecker:
    """Layer 2: Completeness check (BLOCKING)."""

    POSITIVE_NUMERIC_FIELDS = {"distanceMeters", "cameraHeightCm"}

    def check(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        issues = []
        for record in records:
            rid = record.get("recordId", "unknown")

            # Required string fields must not be empty
            for field in ("filename", "deviceModel", "deviceAlias",
                          "captureTimestamp", "datasetVersion"):
                val = record.get(field)
                if val is None or str(val).strip() == "":
                    issues.append(self._issue(rid, field, "EMPTY_REQUIRED_FIELD",
                        f"Required field '{field}' is null or empty."))

            # Numeric fields must be positive
            for field in self.POSITIVE_NUMERIC_FIELDS:
                val = record.get(field)
                if val is not None:
                    try:
                        fval = float(val)
                        if fval <= 0:
                            issues.append(self._issue(rid, field, "NON_POSITIVE_VALUE",
                                f"Field '{field}' = {fval}. Must be > 0."))
                    except (TypeError, ValueError):
                        issues.append(self._issue(rid, field, "TYPE_ERROR",
                            f"Field '{field}' value '{val}' cannot be converted to float."))

            # Context-dependent: detection success requires pixel fields
            if record.get("detectionSuccess") is True:
                for pf in ("markerWidthPx", "markerHeightPx", "centerX", "centerY"):
                    if record.get(pf) is None:
                        issues.append(self._issue(rid, pf, "MISSING_DETECTION_FIELD",
                            f"detectionSuccess=true but '{pf}' is null. "
                            f"Pixel fields are required when detection succeeded."))

            # Context-dependent: synthetic records require syntheticParameters
            if record.get("sourceType") == "synthetic":
                if not record.get("syntheticParameters"):
                    issues.append(self._issue(rid, "syntheticParameters", "MISSING_SYNTHETIC_PARAMS",
                        "sourceType='synthetic' requires syntheticParameters to be populated. "
                        "See SYNTHETIC_GENERATION_GUIDE.md Section 5."))

        return issues

    @staticmethod
    def _issue(record_id: str, field: str, issue_type: str, detail: str) -> Dict[str, Any]:
        return {
            "layer": "completeness",
            "severity": "blocking",
            "recordId": record_id,
            "field": field,
            "issue": issue_type,
            "detail": detail,
        }
