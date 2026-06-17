"""
Auriga Data Factory — Coverage Analyzer
Identifies dataset coverage gaps and generates collection recommendations.

See COVERAGE_ANALYSIS_GUIDE.md for full specification.

WARNING: Coverage score weights and gap severity ratings are design estimates.
         See Research Debt RD-005. Do not treat the coverage score as a validated metric.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Expected distance coverage for fiducial datasets (meters)
FIDUCIAL_DISTANCE_TARGETS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
FIDUCIAL_ORIENTATION_TARGETS = ["flat", "angled", "tilted", "down", "overhead"]

# Dimension weights for overall coverage score
# WARNING: These are uncalibrated design estimates. See RD-005.
DIMENSION_WEIGHTS = {
    "distance": 0.50,
    "orientation": 0.25,
    "camera_height": 0.15,
    "device": 0.10,
}

# Gap severity thresholds for fiducial distance
CORE_DISTANCE_RANGE = {0.5, 1.0, 1.5, 2.0, 2.5, 3.0}
EXTENDED_DISTANCE_RANGE = {3.5, 4.0, 4.5, 5.0}
CRITICAL_ORIENTATIONS = {"flat", "down"}


@dataclass
class Gap:
    gap_id: str
    dimension: str
    missing_value: Any
    severity: str  # "critical", "high", "medium", "low"
    recommendation_type: str  # "real_collection", "synthetic_extension"
    recommendation: str
    status: str = "open"


@dataclass
class CoverageResult:
    dataset_version: str
    record_count: int
    coverage_score: float
    dimension_scores: Dict[str, float]
    coverage_matrices: Dict[str, Any]
    gaps: List[Gap]
    recommendations_real: List[str]
    recommendations_synthetic: List[str]

    def summary(self) -> str:
        grade = (
            "Excellent" if self.coverage_score >= 90 else
            "Good" if self.coverage_score >= 70 else
            "Partial" if self.coverage_score >= 50 else
            "Insufficient"
        )
        return (
            f"Coverage: {self.coverage_score:.1f}% ({grade}) | "
            f"Gaps: {len(self.gaps)} | "
            f"Real recommendations: {len(self.recommendations_real)} | "
            f"Synthetic recommendations: {len(self.recommendations_synthetic)}"
        )

    def to_markdown(self) -> str:
        lines = [
            f"# Coverage Analysis: {self.dataset_version}",
            f"",
            f"**Records analyzed:** {self.record_count}",
            f"**Overall Coverage Score:** {self.coverage_score:.1f}%",
            f"",
            f"## Dimension Scores",
            f"",
            f"| Dimension | Score | Weight | Weighted |",
            f"|---|---|---|---|",
        ]
        total_weighted = 0.0
        for dim, weight in DIMENSION_WEIGHTS.items():
            score = self.dimension_scores.get(dim, 0.0)
            weighted = score * weight
            total_weighted += weighted
            lines.append(f"| {dim} | {score:.1f}% | {weight} | {weighted:.1f}% |")
        lines.append(f"| **Overall** | | | **{total_weighted:.1f}%** |")

        lines += ["", "## Coverage Gaps", "", "| Gap | Dimension | Missing | Severity |", "|---|---|---|---|"]
        for gap in self.gaps:
            lines.append(f"| {gap.gap_id} | {gap.dimension} | {gap.missing_value} | {gap.severity} |")

        if self.recommendations_real:
            lines += ["", "## Real Data Collection Recommendations", ""]
            for r in self.recommendations_real:
                lines.append(f"- {r}")

        if self.recommendations_synthetic:
            lines += ["", "## Synthetic Extension Recommendations", ""]
            for r in self.recommendations_synthetic:
                lines.append(f"- {r}")

        lines += [
            "",
            "> **Warning:** Coverage score weights are design estimates (RD-005). ",
            "> Do not treat the score as a validated metric.",
        ]

        return "\n".join(lines)


class CoverageAnalyzer:
    """
    Analyzes a validated dataset for coverage gaps and generates recommendations.
    Primarily designed for fiducial calibration datasets (Tier 1 MVP).
    """

    def analyze(
        self,
        records: List[Dict[str, Any]],
        dataset_version: str,
    ) -> CoverageResult:
        """
        Run coverage analysis on a set of canonical records.

        Returns a CoverageResult with matrices, gaps, scores, and recommendations.
        """
        real_records = [r for r in records if r.get("sourceType") == "real"]

        distance_matrix = self._build_distance_orientation_matrix(real_records)
        device_coverage = self._build_device_coverage(real_records)
        height_coverage = self._build_height_coverage(real_records)

        gaps = self._identify_gaps(real_records, distance_matrix, device_coverage)
        dimension_scores = self._compute_dimension_scores(
            real_records, distance_matrix, device_coverage, height_coverage
        )
        coverage_score = sum(
            dimension_scores.get(dim, 0.0) * weight
            for dim, weight in DIMENSION_WEIGHTS.items()
        )

        rec_real = []
        rec_synth = []
        for i, gap in enumerate(gaps):
            gap.gap_id = f"G-{i+1:03d}"
            if gap.severity in ("critical", "high"):
                rec_real.append(
                    f"[RC-{i+1:03d}] Collect real data: {gap.dimension} = {gap.missing_value}. "
                    f"Follow DATA_INGESTION_GUIDE.md."
                )
            rec_synth.append(
                f"[RS-{i+1:03d}] Synthetic extension possible: {gap.dimension} = {gap.missing_value}. "
                f"Use GeometryGenerator with distanceM={gap.missing_value}."
            )

        return CoverageResult(
            dataset_version=dataset_version,
            record_count=len(records),
            coverage_score=round(coverage_score, 1),
            dimension_scores={k: round(v, 1) for k, v in dimension_scores.items()},
            coverage_matrices={
                "distance_x_orientation": distance_matrix,
                "device_coverage": device_coverage,
                "height_coverage": height_coverage,
            },
            gaps=gaps,
            recommendations_real=rec_real,
            recommendations_synthetic=rec_synth,
        )

    def _build_distance_orientation_matrix(
        self, records: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, int]]:
        """Build a count matrix: distance_bucket → orientation → count."""
        matrix: Dict[str, Dict[str, int]] = {}
        for target in FIDUCIAL_DISTANCE_TARGETS:
            key = str(target)
            matrix[key] = {ori: 0 for ori in FIDUCIAL_ORIENTATION_TARGETS}

        for record in records:
            dist = record.get("distanceMeters")
            ori = record.get("orientation")
            if dist is None or ori is None:
                continue
            bucket = self._distance_bucket(float(dist))
            if bucket and ori in FIDUCIAL_ORIENTATION_TARGETS:
                matrix.setdefault(bucket, {ori: 0 for ori in FIDUCIAL_ORIENTATION_TARGETS})
                matrix[bucket][ori] = matrix[bucket].get(ori, 0) + 1

        return matrix

    def _build_device_coverage(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for record in records:
            alias = record.get("deviceAlias", "unknown")
            counts[alias] += 1
        return dict(counts)

    def _build_height_coverage(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        buckets = {"low (60-100cm)": 0, "standard (100-140cm)": 0, "high (140-180cm)": 0, "other": 0}
        for record in records:
            h = record.get("cameraHeightCm")
            if h is None:
                continue
            fh = float(h)
            if 60 <= fh < 100:
                buckets["low (60-100cm)"] += 1
            elif 100 <= fh < 140:
                buckets["standard (100-140cm)"] += 1
            elif 140 <= fh <= 180:
                buckets["high (140-180cm)"] += 1
            else:
                buckets["other"] += 1
        return buckets

    def _identify_gaps(
        self,
        records: List[Dict[str, Any]],
        distance_matrix: Dict[str, Dict[str, int]],
        device_coverage: Dict[str, int],
    ) -> List[Gap]:
        gaps = []
        gap_counter = 0

        # Distance gaps
        for target in FIDUCIAL_DISTANCE_TARGETS:
            key = str(target)
            total = sum(distance_matrix.get(key, {}).values())
            if total == 0:
                severity = "critical" if target in CORE_DISTANCE_RANGE else "high"
                gap_counter += 1
                gaps.append(Gap(
                    gap_id=f"G-{gap_counter:03d}",
                    dimension="distance",
                    missing_value=f"{target}m",
                    severity=severity,
                    recommendation_type="synthetic_extension",
                    recommendation=f"No samples at {target}m. Collect real data or extend synthetically.",
                ))

        # Orientation gaps (flat and down are critical)
        for ori in FIDUCIAL_ORIENTATION_TARGETS:
            total = sum(
                matrix.get(ori, 0)
                for matrix in distance_matrix.values()
            )
            if total == 0:
                severity = "high" if ori in CRITICAL_ORIENTATIONS else "medium"
                if ori == "overhead":
                    severity = "low"
                gap_counter += 1
                gaps.append(Gap(
                    gap_id=f"G-{gap_counter:03d}",
                    dimension="orientation",
                    missing_value=ori,
                    severity=severity,
                    recommendation_type="real_collection",
                    recommendation=f"No '{ori}' orientation samples found.",
                ))

        # Detection outcome balance
        successes = sum(1 for r in records if r.get("detectionSuccess") is True)
        failures = sum(1 for r in records if r.get("detectionSuccess") is False)
        if successes == 0 and records:
            gap_counter += 1
            gaps.append(Gap(
                gap_id=f"G-{gap_counter:03d}",
                dimension="detection_outcome",
                missing_value="any_success",
                severity="critical",
                recommendation_type="real_collection",
                recommendation="No successful detections found. Dataset may be corrupted or misconfigured.",
            ))
        elif failures == 0 and len(records) > 5:
            gap_counter += 1
            gaps.append(Gap(
                gap_id=f"G-{gap_counter:03d}",
                dimension="detection_outcome",
                missing_value="any_failure",
                severity="medium",
                recommendation_type="real_collection",
                recommendation=(
                    "No detection failures found. "
                    "Including failure cases improves edge-case characterization."
                ),
            ))

        return gaps

    def _compute_dimension_scores(
        self,
        records: List[Dict[str, Any]],
        distance_matrix: Dict[str, Dict[str, int]],
        device_coverage: Dict[str, int],
        height_coverage: Dict[str, int],
    ) -> Dict[str, float]:
        # Distance coverage: fraction of target distances with ≥1 sample
        covered_distances = sum(
            1 for target in FIDUCIAL_DISTANCE_TARGETS
            if sum(distance_matrix.get(str(target), {}).values()) > 0
        )
        distance_score = (covered_distances / len(FIDUCIAL_DISTANCE_TARGETS)) * 100

        # Orientation coverage
        orientation_totals = {
            ori: sum(m.get(ori, 0) for m in distance_matrix.values())
            for ori in FIDUCIAL_ORIENTATION_TARGETS
        }
        covered_orientations = sum(1 for v in orientation_totals.values() if v > 0)
        orientation_score = (covered_orientations / len(FIDUCIAL_ORIENTATION_TARGETS)) * 100

        # Camera height coverage
        height_buckets_with_data = sum(
            1 for k, v in height_coverage.items()
            if k != "other" and v > 0
        )
        height_score = (height_buckets_with_data / 3) * 100

        # Device coverage (at least 1 device = 100% for MVP)
        device_score = 100.0 if device_coverage else 0.0

        return {
            "distance": distance_score,
            "orientation": orientation_score,
            "camera_height": height_score,
            "device": device_score,
        }

    @staticmethod
    def _distance_bucket(dist: float) -> Optional[str]:
        """Round a distance to the nearest 0.5m target bucket."""
        for target in FIDUCIAL_DISTANCE_TARGETS:
            if abs(dist - target) <= 0.15:
                return str(target)
        return None
