"""
Auriga Data Factory — Normalizer
Converts raw row dictionaries to canonical schema records.

Handles:
  - UUID generation for recordId
  - Type coercion (string "true" → bool, "1.5" → float)
  - Enum normalization (lowercase, strip whitespace)
  - Null handling for optional fields
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

# Enum permitted values per canonical schema
ORIENTATION_VALUES = {"flat", "angled", "tilted", "overhead", "down", "unknown"}
SOURCE_TYPE_VALUES = {"real", "synthetic", "hybrid"}
FIDUCIAL_TYPE_VALUES = {"aruco", "apriltag", "qr", "custom", "none"}
LIGHTING_VALUES = {"indoor_artificial", "indoor_natural", "outdoor", "unknown"}
ENVIRONMENT_VALUES = {"hallway", "room", "outdoor", "lab", "unknown"}


class Normalizer:
    """
    Normalizes a raw CSV row dict to a canonical schema record.
    Generates UUIDs, coerces types, normalizes enums.
    """

    def normalize_row(
        self,
        row: Dict[str, Any],
        dataset_version: str,
        row_index: int,
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Normalize a single raw row to canonical schema.

        Returns:
            (record, warnings, errors)
            record   — normalized dict
            warnings — list of non-blocking issues
            errors   — list of blocking issues
        """
        warnings: List[str] = []
        errors: List[str] = []
        record: Dict[str, Any] = {}

        # --- recordId: always generate fresh UUID ---
        record["recordId"] = str(uuid.uuid4())

        # --- datasetVersion: use provided version if row is blank ---
        record["datasetVersion"] = dataset_version

        # --- sourceType ---
        record["sourceType"] = self._normalize_enum(
            row.get("sourceType", "real"), SOURCE_TYPE_VALUES, "sourceType",
            row_index, warnings, errors
        )

        # --- captureTimestamp ---
        ts = (row.get("captureTimestamp") or row.get("timestamp") or "").strip()
        if not ts:
            warnings.append(
                f"Row {row_index}: captureTimestamp is blank. "
                f"Set to placeholder. See DATA_INGESTION_GUIDE.md Section 3.5."
            )
            ts = "1970-01-01T00:00:00Z"
        record["captureTimestamp"] = ts

        # --- filename / imagePath ---
        record["filename"] = (row.get("filename") or "").strip()
        record["imagePath"] = (row.get("imagePath") or "").strip()

        # --- fiducialType ---
        record["fiducialType"] = self._normalize_enum(
            row.get("fiducialType", "aruco"), FIDUCIAL_TYPE_VALUES,
            "fiducialType", row_index, warnings, errors
        )

        # --- distanceMeters ---
        record["distanceMeters"] = self._to_float(
            row.get("distanceMeters") or row.get("distance"),
            "distanceMeters", row_index, errors
        )

        # --- orientation ---
        record["orientation"] = self._normalize_enum(
            row.get("orientation", "unknown"), ORIENTATION_VALUES,
            "orientation", row_index, warnings, errors
        )

        # --- cameraHeightCm ---
        record["cameraHeightCm"] = self._to_float(
            row.get("cameraHeightCm") or row.get("camera_height"),
            "cameraHeightCm", row_index, errors
        )

        # --- deviceModel ---
        record["deviceModel"] = (row.get("deviceModel") or row.get("device") or "").strip()
        if not record["deviceModel"]:
            warnings.append(
                f"Row {row_index}: deviceModel is blank. "
                f"Record the device model for reproducibility."
            )

        # --- deviceAlias ---
        record["deviceAlias"] = (row.get("deviceAlias") or "Device-A").strip()

        # --- detectionSuccess ---
        record["detectionSuccess"] = self._to_bool(
            row.get("detectionSuccess") or row.get("detected"),
            "detectionSuccess", row_index, errors
        )

        # --- Optional pixel fields ---
        record["markerWidthPx"] = self._to_int_optional(row.get("markerWidthPx") or row.get("width"))
        record["markerHeightPx"] = self._to_int_optional(row.get("markerHeightPx") or row.get("height"))
        record["markerAreaPx"] = self._to_int_optional(row.get("markerAreaPx") or row.get("area"))
        record["centerX"] = self._to_float_optional(row.get("centerX"))
        record["centerY"] = self._to_float_optional(row.get("centerY"))
        record["markerPhysicalSizeMm"] = self._to_float_optional(row.get("markerPhysicalSizeMm"))
        record["bearingDegrees"] = self._to_float_optional(row.get("bearingDegrees"))
        record["pitchDegrees"] = self._to_float_optional(row.get("pitchDegrees"))
        record["yawDegrees"] = self._to_float_optional(row.get("yawDegrees"))
        record["markerId"] = (row.get("markerId") or "").strip() or None  # RD-026

        # --- Enum optional fields ---
        lc = (row.get("lightingCondition") or "").strip().lower()
        record["lightingCondition"] = lc if lc in LIGHTING_VALUES else None

        env = (row.get("environmentType") or "").strip().lower()
        record["environmentType"] = env if env in ENVIRONMENT_VALUES else None

        # --- syntheticParameters ---
        sp_raw = row.get("syntheticParameters")
        if sp_raw and isinstance(sp_raw, str):
            import json
            try:
                record["syntheticParameters"] = json.loads(sp_raw)
            except json.JSONDecodeError:
                warnings.append(
                    f"Row {row_index}: syntheticParameters is not valid JSON — stored as string."
                )
                record["syntheticParameters"] = sp_raw
        elif sp_raw and isinstance(sp_raw, dict):
            record["syntheticParameters"] = sp_raw
        else:
            record["syntheticParameters"] = None

        # --- notes ---
        record["notes"] = (row.get("notes") or "").strip() or None

        return record, warnings, errors

    # ------------------------------------------------------------------
    # Type coercion helpers
    # ------------------------------------------------------------------

    def _to_float(
        self,
        value: Any,
        field_name: str,
        row_index: int,
        errors: List[str],
    ) -> Optional[float]:
        if value is None or str(value).strip() == "":
            errors.append(f"Row {row_index}: required field '{field_name}' is missing or empty.")
            return None
        try:
            return float(str(value).strip())
        except ValueError:
            errors.append(f"Row {row_index}: field '{field_name}' value '{value}' is not a valid number.")
            return None

    def _to_float_optional(self, value: Any) -> Optional[float]:
        if value is None or str(value).strip() == "":
            return None
        try:
            return float(str(value).strip())
        except ValueError:
            return None

    def _to_int_optional(self, value: Any) -> Optional[int]:
        if value is None or str(value).strip() == "":
            return None
        try:
            return int(float(str(value).strip()))
        except ValueError:
            return None

    def _to_bool(
        self,
        value: Any,
        field_name: str,
        row_index: int,
        errors: List[str],
    ) -> Optional[bool]:
        if value is None or str(value).strip() == "":
            errors.append(f"Row {row_index}: required field '{field_name}' is missing.")
            return None
        s = str(value).strip().lower()
        if s in ("true", "1", "yes", "detected"):
            return True
        if s in ("false", "0", "no", "not detected", "undetected"):
            return False
        errors.append(
            f"Row {row_index}: field '{field_name}' value '{value}' "
            f"cannot be interpreted as boolean."
        )
        return None

    def _normalize_enum(
        self,
        value: Any,
        permitted: set,
        field_name: str,
        row_index: int,
        warnings: List[str],
        errors: List[str],
    ) -> Optional[str]:
        if value is None or str(value).strip() == "":
            errors.append(f"Row {row_index}: required enum field '{field_name}' is missing.")
            return None
        normalized = str(value).strip().lower()
        if normalized not in permitted:
            errors.append(
                f"Row {row_index}: field '{field_name}' value '{value}' "
                f"is not in permitted values: {sorted(permitted)}."
            )
            return None
        return normalized
