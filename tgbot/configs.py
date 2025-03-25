# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
# pylint: disable=too-few-public-methods
"""This module contains the `ConfigVars` class."""

from decouple import config


class ConfigVars:
    """
    This class is used to fetch environment variables and set a default values.
    """

    # Mandatory
    BOT_TOKEN = (config("BOT_TOKEN", default=None),)
    OWNER_ID = (config("OWNER_ID", cast=int, default=0),)
    _LOG = (config("LOG_GROUP_ID", default=""),)

    # Optional
    PREFIXES = (config("PREFIXES", cast=lambda v: v.split(), default="/"),)
    OWNER_ONLY = (config("OWNER_ONLY", cast=bool, default=True),)
    FORUM_TOPIC = (config("FORUM_TOPIC", cast=bool, default=False),)
    PM_GROUP_ID = (config("PM_GROUP_ID", cast=int, default=0),)
    MAX_WARNING = (config("MAX_WARNING", cast=int, default=3),)

    # Convert LOG_GROUP_ID to integer or default to OWNER_ID
    try:
        LOG_GROUP_ID = int(_LOG)
    except ValueError:
        LOG_GROUP_ID = OWNER_ID
