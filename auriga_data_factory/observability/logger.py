"""
Auriga Data Factory — Structured Logger
========================================
Provides a unified, structured logging interface for all Data Factory events.
Events are categorised by subsystem and include provenance metadata.

Event categories logged:
    - ingestion: dataset import events
    - validation: schema and integrity check events
    - promotion: dataset state transition events
    - error: unrecoverable failures
    - warning: recoverable anomalies
    - research_debt: documented technical debt discoveries
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Format log records as single-line JSON for machine consumption."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge any extra fields attached to the record.
        for key, value in record.__dict__.items():
            if key.startswith("auriga_"):
                payload[key[7:]] = value  # strip "auriga_" prefix
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class AurigaLogger:
    """
    Thin façade over Python's standard ``logging`` module, adding:

    * Structured JSON output.
    * Consistent subsystem tagging.
    * Research debt event helpers.
    * Optional file sink.

    Parameters
    ----------
    name:
        Logger name (typically the module path).
    level:
        Minimum severity level (default INFO).
    log_file:
        Optional path to a JSONL log file.
    """

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
    ) -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        if not self._logger.handlers:
            # Console handler (plain text for readability).
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(
                logging.Formatter(
                    fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                )
            )
            self._logger.addHandler(console_handler)

            if log_file is not None:
                log_file = Path(log_file)
                log_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setLevel(level)
                file_handler.setFormatter(StructuredFormatter())
                self._logger.addHandler(file_handler)

    # ------------------------------------------------------------------ #
    # Public helpers                                                        #
    # ------------------------------------------------------------------ #

    def ingestion(self, message: str, **kwargs: Any) -> None:
        """Log an ingestion-phase event."""
        self._emit(logging.INFO, message, subsystem="ingestion", **kwargs)

    def validation(self, message: str, **kwargs: Any) -> None:
        """Log a validation-phase event."""
        self._emit(logging.INFO, message, subsystem="validation", **kwargs)

    def promotion(self, message: str, **kwargs: Any) -> None:
        """Log a dataset state-promotion event."""
        self._emit(logging.INFO, message, subsystem="promotion", **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:  # noqa: A003
        """Log a recoverable anomaly."""
        self._emit(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs: Any) -> None:
        """Log an unrecoverable failure."""
        self._emit(logging.ERROR, message, exc_info=exc_info, **kwargs)

    def research_debt(self, debt_id: str, message: str, **kwargs: Any) -> None:
        """
        Log a research debt discovery.

        Parameters
        ----------
        debt_id:
            Canonical identifier, e.g. ``RD-DATA-001``.
        message:
            Human-readable description of the debt.
        """
        self._emit(
            logging.WARNING,
            f"[{debt_id}] {message}",
            subsystem="research_debt",
            debt_id=debt_id,
            **kwargs,
        )

    def info(self, message: str, **kwargs: Any) -> None:
        """Log a general informational event."""
        self._emit(logging.INFO, message, **kwargs)

    # ------------------------------------------------------------------ #
    # Internal                                                              #
    # ------------------------------------------------------------------ #

    def _emit(
        self,
        level: int,
        message: str,
        exc_info: bool = False,
        **kwargs: Any,
    ) -> None:
        extra = {f"auriga_{k}": v for k, v in kwargs.items()}
        self._logger.log(level, message, extra=extra, exc_info=exc_info)


# Module-level convenience factory -----------------------------------------

_registry: Dict[str, AurigaLogger] = {}


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> AurigaLogger:
    """
    Return a cached :class:`AurigaLogger` instance for the given name.

    Parameters
    ----------
    name:
        Logger name.
    level:
        Log level (default INFO).
    log_file:
        Optional JSONL file path.
    """
    if name not in _registry:
        _registry[name] = AurigaLogger(name, level=level, log_file=log_file)
    return _registry[name]
