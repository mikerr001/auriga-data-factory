"""
Auriga Data Factory — Layer 1: Schema Validator
Checks required field presence, type conformance, and enum validity.
"""

import re
from typing import Any, Dict, List

REQUIRED_FIELDS = [
    "recordId", "datasetVersion", "sourceType", "captureTimestamp",
    "filename", "imagePath", "fiducialType", "distanceMeters",
    "orientation", "cameraHeightCm", "deviceModel", "deviceAlias",
    "detectionSuccess",
]

ENUM_FIELDS = {
    "sourceType": {"real", "synthetic", "hybrid"},
    "fiducialType": {"aruco", "apriltag", "qr", "custom", "none"},
    "orientation": {"flat", "angled", "tilted", "overhead", "down", "unknown"},
    "lightingCondition": {"indoor_artificial", "indoor_natural", "outdoor", "unknown"},
    "environmentType": {"hallway", "room", "outdoor", "lab", "unknown"},
}

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

VERSION_PATTERN = re.compile(r"^[a-z][a-z0-9]*(_[a-z][a-z0-9]*)+_v\d+$")

PROHIBITED_FIELDS = {
    "deviceSerialNumber", "imei", "androidId", "macAddress",
    "hardwareFingerprint", "collectorName", "collectorEmail",
}


class SchemaValidator:
    """Layer 1: Schema validation (BLOCKING)."""

    def check(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        issues = []
        for i, record in enumerate(records):
            rid = record.get("recordId", f"row_{i}")

            # Prohibited fields
            for pf in PROHIBITED_FIELDS:
                if pf in record:
                    issues.append(self._issue(rid, pf, "PROHIBITED_FIELD",
                        f"Constitutional rule violation: field '{pf}' must not appear in any Auriga dataset. "
                        f"See CONSTITUTION.md rules P-2 through P-5."))

            # Required field presence
            for rf in REQUIRED_FIELDS:
                if rf not in record:
                    issues.append(self._issue(rid, rf, "MISSING_REQUIRED_FIELD",
                        f"Required field '{rf}' is absent from record."))

            # UUID format
            if "recordId" in record and record["recordId"]:
                if not UUID_PATTERN.match(str(record["recordId"])):
                    issues.append(self._issue(rid, "recordId", "INVALID_UUID",
                        f"recordId '{record['recordId']}' is not a valid UUID v4."))

            # Dataset version format
            if "datasetVersion" in record and record["datasetVersion"]:
                if not VERSION_PATTERN.match(str(record["datasetVersion"])):
                    issues.append(self._issue(rid, "datasetVersion", "INVALID_VERSION_FORMAT",
                        f"datasetVersion '{record['datasetVersion']}' does not match "
                        f"expected format {{family}}_{{subtype}}_v{{n}}."))

            # Enum conformance
            for enum_field, permitted in ENUM_FIELDS.items():
                if enum_field in record and record[enum_field] is not None:
                    if str(record[enum_field]).lower() not in permitted:
                        issues.append(self._issue(rid, enum_field, "INVALID_ENUM_VALUE",
                            f"'{record[enum_field]}' is not in permitted values: {sorted(permitted)}."))

        return issues

    @staticmethod
    def _issue(record_id: str, field: str, issue_type: str, detail: str) -> Dict[str, Any]:
        return {
            "layer": "schema",
            "severity": "blocking",
            "recordId": record_id,
            "field": field,
            "issue": issue_type,
            "detail": detail,
        }
