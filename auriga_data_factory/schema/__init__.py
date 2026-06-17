"""Schema module — canonical dataset representation and versioning."""
from .canonical import CanonicalSample, CanonicalDataset, DatasetState, SourceType, FiducialType
from .versioning import DatasetVersion

__all__ = [
    "CanonicalSample", "CanonicalDataset", "DatasetState",
    "SourceType", "FiducialType", "DatasetVersion",
]
