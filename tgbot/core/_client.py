"""This module contain the Python-Telegram-Bot's Application wrapper."""

import asyncio
import traceback
from functools import wraps
from logging import Logger

from telegram.ext import Application
from telegram.ext import CallbackQueryHandler
from telegram.ext import filters
from telegram.ext import InlineQueryHandler
from telegram.ext import MessageHandler

from .. import DB
from .. import Var
from ..utils import LOGS


class PrefixCommandFilter:
    """
    Message filtering for `on_cmd` to support multiple prefixes and filters.
    """

    def __init__(self, commands, prefixes, extra_filter=None):
        self.commands = set(commands)
        self.prefixes = set(prefixes)
        self.extra_filter = extra_filter

    def _filter(self, message):
        if not message.text:
            return False
        text = message.text.strip()

        for prefix in self.prefixes:
            if text.startswith(prefix):
                cmd = text[len(prefix)].split()[0]
                if cmd in self.commands:
                    return self.extra_filter(message) if self.extra_filter else True

        return False


class Client:
    """
    A very simple PTB client wrapper with Pyrogram-style decorators.
    """

    def __init__(self, token, log_channel=None, logger: Logger = LOGS, **kwargs):
        """
        Initializes the bot with the given token.

        Args:
            token (str): Telegram bot token.
            log_channel (int): Telegram group ID where errors will be logged.
        """
        self._cache: dict[str, str | None] = {}
        self.application = Application.builder().token(token).build()
        self.log_channel = log_channel
        self.bot = self.application.bot
        self.bot_info = None
        self.logger = logger

        asyncio.create_task(self._async_init())

    async def _async_init(self):
        """
        Asynchronously initialize the bot and fetch its info.
        """
        try:
            self.logger.info("Starting bot client...")
            await self.application.initialize()
            await self.application.start()
        except BaseException as e:
            self.logger.error(
                "The bot token is expired or invalid"
                "get a new one from @BotFather and add it at .env file in BOT_TOKEN!"
            )
            self.logger.error(e)
            import sys  # pylint: disable=import-outside-toplevel

            sys.exit()

        self.bot_info = await self.bot.get_me()
        me = self.bot_info
        self.logger.info(f"Bot started! Username: @{me.username}, ID: {me.id}")

    def __repr__(self):
        name = f"@{self.bot_info.username}" if self.bot_info else "Unknown"
        return f"<Telegram.Client\n name: {name}\n>"

    def error_handler(self, func):
        """
        Wrapper to catch errors and send them to the log group.
        """

        @wraps(func)
        async def wrapper(update, context):
            try:
                return await func(update, context)
            except Exception as e:
                error_message = (
                    f"⚠️ **Error Occurred**\n\n"
                    f"📌 **Function:** `{func.__name__}`\n"
                    f"❌ **Error:** `{str(e)}`\n\n"
                    f"```{traceback.format_exc()}```"
                )

                if self.log_channel:
                    await context.bot.send_message(
                        self.log_channel, error_message, parse_mode="Markdown"
                    )
                else:
                    self.logger.error(error_message)

        return wrapper

    def on_cmd(
        self,
        commands=None,
        prefixes=None,
        owner_only=False,
        dev_only=False,
        *args,
    ):
        """
        Decorator for handling commands.
        Args:
            commands (str | list[str]):
              -Command names (e.g., 'start' or ['ping', 'p'])
            prefixes (str | list[str]):
              - Allowed prefixes (e.g., '/' or ['/', '!'], default = '/')
            group_only (bool):
              - If set to True, commands will only works in groups.
            owner_only (bool):
              - If set to True, commands will only works for the bot's owner.
            dev_only (boo):
              - If set to True, commands will only works for the bot's owner and devs.
              - Check the help message for `auth` command for more info.
            - Additionally, you can pass `telegram.ext.filters` here.
        """
        commands = commands or []
        prefixes = prefixes or DB.get("PREFIXES") or Var("PREFIXES")

        def dynamic_filter(update):
            extra_filter = args[0] if args else None
            for f in args[1:]:
                extra_filter &= f  # Combine multiple filters

            if owner_only:
                owner = int(Var("OWNER_ID"))
                extra_filter = (
                    (extra_filter & filters.User(owner))
                    if extra_filter
                    else filters.User(owner)
                )

            if dev_only:
                get_devs = DB.get("DEVS")
                if get_devs:
                    devs = [int(x) for x in get_devs]
                    owner = int(Var("OWNER_ID"))
                    devs.append(owner)
                    dev_filter = filters.User(devs)
                    extra_filter = (
                        (extra_filter & dev_filter) if extra_filter else dev_filter
                    )
                else:
                    self.logger.info(
                        "Dev list returned 'None', skipping 'dev_only' check for now."
                    )

            return extra_filter(update) if extra_filter else True

        def decorator(func):
            wrapped_func = self.error_handler(func)

            command_filter = PrefixCommandFilter(
                commands, prefixes, filters.create(dynamic_filter)
            )

            self.application.add_handler(
                MessageHandler(
                    filters.TEXT & filters.UpdateType.MESSAGE & command_filter,
                    wrapped_func,
                )
            )
            return wrapped_func

        return decorator

    def on_msg(self, *args):
        """
        Decorator for handling messages.
        """

        extra_filter = args[0] if args else None
        for f in args[1:]:
            extra_filter &= f

        def decorator(func):
            wrapped_func = self.error_handler(func)
            self.application.add_handler(MessageHandler(extra_filter, wrapped_func))
            return wrapped_func

        return decorator

    def on_inline(self):
        """
        Decorator for handling inline queries.
        """

        def decorator(func):
            wrapped_func = self.error_handler(func)
            self.application.add_handler(InlineQueryHandler(wrapped_func))
            return wrapped_func

        return decorator

    def on_callback(self):
        """
        Decorator for handling button callback queries.
        """

        def decorator(func):
            wrapped_func = self.error_handler(func)
            self.application.add_handler(CallbackQueryHandler(wrapped_func))
            return wrapped_func

        return decorator

    async def run(self):
        """
        Starts the bot with polling.
        """
        await self.application.run_polling()
