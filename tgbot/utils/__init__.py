# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""This module contains utility functions"""

from logging import INFO, FileHandler, StreamHandler, basicConfig, getLogger
import os
from typing import Any, Union

__all__ = ["_bot_cache", "LOGS"]

LOG_FILE = "bot_log.txt"
if os.path.isfile(LOG_FILE):
    os.remove(LOG_FILE)

_FMT = "%(asctime)s | %(name)s [%(levelname)s] : %(message)s"
basicConfig(
    level=INFO,
    format=_FMT,
    datefmt="%H:%M:%S",
    handlers=[FileHandler(LOG_FILE), StreamHandler()],
)

LOGS = getLogger("BotLogger")

try:
    import coloredlogs

    coloredlogs.install(level=None, logger=LOGS, fmt=_FMT)
except ImportError:
    pass

# Cache
_bot_cache: dict[Union[str | int], Any] = {}
