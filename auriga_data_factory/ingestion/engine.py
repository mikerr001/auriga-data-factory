"""
Auriga Data Factory — Ingestion Engine
========================================
Orchestrates heterogeneous dataset imports using registered adapters and
produces canonical :class:`CanonicalDataset` objects with full provenance.

Usage example::

    engine = IngestionEngine(output_dir=Path("data/datasets"))
    dataset = engine.ingest(
        source=Path("my_experiment/metadata.csv"),
        name="ArUco Lab Experiment 1",
        adapter="auriga_fiducial",
    )
    print(f"Imported {dataset.sample_count} samples → {dataset.state}")
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..schema.canonical import CanonicalDataset, DatasetState
from ..observability.logger import get_logger
from .adapters import (
    BaseAdapter,
    CSVAdapter,
    AurigaFiducialAdapter,
    LegacyExperimentAdapter,
)

logger = get_logger("auriga.ingestion.engine")

# Registry of built-in adapter names.
_ADAPTER_REGISTRY: Dict[str, Type[BaseAdapter]] = {
    "csv":             CSVAdapter,
    "auriga_fiducial": AurigaFiducialAdapter,
    "legacy":          LegacyExperimentAdapter,
}


class IngestionEngine:
    """
    Main ingestion orchestrator.

    Parameters
    ----------
    output_dir:
        Directory where ingested datasets will be persisted as JSON files.
    default_version:
        Default dataset version string for new imports.
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        default_version: str = "1.0.0",
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else None
        self.default_version = default_version
        self._custom_adapters: Dict[str, Type[BaseAdapter]] = {}

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def register_adapter(self, name: str, adapter_class: Type[BaseAdapter]) -> None:
        """
        Register a custom adapter for future use.

        Parameters
        ----------
        name:
            Identifier string (e.g. ``"my_custom_format"``).
        adapter_class:
            A class that subclasses :class:`BaseAdapter`.
        """
        if not issubclass(adapter_class, BaseAdapter):
            raise TypeError(
                f"adapter_class must subclass BaseAdapter, got {adapter_class}."
            )
        self._custom_adapters[name] = adapter_class
        logger.info(f"Custom adapter registered: '{name}' → {adapter_class.__name__}")

    def ingest(
        self,
        source: Path,
        name: str,
        adapter: str = "auriga_fiducial",
        version: Optional[str] = None,
        notes: str = "",
        adapter_kwargs: Optional[Dict[str, Any]] = None,
    ) -> CanonicalDataset:
        """
        Import a dataset and return a :class:`CanonicalDataset`.

        Parameters
        ----------
        source:
            Path to the source data (file or directory).
        name:
            Human-readable name for the resulting dataset.
        adapter:
            Name of the adapter to use. Built-in options:
            ``"csv"``, ``"auriga_fiducial"``, ``"legacy"``.
        version:
            Dataset version string (defaults to ``self.default_version``).
        notes:
            Free-text notes attached to the dataset.
        adapter_kwargs:
            Extra keyword arguments forwarded to the adapter constructor.

        Returns
        -------
        CanonicalDataset
            A new dataset in the ``candidate`` state.
        """
        source = Path(source)
        version = version or self.default_version
        adapter_kwargs = adapter_kwargs or {}

        logger.ingestion(
            f"Ingestion started: name='{name}', adapter='{adapter}', source={source}",
            dataset_name=name,
            adapter=adapter,
        )

        adapter_instance = self._build_adapter(adapter, version, adapter_kwargs)

        try:
            samples, provenance = adapter_instance.ingest(source, **adapter_kwargs)
        except Exception as exc:
            logger.error(
                f"Ingestion failed for '{name}': {exc}",
                exc_info=True,
                dataset_name=name,
            )
            raise

        dataset = CanonicalDataset(
            name=name,
            version=version,
            state=DatasetState.CANDIDATE.value,
            samples=samples,
            provenance=provenance,
            notes=notes,
        )

        logger.ingestion(
            f"Ingestion complete: {dataset.sample_count} samples "
            f"({dataset.real_sample_count} real, {dataset.synthetic_sample_count} synthetic). "
            f"Dataset ID: {dataset.dataset_id}",
            dataset_id=dataset.dataset_id,
            sample_count=dataset.sample_count,
        )

        if self.output_dir:
            self._persist(dataset)

        return dataset

    def ingest_batch(
        self,
        sources: List[Dict[str, Any]],
    ) -> List[CanonicalDataset]:
        """
        Ingest multiple datasets in sequence.

        Parameters
        ----------
        sources:
            List of dictionaries, each forwarded as kwargs to :meth:`ingest`.

        Returns
        -------
        List of :class:`CanonicalDataset` objects (in order, skipping failures).
        """
        results: List[CanonicalDataset] = []
        for spec in sources:
            try:
                dataset = self.ingest(**spec)
                results.append(dataset)
            except Exception as exc:
                logger.error(
                    f"Batch ingestion failed for spec {spec.get('name', '?')}: {exc}",
                    exc_info=True,
                )
        return results

    # ------------------------------------------------------------------ #
    # Internal helpers                                                      #
    # ------------------------------------------------------------------ #

    def _build_adapter(
        self,
        name: str,
        version: str,
        kwargs: Dict[str, Any],
    ) -> BaseAdapter:
        """Instantiate the named adapter."""
        registry = {**_ADAPTER_REGISTRY, **self._custom_adapters}
        if name not in registry:
            available = ", ".join(sorted(registry.keys()))
            raise ValueError(
                f"Unknown adapter '{name}'. Available adapters: {available}."
            )
        adapter_class = registry[name]

        # Inject dataset_version if the adapter accepts it.
        import inspect
        sig = inspect.signature(adapter_class.__init__)
        if "dataset_version" in sig.parameters:
            return adapter_class(dataset_version=version, **{
                k: v for k, v in kwargs.items()
                if k in sig.parameters and k != "dataset_version"
            })
        return adapter_class()

    def _persist(self, dataset: CanonicalDataset) -> Path:
        """Write a dataset JSON file to the output directory."""
        safe_name = dataset.name.replace(" ", "_").replace("/", "-")
        filename = f"{safe_name}_v{dataset.version}_{dataset.dataset_id[:8]}.json"
        output_path = self.output_dir / filename
        dataset.save(output_path)
        logger.ingestion(
            f"Dataset persisted: {output_path}",
            dataset_id=dataset.dataset_id,
            path=str(output_path),
        )
        return output_path
