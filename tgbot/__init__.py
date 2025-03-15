###
"""
This module contains global configurations, variables, and commonly used imports.
"""
import os
import sys

_is_module = __package__ in sys.argv or sys.argv[0] == "-m"

if _is_module:
    import time

    # Misc
    from .config import ConfigVars

    # Utility imports
    from .utils import LOGS

    # Core imports
    from .core import Client
    from .core import BotDB

    # Version
    from .version import __version__ as __tgbot__
    from telegram.version import __version__ as __ptb__

    if not os.path.exists("./modules"):
        TEXT = (
            "'modules' directory not found!\n"
            "Make sure that you are on the correct path"
        )
        LOGS.error(TEXT)
        sys.exit()

    # Configuriable... (is that a word?)
    StartTime = time.time()
    DB = BotDB()
    Var = ConfigVars()

    # To store some stuff that isn't necesarilly need to be stored in the database
    _tgbot_cache: dict[str, any | None] = {}

    LOGS.info("Initializing connection with %s...", DB.name)
    if DB.ping():
        LOGS.info("Connected to %s!", DB.name)

    if not Var("BOT_TOKEN"):
        LOGS.error("'BOT_TOKEN' Not found! Please fill it in '.env' file first.")
        sys.exit()

    channel_id = Var("LOG_CHANNEL") or DB.get("LOG_CHANNEL") or None
    print(channel_id)
    Bot = Client(Var("BOT_TOKEN"), log_channel=channel_id)

else:
    from logging import getLogger

    LOGS = getLogger("BotLogger")
    Bot = DB = None  # pylint: disable=invalid-name
