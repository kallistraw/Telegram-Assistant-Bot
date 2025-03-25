# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""This module contains the versionìng of the bot."""

from typing import Final, NamedTuple, Union


class Version(NamedTuple):
    """
    Very pythonic versioning scheme.

    The `prn` is a shorthand for pre-release number, and is always 0 for stable release.
    """

    major: int
    minor: int
    micro: int
    stage: str
    date: Union[str, None]
    prn: int

    def _shorthand(self) -> str:
        return {
            "alpha": "a",
            "beta": "b",
            "candidate": "rc",
        }[self.stage]

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}"
        if self.micro != 0:
            version = f"{version}.{self.micro}"
        if self.stage != "final":
            version = f"{version}{self._shorthand()}{self.prn}"

        return version


__version__: Final[Version] = Version(
    major=0, minor=0, micro=1, stage="alpha", date="3/04/2025", prn=1
)

__all__ = ["__version__"]
