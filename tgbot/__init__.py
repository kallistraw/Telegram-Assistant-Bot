# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""
This module contains global configurations, variables, and commonly used imports.
"""
from logging import WARNING, getLogger
import os
import platform
import sys
import time

from telegram import __version__ as __ptb__
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, Defaults, PicklePersistence

from tgbot.configs import ConfigVars
from tgbot.core import get_database
from tgbot.core.application import TelegramApplication
from tgbot.utils import LOGS
from tgbot.version import __version__

__all__ = ("__ptb__", "__version__", "bot", "database", "LOGS", "Var")

getLogger("httpx").setLevel(WARNING)

Var = ConfigVars()

if not Var.BOT_TOKEN:
    LOGS.error("'BOT_TOKEN' Not found! Please fill it in '.env' file first.")
    sys.exit()

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
    LOGS.warning("The bot might be able to run, but most modules need Python >= 3.9")
    while True:
        response = input("\nDo you want to continue? (yes/no): ").strip().lower()
        if response in ("yes", "y"):
            break
        if response in ("no", "n"):
            LOGS.info(
                "Aborted. If your OS does not have Python >= 3.9,"
                "install it from deadsnake PPA or pyenv."
            )
            sys.exit(1)
        else:
            LOGS.error("Invalid input. Please enter 'yes' or 'no'.")

StartTime = time.time()

# Initialize the bot
# Using HTML as the default parse mode
defaults = Defaults(parse_mode=ParseMode.HTML)

# Data persistence
persist = PicklePersistence(".bot_data.pkl")

database = get_database()

bot_token = database.get("BOT_TOKEN", None) or Var.BOT_TOKEN
log_group_id = database.get("LOG_GROUP_ID", None) or Var.LOG_GROUP_ID or None
bot: TelegramApplication = (
    ApplicationBuilder()
    .application_class(TelegramApplication, kwargs={"log_group_id": log_group_id})
    .arbitrary_callback_data(2048)
    .defaults(defaults)
    .persistence(persist)
    .token(bot_token)
    .build()
)
