"""
Auriga Data Factory — Dataset Versioning
=========================================
Utilities for managing semantic version strings and producing new versions
when datasets are modified.

Constitutional rule:
    Any modification to an approved dataset MUST produce a new version.
    The original approved dataset MUST remain immutable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class DatasetVersion:
    """
    Immutable semantic version: ``major.minor.patch``.

    Parameters
    ----------
    major:
        Incremented for schema-breaking changes.
    minor:
        Incremented for backward-compatible additions.
    patch:
        Incremented for bug-fixes and corrections.
    """

    major: int
    minor: int
    patch: int

    # ------------------------------------------------------------------ #
    # Constructors                                                          #
    # ------------------------------------------------------------------ #

    @classmethod
    def from_string(cls, version_str: str) -> "DatasetVersion":
        """
        Parse a version string such as ``"1.2.3"``.

        Raises
        ------
        ValueError
            If the string is not a valid ``major.minor.patch`` triplet.
        """
        parts = version_str.strip().split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid version string '{version_str}'. "
                "Expected format: 'major.minor.patch'."
            )
        try:
            return cls(major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2]))
        except ValueError as exc:
            raise ValueError(
                f"Version components must be integers: '{version_str}'."
            ) from exc

    @classmethod
    def initial(cls) -> "DatasetVersion":
        """Return the first version ``1.0.0``."""
        return cls(major=1, minor=0, patch=0)

    # ------------------------------------------------------------------ #
    # Bump helpers                                                          #
    # ------------------------------------------------------------------ #

    def bump_major(self) -> "DatasetVersion":
        """Return a new version with the major component incremented."""
        return DatasetVersion(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "DatasetVersion":
        """Return a new version with the minor component incremented."""
        return DatasetVersion(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "DatasetVersion":
        """Return a new version with the patch component incremented."""
        return DatasetVersion(major=self.major, minor=self.minor, patch=self.patch + 1)

    # ------------------------------------------------------------------ #
    # Comparison                                                            #
    # ------------------------------------------------------------------ #

    def as_tuple(self) -> Tuple[int, int, int]:
        """Return the version as a comparable tuple."""
        return (self.major, self.minor, self.patch)

    def __lt__(self, other: "DatasetVersion") -> bool:  # noqa: D105
        return self.as_tuple() < other.as_tuple()

    def __le__(self, other: "DatasetVersion") -> bool:  # noqa: D105
        return self.as_tuple() <= other.as_tuple()

    def __gt__(self, other: "DatasetVersion") -> bool:  # noqa: D105
        return self.as_tuple() > other.as_tuple()

    def __ge__(self, other: "DatasetVersion") -> bool:  # noqa: D105
        return self.as_tuple() >= other.as_tuple()

    def __str__(self) -> str:  # noqa: D105
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self) -> str:  # noqa: D105
        return f"DatasetVersion('{self}')"
