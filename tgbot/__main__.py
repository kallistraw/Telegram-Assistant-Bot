# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
# pylint: disable=C0415
"""This module serves as the main entry point."""
from tgbot.utils import LOGS

LOGS.info("Initializing...")
_SUCCESS = """
        ——————————————————————————————————————————————————————————————————————
               Your bot is now online! Check your log group for cookies!
        ——————————————————————————————————————————————————————————————————————
    """


def main():
    """The main function to update the source, load modules, and start the bot"""
    import os
    import time

    from telegram import Update

    from tgbot import StartTime, bot, database
    from tgbot.utils.loader import load_modules

    # Update the bot (if any) when restarting.
    if database.get("UPDATE_ON_RESTART") and os.path.exists(".git"):
        pass

    load_modules("modules")

    _no_log = database.get("NO_LOG_MSG")

    # Send deploy message to Telegram if 'NO_LOG_MSG' hasn't been set yet or is False
    if not _no_log or _no_log.lower() != "true":
        pass

    _time_taken = f"Bot started in {(time.time() - StartTime) * 1000}"
    LOGS.info(_time_taken)
    LOGS.info(_SUCCESS)
    bot.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
