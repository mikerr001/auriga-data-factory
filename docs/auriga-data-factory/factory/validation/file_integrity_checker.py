"""
Auriga Data Factory — Layer 3: File Integrity Checker
Verifies that all referenced image files exist and are readable.
"""

import os
from typing import Any, Dict, List

READABLE_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class FileIntegrityChecker:
    """Layer 3: File integrity check (BLOCKING)."""

    def __init__(self, base_path: str):
        """
        Args:
            base_path: Root directory for the dataset.
                       image paths in records are resolved relative to this.
        """
        self.base_path = base_path

    def check(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        issues = []
        for record in records:
            rid = record.get("recordId", "unknown")
            source_type = record.get("sourceType", "real")
            image_path = record.get("imagePath")

            # Synthetic records without images are permitted
            if source_type == "synthetic" and not image_path:
                continue

            if not image_path:
                issues.append(self._issue(rid, "MISSING_IMAGE_PATH",
                    "imagePath is null or empty for a non-synthetic record."))
                continue

            full_path = os.path.join(self.base_path, image_path)

            if not os.path.exists(full_path):
                issues.append(self._issue(rid, "IMAGE_FILE_NOT_FOUND",
                    f"Image file not found: {full_path}"))
                continue

            # Check extension is a known image type
            _, ext = os.path.splitext(full_path)
            if ext.lower() not in READABLE_IMAGE_EXTENSIONS:
                issues.append(self._issue(rid, "UNRECOGNIZED_IMAGE_FORMAT",
                    f"File extension '{ext}' is not a recognized image format: "
                    f"{READABLE_IMAGE_EXTENSIONS}"))
                continue

            # Attempt to open the file to verify readability
            try:
                with open(full_path, "rb") as f:
                    header = f.read(8)
                    if len(header) < 4:
                        issues.append(self._issue(rid, "IMAGE_TOO_SMALL",
                            f"File at {full_path} is too small to be a valid image."))
            except (OSError, IOError) as e:
                issues.append(self._issue(rid, "IMAGE_UNREADABLE",
                    f"Cannot read file {full_path}: {e}"))

            # Filename consistency: imagePath basename must match filename field
            filename_field = record.get("filename", "")
            image_basename = os.path.basename(image_path)
            if filename_field and image_basename != filename_field:
                issues.append(self._issue(rid, "FILENAME_MISMATCH",
                    f"'filename' field ('{filename_field}') does not match "
                    f"imagePath basename ('{image_basename}')."))

        return issues

    @staticmethod
    def _issue(record_id: str, issue_type: str, detail: str) -> Dict[str, Any]:
        return {
            "layer": "file_integrity",
            "severity": "blocking",
            "recordId": record_id,
            "field": "imagePath",
            "issue": issue_type,
            "detail": detail,
        }
