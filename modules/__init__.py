"""
This module contains global variables, modules cache, and most common imports.
"""

from tgbot import Bot
from tgbot import DB
from tgbot import Var
from tgbot.utils import is_dangerous
from tgbot.utils import load_modules
from tgbot.utils import LOGS

# Variables
LOG_CHANNEL = Var("LOG_CHANNEL")
OWNER_ID = Var("OWNER_ID")
PREFIXES = DB.get_key("PREFIXES") or Var("PREFIXES")

if "/" in PREFIXES:
    # Use '/' if available. (Telegram standard)
    i = sorted(PREFIXES, key=lambda x: x != "/")[0]
else:
    i = PREFIXES[0]

# For caching some data to make modules work faster.
_tgbot_cache: dict[any, any | None] = {}
