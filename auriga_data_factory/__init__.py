"""
Auriga Data Factory
===================
Offline-first research infrastructure platform for ingesting, validating,
analysing, versioning, and approving datasets for downstream Auriga systems.

Constitutional constraints:
- Never store unique hardware identifiers.
- Never transmit datasets to cloud services by default.
- Never modify approved datasets.
- Never bypass human approval.
- Never hide validation failures.
- Always preserve provenance.
- Always distinguish between real and synthetic data.
- Always document uncertainty.
"""

__version__ = "1.0.0"
__project__ = "Auriga Data Factory"
__phase__ = "B — Implementation"
