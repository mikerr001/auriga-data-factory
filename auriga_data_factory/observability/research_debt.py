"""
Auriga Data Factory — Research Debt Register
=============================================
A lightweight in-memory and on-disk register for tracking technical and
scientific debt discovered during data factory operations.

Debt items follow the pattern:  RD-DATA-NNN

Examples from the specification:
    RD-DATA-001: Synthetic uncertainty modelling assumptions.
    RD-DATA-002: Coverage thresholds require empirical tuning.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ResearchDebt:
    """
    A single research debt item.

    Attributes
    ----------
    debt_id:
        Canonical identifier, e.g. ``RD-DATA-001``.
    title:
        Short summary (one line).
    description:
        Full description of the debt.
    severity:
        ``low`` | ``medium`` | ``high`` | ``critical``.
    subsystem:
        Data factory subsystem where the debt was discovered.
    discovered_at:
        ISO-8601 UTC timestamp of discovery.
    resolved:
        Whether the debt has been addressed.
    resolution_notes:
        Optional notes describing how the debt was resolved.
    """

    debt_id: str
    title: str
    description: str
    severity: str = "medium"
    subsystem: str = "unknown"
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved: bool = False
    resolution_notes: Optional[str] = None

    def __post_init__(self) -> None:
        valid_severities = {"low", "medium", "high", "critical"}
        if self.severity not in valid_severities:
            raise ValueError(
                f"Invalid severity '{self.severity}'. Must be one of {valid_severities}."
            )


class ResearchDebtRegister:
    """
    Manages a collection of :class:`ResearchDebt` items.

    The register can be persisted to a JSONL file and reloaded between sessions.

    Parameters
    ----------
    register_path:
        Optional path to a JSONL file for persistence.
    """

    # Canonical debt items pre-registered from the specification.
    _BUILTIN_DEBTS: List[Dict] = [
        {
            "debt_id": "RD-DATA-001",
            "title": "Synthetic uncertainty modelling assumptions",
            "description": (
                "The synthetic geometry generator uses simplified perspective "
                "projection formulae. Real-world lens distortion, sensor noise, "
                "and environmental occlusion are not modelled. Synthetic samples "
                "may not faithfully represent edge cases encountered in production."
            ),
            "severity": "medium",
            "subsystem": "synthetic",
        },
        {
            "debt_id": "RD-DATA-002",
            "title": "Coverage thresholds require empirical tuning",
            "description": (
                "Current coverage completeness thresholds (distance bins, "
                "orientation bins, minimum samples-per-cell) are heuristic. "
                "They should be validated against downstream model performance "
                "data before being treated as ground truth."
            ),
            "severity": "medium",
            "subsystem": "coverage",
        },
        {
            "debt_id": "RD-DATA-003",
            "title": "Outlier detection sensitivity unvalidated",
            "description": (
                "The IQR-based outlier detection in the validation engine uses "
                "a fixed multiplier of 1.5. This may be too aggressive for small "
                "datasets or too permissive for large ones. Requires domain-expert "
                "calibration per fiducial type."
            ),
            "severity": "low",
            "subsystem": "validation",
        },
        {
            "debt_id": "RD-DATA-004",
            "title": "Human approval workflow is file-based",
            "description": (
                "The current human approval mechanism writes a JSON approval "
                "record to disk. This is sufficient for research use but does "
                "not provide cryptographic non-repudiation of reviewer identity. "
                "A signed-approval mechanism should be considered for production."
            ),
            "severity": "low",
            "subsystem": "approval",
        },
    ]

    def __init__(self, register_path: Optional[Path] = None) -> None:
        self._debts: Dict[str, ResearchDebt] = {}
        self._register_path = register_path

        # Populate built-in items.
        for item in self._BUILTIN_DEBTS:
            debt = ResearchDebt(**item)
            self._debts[debt.debt_id] = debt

        # Load persisted items if file exists.
        if register_path and Path(register_path).exists():
            self._load(Path(register_path))

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def add(self, debt: ResearchDebt) -> None:
        """Register a new debt item, overwriting if the ID already exists."""
        self._debts[debt.debt_id] = debt
        if self._register_path:
            self._save()

    def resolve(self, debt_id: str, notes: str) -> None:
        """Mark a debt item as resolved with explanatory notes."""
        if debt_id not in self._debts:
            raise KeyError(f"No research debt with ID '{debt_id}'.")
        self._debts[debt_id].resolved = True
        self._debts[debt_id].resolution_notes = notes
        if self._register_path:
            self._save()

    def all_items(self) -> List[ResearchDebt]:
        """Return all registered debt items."""
        return list(self._debts.values())

    def unresolved(self) -> List[ResearchDebt]:
        """Return only unresolved debt items."""
        return [d for d in self._debts.values() if not d.resolved]

    def as_markdown(self) -> str:
        """Render the register as a Markdown table."""
        lines = [
            "# Research Debt Register — Auriga Data Factory",
            "",
            "| ID | Severity | Subsystem | Title | Resolved |",
            "|----|----------|-----------|-------|----------|",
        ]
        for debt in sorted(self._debts.values(), key=lambda d: d.debt_id):
            resolved_str = "✓" if debt.resolved else "✗"
            lines.append(
                f"| {debt.debt_id} | {debt.severity} | {debt.subsystem} "
                f"| {debt.title} | {resolved_str} |"
            )
        lines += ["", "## Detail"]
        for debt in sorted(self._debts.values(), key=lambda d: d.debt_id):
            lines += [
                f"",
                f"### {debt.debt_id} — {debt.title}",
                f"**Severity:** {debt.severity}  ",
                f"**Subsystem:** {debt.subsystem}  ",
                f"**Discovered:** {debt.discovered_at}  ",
                f"**Resolved:** {'Yes' if debt.resolved else 'No'}  ",
                f"",
                debt.description,
            ]
            if debt.resolution_notes:
                lines += ["", f"**Resolution:** {debt.resolution_notes}"]
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Persistence                                                           #
    # ------------------------------------------------------------------ #

    def _save(self) -> None:
        path = Path(self._register_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            for debt in self._debts.values():
                fh.write(json.dumps(asdict(debt)) + "\n")

    def _load(self, path: Path) -> None:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                debt = ResearchDebt(**data)
                # Persisted items take precedence over built-ins.
                self._debts[debt.debt_id] = debt
