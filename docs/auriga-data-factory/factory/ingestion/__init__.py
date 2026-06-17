"""
Auriga Data Factory — Ingestion Subsystem
Normalizes raw collected data to the Auriga Canonical Schema.
"""

from .ingestor import BaseIngestor
from .csv_ingestor import CsvIngestor
from .normalizer import Normalizer

__all__ = ["BaseIngestor", "CsvIngestor", "Normalizer"]
