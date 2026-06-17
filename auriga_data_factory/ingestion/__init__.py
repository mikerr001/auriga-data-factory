"""Ingestion module — heterogeneous dataset import and provenance tracking."""
from .engine import IngestionEngine
from .adapters import CSVAdapter, AurigaFiducialAdapter

__all__ = ["IngestionEngine", "CSVAdapter", "AurigaFiducialAdapter"]
