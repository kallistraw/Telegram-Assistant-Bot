###
import os
import time
from logging import basicConfig
from logging import FileHandler
from logging import getLogger
from logging import INFO
from logging import StreamHandler

from .config import *
from .utils.wrapper import *

__version__ = "0.0.1-build"

Var = ConfigVars()

channel_id = Var("LOG_CHANNEL") if Var("LOG_CHANNEL") else None
bot = Client(Var("BOT_TOKEN"), log_channel=channel_id)

filename = time.strftime("%Y-%m-%d.log")
if os.path.isfile(filename):
    os.remove(filename)

_FMT = "%(asctime)s | %(name)s [%(levelname)s] : %(message)s"
basicConfig(
    level=INFO,
    format=_FMT,
    datefmt="%H:%M:%S",
    handlers=[FileHandler(filename), StreamHandler()],
)

LOGS = getLogger("BotLogger")

try:
    import coloredlogs

    coloredlogs.install(level=None, logger=LOGS, fmt=_FMT)
except ImportError:
    pass
