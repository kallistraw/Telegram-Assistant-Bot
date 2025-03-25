# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""This module contains the core functions of the bot."""

from enum import Enum
from os import path

from tgbot.core.database import SQLite
from tgbot.utils import LOGS

__all__ = ("BotConfig", "get_database")


_file = path.dirname(path.abspath(__file__))
_root = path.abspath(path.join(_file, "../.."))


# Lazy loading database instance
_DB_INSTANCE = None


def get_database():
    """Returns the database instance."""
    global _DB_INSTANCE  # pylint: disable=global-statement
    if _DB_INSTANCE is None:
        _DB_INSTANCE = SQLite(logger=LOGS)
        return _DB_INSTANCE
    return _DB_INSTANCE


# Do NOT overwrite the attribute names
class BotConfig(Enum):
    """
    This enum contains the bot's global configuration.
    """

    # You should not edit the configuration defined below.
    # You can configure the bot within the bot itself.
    # See the `settings` command help message for more information.

    THUMBNAIL = path.abspath(path.join(_root, "assets/thumbnail.jpeg"))
    """
    :obj:`str`: The path to image that will be used for a thumbnail when the bot send a documents.

    Note:
        If you set your thumbnail manually for whatever reason, please make sure that it is in
        JPEG formats and less than 200 KiB in size. The thumbnail's height and width should not
        exceed 320.
    """

    def __str__(self):
        return str(self.value)  # Ensure string output
