"""
Auriga Data Factory — Abstract Synthetic Generator
Base interface for all synthetic generation strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class SyntheticGenerator(ABC):
    """
    Abstract base for all Auriga synthetic data generators.

    All implementations must:
      - Label every produced record with sourceType = 'synthetic'.
      - Populate syntheticParameters with all generation inputs.
      - Produce records conforming to the Auriga Canonical Schema.
      - Never produce records that claim to be 'real'.
    """

    GENERATOR_VERSION = "1.0.0"

    @abstractmethod
    def generate(
        self,
        coverage_gaps: List[Dict[str, Any]],
        base_dataset_version: str,
        output_path: str,
    ) -> str:
        """
        Generate synthetic records to address coverage gaps.

        Args:
            coverage_gaps: List of gap dicts from CoverageAnalyzer.
            base_dataset_version: The real dataset this synthetic data extends.
            output_path: Directory where the synthetic dataset will be written.

        Returns:
            Path to the generated dataset directory.
        """
        raise NotImplementedError

    @abstractmethod
    def generator_name(self) -> str:
        """Return a human-readable name for this generator."""
        raise NotImplementedError
