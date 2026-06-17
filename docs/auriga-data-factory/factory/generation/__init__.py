"""
Auriga Data Factory — Synthetic Generation Subsystem

Primary MVP: GeometryGenerator (mathematically derived from camera models).
Future:      AugmentationGenerator, RenderingGenerator, MLGenerator (placeholders).

See SYNTHETIC_GENERATION_GUIDE.md for full specification and constitutional position.
"""

from .generator import SyntheticGenerator
from .geometry_generator import GeometryGenerator
from .augmentation_generator import AugmentationGenerator
from .rendering_generator import RenderingGenerator
from .ml_generator import MLGenerator

__all__ = [
    "SyntheticGenerator",
    "GeometryGenerator",
    "AugmentationGenerator",
    "RenderingGenerator",
    "MLGenerator",
]
