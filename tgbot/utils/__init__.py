"""This module contains utility functions"""

import os
import time
from logging import basicConfig
from logging import FileHandler
from logging import getLogger
from logging import INFO
from logging import StreamHandler

from .helpers import is_dangerous
from .helpers import load_modules

# Logger
log_file = time.strftime("%Y-%m-%d.log")
if os.path.isfile(log_file):
    os.remove(log_file)

_FMT = "%(asctime)s | %(name)s [%(levelname)s] : %(message)s"
basicConfig(
    level=INFO,
    format=_FMT,
    datefmt="%H:%M:%S",
    handlers=[FileHandler(log_file), StreamHandler()],
)

LOGS = getLogger("BotLogger")

try:
    import coloredlogs

    coloredlogs.install(level=None, logger=LOGS, fmt=_FMT)
except ImportError:
    pass

__all__ = ("is_dangerous", "load_modules", "log_file", "LOGS")
