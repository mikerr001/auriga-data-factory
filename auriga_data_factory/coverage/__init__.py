"""Coverage module — dataset completeness analysis and collection recommendations."""
from .engine import CoverageEngine
from .results import CoverageReport, CoverageScore

__all__ = ["CoverageEngine", "CoverageReport", "CoverageScore"]
