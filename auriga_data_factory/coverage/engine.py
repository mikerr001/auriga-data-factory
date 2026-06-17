"""
Auriga Data Factory — Coverage Analysis Engine
================================================
Determines dataset completeness across multiple dimensions and generates
actionable collection recommendations.

Dimensions analysed:
    - Distance coverage   — expected distance bins are represented.
    - Orientation coverage — standard orientations are covered.
    - Device coverage     — multiple device aliases are represented.
    - Fiducial type       — multiple fiducial families if applicable.
    - Sample balance      — no single cell dominates the distribution.

Research debt: RD-DATA-002 — Coverage thresholds require empirical tuning.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..schema.canonical import CanonicalDataset, CanonicalSample
from ..observability.logger import get_logger
from .results import CoverageReport, CoverageScore

logger = get_logger("auriga.coverage.engine")

# Default expected distance bins (metres).
DEFAULT_DISTANCE_BINS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

# Standard orientation labels.
DEFAULT_ORIENTATIONS = ["Down", "Up", "Left", "Right", "Angled", "Flat"]

# Minimum samples per (distance_bin × orientation) cell.
DEFAULT_MIN_CELL_SAMPLES = 3


class CoverageEngine:
    """
    Analyses dataset coverage across multiple dimensions.

    Parameters
    ----------
    expected_distances:
        Distance values (in metres) expected to be covered.
    expected_orientations:
        Orientation labels expected to be covered.
    min_devices:
        Minimum number of distinct device aliases expected.
    min_cell_samples:
        Minimum samples expected per (distance × orientation) cell.
    distance_tolerance:
        Metres tolerance when matching a sample to a distance bin.
    """

    def __init__(
        self,
        expected_distances: Optional[List[float]] = None,
        expected_orientations: Optional[List[str]] = None,
        min_devices: int = 1,
        min_cell_samples: int = DEFAULT_MIN_CELL_SAMPLES,
        distance_tolerance: float = 0.3,
    ) -> None:
        self.expected_distances = expected_distances or DEFAULT_DISTANCE_BINS
        self.expected_orientations = expected_orientations or DEFAULT_ORIENTATIONS
        self.min_devices = min_devices
        self.min_cell_samples = min_cell_samples
        self.distance_tolerance = distance_tolerance

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def analyse(self, dataset: CanonicalDataset) -> CoverageReport:
        """
        Perform a full coverage analysis on ``dataset``.

        Parameters
        ----------
        dataset:
            The dataset to analyse.

        Returns
        -------
        CoverageReport
            Containing per-dimension scores, recommendations, and heatmaps.
        """
        logger.info(
            f"Coverage analysis started: '{dataset.name}' ({dataset.sample_count} samples)",
            dataset_id=dataset.dataset_id,
        )

        scores: List[CoverageScore] = []
        scores.append(self._analyse_distance(dataset.samples))
        scores.append(self._analyse_orientation(dataset.samples))
        scores.append(self._analyse_device(dataset.samples))
        scores.append(self._analyse_balance(dataset.samples))

        overall = sum(s.score for s in scores) / len(scores) if scores else 0.0

        recommendations = self._generate_recommendations(dataset.samples)
        heatmap_data = self._build_heatmap(dataset.samples)

        report = CoverageReport(
            dataset_id=dataset.dataset_id,
            dataset_name=dataset.name,
            dataset_version=dataset.version,
            scores=scores,
            overall_score=overall,
            recommendations=recommendations,
            heatmap_data=heatmap_data,
            analysed_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            f"Coverage analysis complete: overall_score={overall:.1%}, "
            f"{len(recommendations)} recommendation(s).",
            dataset_id=dataset.dataset_id,
        )
        return report

    # ------------------------------------------------------------------ #
    # Dimension analysers                                                   #
    # ------------------------------------------------------------------ #

    def _analyse_distance(self, samples: List[CanonicalSample]) -> CoverageScore:
        """Measure coverage across expected distance bins."""
        covered: List[float] = []
        missing: List[float] = []

        for expected_d in self.expected_distances:
            found = any(
                abs(s.distance_meters - expected_d) <= self.distance_tolerance
                for s in samples
            )
            if found:
                covered.append(expected_d)
            else:
                missing.append(expected_d)

        observed = sorted({round(s.distance_meters, 1) for s in samples})
        score = len(covered) / len(self.expected_distances) if self.expected_distances else 1.0

        return CoverageScore(
            dimension="distance",
            score=score,
            observed_values=observed,
            expected_values=self.expected_distances,
            missing_values=missing,
            notes=f"{len(covered)}/{len(self.expected_distances)} distance bins covered.",
        )

    def _analyse_orientation(self, samples: List[CanonicalSample]) -> CoverageScore:
        """Measure coverage across expected orientation labels."""
        observed_orientations = {s.orientation for s in samples}
        covered = [o for o in self.expected_orientations if o in observed_orientations]
        missing = [o for o in self.expected_orientations if o not in observed_orientations]
        score = len(covered) / len(self.expected_orientations) if self.expected_orientations else 1.0

        return CoverageScore(
            dimension="orientation",
            score=score,
            observed_values=sorted(observed_orientations),
            expected_values=self.expected_orientations,
            missing_values=missing,
            notes=f"{len(covered)}/{len(self.expected_orientations)} orientations covered.",
        )

    def _analyse_device(self, samples: List[CanonicalSample]) -> CoverageScore:
        """Measure device diversity."""
        devices = list({s.device_alias for s in samples})
        score = min(1.0, len(devices) / self.min_devices) if self.min_devices > 0 else 1.0
        notes = f"{len(devices)} device alias(es) observed (minimum: {self.min_devices})."

        return CoverageScore(
            dimension="device_diversity",
            score=score,
            observed_values=sorted(devices),
            expected_values=[f"≥{self.min_devices} devices"],
            missing_values=[] if len(devices) >= self.min_devices else ["Additional devices needed"],
            notes=notes,
        )

    def _analyse_balance(self, samples: List[CanonicalSample]) -> CoverageScore:
        """
        Measure balance of the (distance_bin × orientation) matrix.

        A perfectly balanced dataset has equal samples in every cell.
        Score is based on the fraction of cells meeting the minimum.
        """
        cells: Dict[Tuple[float, str], int] = defaultdict(int)
        for s in samples:
            bin_d = self._nearest_bin(s.distance_meters)
            cells[(bin_d, s.orientation)] += 1

        expected_cells = len(self.expected_distances) * len(self.expected_orientations)
        if expected_cells == 0:
            return CoverageScore(
                dimension="sample_balance",
                score=1.0,
                notes="No expected cells defined.",
            )

        sufficient_cells = sum(
            1 for count in cells.values() if count >= self.min_cell_samples
        )
        # Cells that don't exist at all count as 0.
        score = sufficient_cells / expected_cells

        return CoverageScore(
            dimension="sample_balance",
            score=min(1.0, score),
            observed_values=[f"{k[0]}m×{k[1]}={v}" for k, v in sorted(cells.items())],
            notes=(
                f"{sufficient_cells}/{expected_cells} cells have ≥{self.min_cell_samples} sample(s)."
            ),
        )

    # ------------------------------------------------------------------ #
    # Recommendations                                                        #
    # ------------------------------------------------------------------ #

    def _generate_recommendations(self, samples: List[CanonicalSample]) -> List[str]:
        """
        Produce concrete, actionable collection recommendations.

        Example output:
            "Collect 12 additional samples at 2.5 metres using Down orientation."
        """
        recommendations: List[str] = []

        # Count existing (distance_bin × orientation) cells.
        cells: Dict[Tuple[float, str], int] = defaultdict(int)
        for s in samples:
            bin_d = self._nearest_bin(s.distance_meters)
            cells[(bin_d, s.orientation)] += 1

        for dist in self.expected_distances:
            for orient in self.expected_orientations:
                count = cells.get((dist, orient), 0)
                if count < self.min_cell_samples:
                    needed = self.min_cell_samples - count
                    recommendations.append(
                        f"Collect {needed} additional sample(s) at "
                        f"{dist} metres using {orient} orientation."
                    )

        # Warn if no device diversity.
        devices = {s.device_alias for s in samples}
        if len(devices) < self.min_devices:
            recommendations.append(
                f"Capture data from at least {self.min_devices} distinct "
                f"device alias(es). Currently have {len(devices)}."
            )

        return recommendations

    # ------------------------------------------------------------------ #
    # Heatmap builder                                                        #
    # ------------------------------------------------------------------ #

    def _build_heatmap(self, samples: List[CanonicalSample]) -> Dict[str, Any]:
        """
        Build a 2-D heatmap of (distance × orientation) sample counts.

        Returns a dict suitable for JSON serialisation and rendering.
        """
        orientations = self.expected_orientations
        distances = self.expected_distances

        # Build matrix: rows = orientations, cols = distances.
        matrix: List[List[int]] = []
        for orient in orientations:
            row: List[int] = []
            for dist in distances:
                count = sum(
                    1 for s in samples
                    if s.orientation == orient
                    and abs(s.distance_meters - dist) <= self.distance_tolerance
                )
                row.append(count)
            matrix.append(row)

        return {
            "distance_x_orientation": {
                "x_labels": [str(d) for d in distances],
                "y_labels": orientations,
                "matrix": matrix,
                "x_axis": "Distance (m)",
                "y_axis": "Orientation",
                "description": "Sample count per (distance × orientation) cell.",
            }
        }

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    def _nearest_bin(self, distance: float) -> float:
        """Return the nearest expected distance bin for a measurement."""
        if not self.expected_distances:
            return round(distance, 1)
        return min(self.expected_distances, key=lambda d: abs(d - distance))
