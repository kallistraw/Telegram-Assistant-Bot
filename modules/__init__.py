# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""
This module contains global variables, modules cache, and commonly used imports.
"""
from tgbot import Var, bot, database
from tgbot.core import BotConfig
from tgbot.utils import LOGS, _bot_cache
from tgbot.utils.helpers import KeepSafe, TempCache, censors, get_files, is_dangerous
from tgbot.utils.loader import load_modules
from tgbot.utils.tools import process_thumbnail

__all__ = (
    "_bot_cache",
    "_module_cache",
    "AUTH_LIST",
    "bot",
    "BotConfig",
    "bot_cache",
    "censors",
    "db",
    "FORUM_TOPIC",
    "get_files",
    "is_dangerous",
    "KeepSafe",
    "load_modules",
    "LOG_GROUP_ID",
    "LOGS",
    "module_cache",
    "OWNER_ID",
    "PM_GROUP_ID",
    "process_thumbnail",
    "Var",
    "MAX_WARNING",
)

# Shorthand
db = database

# Constants
LOG_GROUP_ID = db.get("LOG_GROUP_ID") or Var.LOG_GROUP_ID
OWNER_ID = Var.OWNER_ID
AUTH_LIST = [
    OWNER_ID,
]
PM_GROUP_ID = db.get("PM_GROUP_ID") or Var.PM_GROUP_ID
FORUM_TOPIC = db.get("FORUM_TOPIC") or Var.FORUM_TOPIC
MAX_WARNING = db.get("MAX_WARNING") or Var.MAX_WARNING

if not Var.OWNER_ONLY:
    ADMINS = db.get("ADMINS", [])
    if isinstance(ADMINS, list):
        AUTH_LIST.extend(x for x in ADMINS)
    elif isinstance(ADMINS, str):
        AUTH_LIST.append(ADMINS)


# For caching some data to make modules work faster.
_module_cache: dict[str, object] = {}
module_cache = TempCache(_module_cache)
bot_cache = TempCache(_bot_cache)
LOADED = bot_cache.get("loaded_modules")
