"""This module contains utility functions"""

from logging import INFO, FileHandler, StreamHandler, basicConfig, getLogger
import os
import time

# Logger
log_file = time.strftime("tg-bot.log")

# Don't know if this is a good idea or not...
# Basically, everytime the bot restart,
# will delete and create a new log file to keep it small and clean
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

__all__ = [
    "LOGS",
]
