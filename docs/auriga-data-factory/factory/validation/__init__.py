"""
Auriga Data Factory — Validation Subsystem
7-layer quality validation pipeline.

Layers:
  1. Schema validation       (BLOCKING)
  2. Completeness check      (BLOCKING)
  3. File integrity check    (BLOCKING)
  4. Duplicate detection     (BLOCKING)
  5. Consistency check       (BLOCKING)
  6. Outlier detection       (ADVISORY)
  7. Coverage analysis       (ADVISORY)
"""

from .validator import Validator, ValidationResult

__all__ = ["Validator", "ValidationResult"]
