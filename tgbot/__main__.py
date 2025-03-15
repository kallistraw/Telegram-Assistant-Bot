"""This module serves as the main entry point."""

import asyncio


async def main():
    """This function is the main function to start the bot."""
    # pylint: disable=import-outside-toplevel
    import os
    import sys
    import time

    # Core imports
    from . import Bot
    from . import DB

    # Utility imports
    from .utils import load_modules, LOGS

    # Misc imports
    from . import StartTime

    # Update the bot (if any) when restarting.
    if DB.get_key("UPDATE_ON_RESTART") and os.path.exists(".git"):
        pass  # TODO

    LOGS.info("Initializing...")

    load_modules()

    _time_taken = f"Bot started in {StartTime - time.time() * 1000}"
    _success = """
            ——————————————————————————————————————————————————————————————————————
                   Your bot is now online! Check your log group for cookies!
            ——————————————————————————————————————————————————————————————————————
        """

    _no_log = DB.get_key("NO_LOG_MSG")

    # Send deploy message to Telegram if 'NO_LOG_MSG' is not set or not True
    if not _no_log or _no_log.lower() != "true":
        pass  # TODO

    LOGS.info(_time_taken)
    LOGS.info(_success)
    await Bot.run()


if __name__ == "__main__":
    asyncio.run(main())
