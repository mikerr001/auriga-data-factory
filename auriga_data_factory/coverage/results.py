"""
Auriga Data Factory — Coverage Result Types
============================================
Data structures for dataset coverage analysis outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CoverageScore:
    """
    Normalised coverage score (0.0–1.0) for a single dimension.

    Attributes
    ----------
    dimension:
        Name of the coverage dimension (e.g. ``"distance"``, ``"orientation"``).
    score:
        Score between 0.0 (no coverage) and 1.0 (complete coverage).
    observed_values:
        List of distinct observed values.
    expected_values:
        List of expected/target values.
    missing_values:
        Values in ``expected_values`` not present in ``observed_values``.
    notes:
        Human-readable description of the score.
    """

    dimension: str
    score: float
    observed_values: List[Any] = field(default_factory=list)
    expected_values: List[Any] = field(default_factory=list)
    missing_values: List[Any] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": round(self.score, 3),
            "observed_values": self.observed_values,
            "expected_values": self.expected_values,
            "missing_values": self.missing_values,
            "notes": self.notes,
        }


@dataclass
class CoverageReport:
    """
    Full coverage analysis report for a dataset.

    Attributes
    ----------
    dataset_id:
        ID of the analysed dataset.
    dataset_name:
        Human-readable name.
    dataset_version:
        Dataset version string.
    scores:
        Per-dimension coverage scores.
    overall_score:
        Weighted average of all dimension scores.
    recommendations:
        List of human-readable collection recommendations.
    heatmap_data:
        Dict of 2-D heatmap matrices keyed by axis pair name.
    analysed_at:
        ISO-8601 timestamp of analysis.
    """

    dataset_id: str
    dataset_name: str
    dataset_version: str
    scores: List[CoverageScore] = field(default_factory=list)
    overall_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    heatmap_data: Dict[str, Any] = field(default_factory=dict)
    analysed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "analysed_at": self.analysed_at,
            "overall_score": round(self.overall_score, 3),
            "scores": [s.to_dict() for s in self.scores],
            "recommendations": self.recommendations,
            "heatmap_data": self.heatmap_data,
        }

    def as_text(self) -> str:
        """Render a human-readable coverage report."""
        lines = [
            "=" * 60,
            f"COVERAGE REPORT — {self.dataset_name} v{self.dataset_version}",
            f"Dataset ID  : {self.dataset_id}",
            f"Analysed    : {self.analysed_at}",
            f"Overall     : {self.overall_score:.1%}",
            "=" * 60,
            "Dimension Scores:",
        ]
        for score in self.scores:
            bar_len = int(score.score * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {score.dimension:20} [{bar}] {score.score:.1%}")
            if score.missing_values:
                lines.append(f"    Missing: {score.missing_values}")

        if self.recommendations:
            lines += ["", "Collection Recommendations:"]
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"  {i}. {rec}")
        lines.append("=" * 60)
        return "\n".join(lines)
