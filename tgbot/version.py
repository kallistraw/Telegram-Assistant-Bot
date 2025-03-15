"""This module contains the versionìng of the bot."""

from typing import Final
from typing import NamedTuple


class Version(NamedTuple):
    """
    Very pythonic versioning scheme.

    The `prn` is a shorthand for pre-release number,
    and is always 0 for stable release (obviously).
    """

    major: int
    minor: int
    patch: int
    stage: str
    date: str | None
    prn: int

    def _shorthand(self) -> str:
        return {
            "alpha": "a",
            "beta": "b",
            "candidate": "rc",
        }[self.stage]

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}"
        if self.patch != 0:
            version = f"{version}.{self.patch}"
        if self.stage != "final":
            version = f"{version}{self._shorthand()}{self.prn}"

        return version


__version__: Final[Version] = Version(
    major=0, minor=0, patch=1, stage="alpha", date="3/04/2025", prn=1
)

__all__ = "__version__"
