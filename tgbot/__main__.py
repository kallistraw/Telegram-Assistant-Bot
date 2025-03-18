"""This module serves as the main entry point."""

import os
import time


def main():
    """The main function to update the source, load modules, and start the bot"""
    # pylint: disable=import-outside-toplevel
    from tgbot import DB, Bot, StartTime
    from tgbot.utils import LOGS
    from tgbot.utils.helpers import load_modules

    # Update the bot (if any) when restarting.
    if DB.get_key("UPDATE_ON_RESTART") and os.path.exists(".git"):
        pass

    LOGS.info("Initializing...")

    load_modules("modules")

    _time_taken = f"Bot started in {StartTime - time.time() * 1000}"
    _success = """
            ——————————————————————————————————————————————————————————————————————
                   Your bot is now online! Check your log group for cookies!
            ——————————————————————————————————————————————————————————————————————
        """

    _no_log = DB.get_key("NO_LOG_MSG")

    # Send deploy message to Telegram if 'NO_LOG_MSG' hasn't been set yet or is False
    if not _no_log or _no_log.lower() != "true":
        pass

    LOGS.info(_time_taken)
    LOGS.info(_success)
    Bot.run()


if __name__ == "__main__":
    main()
