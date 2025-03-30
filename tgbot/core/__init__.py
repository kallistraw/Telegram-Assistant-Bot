# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""This module contains the core functions of the bot."""

from os import path

from telegram._utils.enum import StringEnum

from tgbot.configs import ConfigVars as Var
from tgbot.core.database import MongoDB, PostgreSQL, SQLite

__all__ = ("BotConfig", "get_database")


_file = path.dirname(path.abspath(__file__))
_root = path.abspath(path.join(_file, "../.."))


# Lazy loading database instance
_DB_INSTANCE = None


def get_database():
    """Returns the database instance."""
    global _DB_INSTANCE  # pylint: disable=W0603
    if _DB_INSTANCE is None:
        if Var.DATABASE_URL:
            _DB_INSTANCE = PostgreSQL(Var.DATABASE_URL)
        elif Var.MONGO_URI:
            _DB_INSTANCE = MongoDB(Var.MONGO_URI)
        else:
            _DB_INSTANCE = SQLite()
        return _DB_INSTANCE
    return _DB_INSTANCE


# Do NOT overwrite the attribute names
class BotConfig(StringEnum):  # pylint: disable=E0244
    """
    This enum contains the bot's global configuration.
    """

    THUMBNAIL: str = str(path.abspath(path.join(_root, "assets/thumbnail.jpeg")))
    """
    :obj:`str`: The path to image that will be used for a thumbnail when the bot send a documents.

    Note:
        If you set your thumbnail manually for whatever reason, please make sure that it is in
        JPEG formats and less than 200 KiB in size. The thumbnail's height and width should not
        exceed 320.
    """
