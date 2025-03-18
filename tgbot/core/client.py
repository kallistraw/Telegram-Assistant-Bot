"""This module contain the Python-Telegram-Bot's `Application` (bot) wrapper."""

import asyncio
from enum import Enum
from functools import wraps
from io import BytesIO
from logging import Logger
import os
import traceback

from telegram.constants import ParseMode
from telegram.error import InvalidToken, RetryAfter
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    InlineQueryHandler,
    MessageHandler,
    PrefixHandler,
    filters,
)
from telegram.ext.filters import MessageFilter

from tgbot.configs import get_var
from tgbot.core.database import bot_db
from tgbot.utils import LOGS

__all__ = ("Client", "BotConfig")

Var = get_var()
DB = bot_db()

_file = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_file, "../.."))


# Do NOT overwrite the argument names
class BotConfig(Enum):
    """
    This enum contains the bot's global configuration.

    You should not overwrite the value of the p, you can customize the bot's
    configuration within the bot itself.
    See the `settings` command help message for more information.
    """

    __slots__ = ()

    CUSTOM_THUMBNAIL = os.path.abspath(os.path.join(_root, "assets/thumbnail.jpeg"))
    """
    :obj:`str`: The path to image that is used as a thumbnail when the bot send a documents.

    Note:
        If you set your thumbnail manually for whatever reason, please make sure that it is in
        JPEG formats and less than 200 KiB in size. The thumbnail's width should not exceed 320.
    """

    LANGUAGE = "en"
    """
    :obj:`str`: The preferred language used by the bot.

    Note:
        This feature is still under development and currently only supports `EN`.
        Languages to be added in the future:
          - `ID`
          - `ZH`

        If you want to contribute in the translation, please see the `README` at
        https://github.com/kallistraw/Telegram-Assistant-Bot/strings/README.md
    """

    def __str__(self):
        return str(self.value)  # Ensure string output


