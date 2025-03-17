"""
This module contains global variables, modules cache, and commonly used imports.
"""

from tgbot import DB, Bot, Var
from tgbot.utils import LOGS
from tgbot.utils.helpers import (
    KeepSafe,
    TempCache,
    _util_cache,
    censors,
    is_dangerous,
    load_modules,
)

# Variables
LOG_CHANNEL = DB.get_key("LOG_CHANNEL") or Var("LOG_CHANNEL")
PREFIXES = DB.get_key("PREFIXES") or Var("PREFIXES")
OWNER_ID = Var("OWNER_ID")

# Prefix formatting.
if "/" in PREFIXES:
    # Use '/' if available. (Telegram standard)
    i = sorted(PREFIXES, key=lambda x: x != "/")[0]
else:
    i = PREFIXES[0]

# For caching some data to make modules work faster.
__cache: dict[str | int, any] = {}
module_cache = TempCache(__cache)

__all__ = (
    "Bot",
    "DB",
    "Var",
    "is_dangerous",
    "LOG_CHANNEL",
    "OWNER_ID",
    "LOGS",
    "load_modules",
    "i",
    "_util_cache",
    "module_cache",
    "KeepSafe",
    "censors",
)

LOADED = _util_cache.dict.get("loaded_modules")
