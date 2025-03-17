###
"""
This module contains global configurations, variables, and commonly used imports.
"""
import os
import platform
import sys
import time

from telegram import __version__ as __ptb__

# Misc imports
from .configs import get_var

# Core imports
from .core import Client, bot_db

# Utility imports
from .utils import LOGS
from .version import __version__

__all__ = ("LOGS", "__version__", "Var", "Bot", "__ptb__")

if not os.path.exists("./modules"):
    TEXT = "'modules' directory not found! Make sure that you are on the correct path"
    LOGS.error(TEXT)
    sys.exit()

# Python versions compatibility
py_ver = sys.version_info
if py_ver < (3, 9):
    if py_ver < (3, 7):
        LOGS.error("Python >= 3.7 is needed to run this bot!")
        LOGS.error("Please install newer Python version from deadsnake PPA or pyenv.")
        sys.exit(1)

    LOGS.warning(
        "Your Python version (%s)"
        "is lower than the recommended version to run this bot!",
        platform.python_version(),
    )
    LOGS.warning("The bot might be able to run, but most modules need Python > 3.9")
    while True:
        response = input("\nDo you want to continue? (yes/no): ").strip().lower()
        if response in ("yes", "y"):
            break
        if response in ("no", "n"):
            LOGS.info(
                "Aborted. If your OS does not have Python > 3.9,"
                "install it from deadsnake PPA or pyenv."
            )
            sys.exit(1)
        else:
            LOGS.error("Invalid input. Please enter 'yes' or 'no'.")

# Cache
_tgbot_cache: dict[str, any] = {}

# Initialization
StartTime = time.time()
Var = get_var()
DB = bot_db()
LOGS.info("Initializing connection with %s...", DB.name)
if DB.ping():
    LOGS.info("Connected to %s!", DB.name)


if not Var("BOT_TOKEN"):
    LOGS.error("'BOT_TOKEN' Not found! Please fill it in '.env' file first.")
    sys.exit()

# Initialize the bot
channel_id = DB.get("LOG_CHANNEL") or Var("LOG_CHANNEL") or None
Bot = Client(Var("BOT_TOKEN"), log_channel=None)