class Client:
    """
    A very simple Python-Telegram-Bot's `Application` (bot) wrapper with Pyrogram-style decorators.
    """

    def __init__(self, token: str, log_channel: int = None, logger: Logger = LOGS):
        self._cache: dict[str, str | None] = {}
        self.application = Application.builder().token(token).build()
        self.log_channel = log_channel
        self.bot = self.application.bot
        self.bot_info = None
        self.logger = logger

        self.logger.info("Initializing bot client...")

        # Check for an existing event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._async_init())
        except RuntimeError:
            asyncio.run(self._async_init())

    async def _async_init(self):
        """
        Asynchronously initialize the bot and fetch its info.
        """
        try:
            await self.application.initialize()
            await self.application.start()
        except InvalidToken:
            self.logger.error(
                "The bot token is expired or invalid."
                "Get a new one from @BotFather and add it in .env file!"
            )
            import sys  # pylint: disable=import-outside-toplevel

            sys.exit(1)

        self.bot_info = await self.bot.get_me()
        me = self.bot_info
        self.logger.info("Bot initialized! Username: @%s, ID: %s", me.username, me.id)

    def __repr__(self):
        name = f"@{self.bot_info.username}" if self.bot_info else "Unknown"
        return f"<Telegram.Client name: {name}>"

    def _error_handler(self, func):
        """
        Wrapper to catch errors and send them to the log group.
        """

        @wraps(func)
        async def wrapper(update, context):
            try:
                return await func(update, context)
            except Exception as e:
                # We seperating the header and the traceback.
                # If the message is exceeding Telegram character limit (4096),
                # will write the traceback into a temporary file and send it with the
                # header as a caption for better readability.
                err = (
                    f"⚠️ **Error Occurred**\n\n"
                    f"📌 **Function:** `{func.__name__}`\n"
                    f"❌ **Error:** `{str(e)}`"
                )

                tb = traceback.format_exc()
                error_message = f"{err}\n\n```{tb}```"

                if self.log_channel:
                    if len(error_message) > 4096:
                        get_thumb = DB.get("CUSTOM_THUMBNAIL")
                        thumb = BotConfig.CUSTOM_THUMBNAIL if get_thumb else None
                        with BytesIO(tb.encode()) as tb_file:
                            tb_file.name = "Traceback.txt"
                            try:
                                await context.bot.send_document(
                                    self.log_channel,
                                    tb_file,
                                    caption=err,
                                    parse_mode=ParseMode.MARKDOWN_V2,
                                    thumbnail=thumb,
                                )
                            except RetryAfter as re:
                                self.logger.error(
                                    "Flood control exceeded. Sleeping for %s seconds",
                                    re.retry_after,
                                )
                                await asyncio.sleep(re.retry_after)
                                await context.bot.send_document(
                                    self.log_channel,
                                    tb_file,
                                    caption=err,
                                    parse_mode=ParseMode.MARKDOWN_V2,
                                    thumbnail=thumb,
                                )
                        return
                    try:
                        await context.bot.send_message(
                            self.log_channel,
                            error_message,
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                    except RetryAfter as re:
                        self.logger.error(
                            "Flood control exceeded. Sleeping for %s seconds",
                            re.retry_after,
                        )
                        await asyncio.sleep(re.retry_after)
                        await context.bot.send_message(
                            self.log_channel,
                            error_message,
                            parse_mode=ParseMode.MARKDOWN,
                        )
                self.logger.error(error_message)

        return wrapper

    def _dynamic_filter(self, owner_only=False, devs_only=False, fltrs=None):
        """
        Dynamically return :obj:`telegram.ext.filters.MessageFilter`.
        """
        owner = int(Var("OWNER_ID"))
        extra_filter = fltrs

        if owner_only:
            extra_filter = (
                (extra_filter & filters.User(owner))
                if extra_filter
                else filters.User(owner)
            )

        if devs_only:
            get_devs = DB.get("DEVS")
            if get_devs:
                devs = [int(x) for x in get_devs]
                devs.append(owner)
                dev_filter = filters.User(devs)
                extra_filter = (
                    (extra_filter & dev_filter) if extra_filter else dev_filter
                )
            else:
                extra_filter = (
                    (extra_filter & filters.User(owner))
                    if extra_filter
                    else filters.User(owner)
                )
        return extra_filter

    def on_cmd(
        self, commands: str | list[str], prefixes: str | list[str] = None, **kwargs
    ):
        """
        Decorator for handling commands.

        Arguments:
            commands (:obj:`str` or :obj:`list` of :obj:`str`):
                Command names (e.g., `'start'` or `['ping', 'p']`).
            prefixes (:obj:`str` or :obj:`list` of :obj:`str`, optional):
                Allowed prefixes (e.g., `'/'` or `['/', '!']`). Defaults to `'/'`.

        Keyword arguments:
            owner_only (:obj:`bool`, optional):
                Whether the command should only work for the bot's owner. Defaults to ``False``.
            devs_only (:obj:`bool`, optional):
                Whether the command should only work for the bot's owner and developers.
                Defaults to ``False``. See the `auth` command help message for more details.
            fltrs (:obj:`telegram.ext.filters.MessageFilter`, optional):
                Additional `telegram.ext.filters` for filtering messages. Defaults to ``None``.
        """
        prefixes = prefixes or DB.get("PREFIXES") or Var("PREFIXES")
        owner_only = kwargs.get("owner_only", False)
        devs_only = kwargs.get("devs_only", False)
        fltrs = kwargs.get("filters", None)
        extra_filter = self._dynamic_filter(owner_only, devs_only, fltrs)

        def decorator(func):
            wrapped_func = self._error_handler(func)

            self.application.add_handler(
                PrefixHandler(
                    prefixes,
                    commands,
                    callback=wrapped_func,
                    filters=extra_filter,
                )
            )
            return wrapped_func

        return decorator

    def on_msg(
        self,
        owner_only: bool = False,
        devs_only: bool = False,
        fltrs: MessageFilter = None,
    ):
        """
        Decorator for handling messages.

        Arguments:
            owner_only (:obj:`bool`, optional):
                Whether the handler should only work for the bot's owner. Defaults to ``False``.
            devs_only (:obj:`bool`, optional):
                Whether the handler should only work for the bot's owner and developers.
                Defaults to ``False``. See the `auth` command help message for more details.
            fltrs (:obj:`telegram.ext.filters.MessageFilter`, optional):
                Additional `telegram.ext.filters` for filtering messages. Defaults to ``None``.
        """

        extra_filter = self._dynamic_filter(owner_only, devs_only, fltrs)

        def decorator(func):
            wrapped_func = self._error_handler(func)
            self.application.add_handler(
                MessageHandler(callback=wrapped_func, filters=extra_filter)
            )
            return wrapped_func

        return decorator

    def on_inline(
        self,
    ):
        """
        Decorator for handling inline queries.
        """

        def decorator(func):
            wrapped_func = self._error_handler(func)
            self.application.add_handler(InlineQueryHandler(callback=wrapped_func))
            return wrapped_func

        return decorator

    def on_callback(
        self,
    ):
        """
        Decorator for handling button callback queries.
        """

        def decorator(func):
            wrapped_func = self._error_handler(func)
            self.application.add_handler(CallbackQueryHandler(callback=wrapped_func))
            return wrapped_func

        return decorator

    def run(self):
        """
        Starts the bot with polling.
        """
        self.application.run_polling()
