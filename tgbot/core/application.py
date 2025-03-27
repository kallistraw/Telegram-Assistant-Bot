# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""This module contain the telegram.ext.Application subclass."""

import asyncio
from contextlib import asynccontextmanager
from functools import wraps
from html import escape
from io import BytesIO
from logging import Logger
from re import Pattern
import traceback
from typing import Any, Callable, Collection, Optional, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.constants import ParseMode
from telegram.error import RetryAfter
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    PrefixHandler,
    filters,
)

from tgbot.configs import ConfigVars
from tgbot.core import BotConfig, get_database
from tgbot.utils import LOGS

database = get_database()

__all__ = [
    "TelegramApplication",
]

Var = ConfigVars()


class ConversationManager:  # pylint: disable=R0903
    """A very simple conversation manager using `asyncio.Queue()`"""

    def __init__(self, chat_id: int, timeout: Optional[int] = 300) -> None:
        self.chat_id = chat_id
        self.queue = asyncio.Queue()
        self.timeout = timeout

    async def wait_update(self) -> Union[Update, None]:
        """Wait for the next message with a timeout."""
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
        except asyncio.TimeoutError:
            return None  # Return None if the user takes too long


class TelegramApplication(Application):
    """
    A very simple subclass of telegram.ext.Application with Pyrogram-style decorators.
    """

    def __init__(self, log_group_id: int, logger: Logger = LOGS, **kwargs) -> None:
        super().__init__(**kwargs)
        self._convo: dict[Any, Any] = {}
        self.log_group_id: int = log_group_id
        self.bot_info: Optional[User] = None
        self.logger: Logger = logger
        self._msg_handler: Optional[MessageHandler] = None

        self.logger.info("Initializing Application...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._async_init())
        self.add_error_handler(self.error_handler)

    # Copies Telethon's `TelegramClient.converation()` behavior
    @asynccontextmanager
    async def conversation(self, chat_id: int, timeout: Optional[int] = 300) -> None:
        """
        Async conversation manager with timeout.

        Arguments:
            chat_id (int): The chat ID to hold a conversation to.
            timeout (int, optional): How long (in seconds) the bot should hold the conversation.
                Defaults to `300` (5 minutes)
        """
        conv = ConversationManager(chat_id, timeout)
        self._convo[chat_id] = conv

        if not hasattr(self, "_msg_handler"):
            self._msg_handler = MessageHandler(
                filters.ChatType.PRIVATE, self._handle_update
            )
            self.add_handler(self._msg_handler)

        try:
            yield conv
        finally:
            del self._convo[chat_id]

            # Remove handler if there's no active conversations
            if not self._convo:
                self.remove_handler(self._msg_handler)
                del self._msg_handler

    async def _handle_update(self, update: Update):
        """Routes incoming updates to the correct conversation queue."""
        chat_id = update.message.chat_id
        if chat_id in self._convo:
            await self._convo[chat_id].queue.put(update)

    async def _async_init(self) -> None:
        """
        Asynchronously initialize the bot and fetch its info.
        """
        await self.bot.initialize()

        self.bot_info = await self.bot.get_me()
        me = self.bot_info
        self.logger.info("Bot initialized! Username: @%s, ID: %s", me.username, me.id)
        return

    def _dynamic_filter(
        self,
        owner_only: bool = False,
        admins_only: bool = False,
        fltrs: Optional[filters.BaseFilter] = None,
    ) -> Optional[filters.BaseFilter]:
        """
        Dynamically return telegram.ext.filters.MessageFilter.
        """
        owner = Var.OWNER_ID
        extra_filter = fltrs

        if owner_only:
            extra_filter = (
                (extra_filter & filters.User(owner))
                if extra_filter
                else filters.User(owner)
            )

        if admins_only:
            get_admins = database.get("ADMINS", [])
            if get_admins:
                admins = [int(x) for x in get_admins]
                admins.append(owner)
                dev_filter = filters.User(admins)
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

    async def error_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Error handler to catch an exception and send them to the log group.
        """
        self.logger.error(
            "An error occured while handling an update:", exc_info=context.error
        )

        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_str = "".join(tb_list)
        # update_str = update.to_dict() if isinstance(update, Update) else str(update)
        text = update.effective_message
        chat = update.effective_chat
        user = update.effective_sender

        err = (
            "⚠️ <b>An error Occurred</b>\n\n"
            f"<b>Chat:</b> <code>{escape(chat.effective_name)} (chat.id)</code>\n"
            f"<b>From user:</b> {user.mention_html()}\n"
            f"<b>Message:</b> <code>{escape(text)}</code>\n"
            # f"<pre>{escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        )

        error_message = err + f"\n<pre>{escape(tb_str)}</pre>"

        if self.log_group_id:
            if len(error_message) > 4096:
                get_thumb = database.get("CUSTOM_THUMBNAIL")
                thumb = BotConfig.THUMBNAIL if get_thumb else None
                with BytesIO(tb_str.encode()) as tb_file:
                    tb_file.name = "traceback.txt"
                    try:
                        await context.bot.send_document(
                            self.log_group_id,
                            tb_file,
                            caption=err,
                            parse_mode=ParseMode.HTML,
                            thumbnail=thumb,
                        )
                    except RetryAfter as re:
                        self.logger.error(
                            "Flood control exceeded. Sleeping for %s seconds",
                            re.retry_after,
                        )
                        await asyncio.sleep(re.retry_after)
                        await context.bot.send_document(
                            self.log_group_id,
                            tb_file,
                            caption=err,
                            parse_mode=ParseMode.HTML,
                            thumbnail=thumb,
                        )
                return
            try:
                await context.bot.send_message(
                    self.log_group_id,
                    error_message,
                    parse_mode=ParseMode.HTML,
                )
            except RetryAfter as re:
                self.logger.error(
                    "Flood control exceeded. Sleeping for %s seconds",
                    re.retry_after,
                )
                await asyncio.sleep(re.retry_after)
                await context.bot.send_message(
                    self.log_group_id,
                    error_message,
                    parse_mode=ParseMode.HTML,
                )

    def on_command(
        self,
        commands: Union[str, Collection[str]],
        prefixes: Optional[Union[str, Collection[str]]] = None,
        **kwargs,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for handling commands.
        For more information, read the official telegram.ext.PrefixHandler documentation.

        Arguments:
            commands (str | Collection[str]): Command names
                (e.g., 'start' or ['ping', 'p']).
            prefixes (str | Collection[str], optional): Allowed prefixes (e.g., '/' or ['/', '!']).
                Defaults to the value of PREFIXES in the database or in .env file. If not present
                in the database or .env file, will use '/'.

        Keyword arguments:
            owner_only (bool, optional): Whether the command should only work for the bot's owner.
                Defaults to False.
            admins_only (bool, optional): Whether the command should only work for the bot's owner
                and admins. Defaults to False. See the auth command help message for more details.
            chat_type (str, optional): If set to "group" the command will only work in groups. If
                set to "private", will only work in private messages. Defaults to None.
            filters (telegram.ext.filters, optional): Additional telegram.ext.filters for filtering
                messages. Defaults to None.
        """
        prefixes = prefixes or database.get("PREFIXES") or Var.PREFIXES
        owner_only = kwargs.get("owner_only", False)
        admins_only = kwargs.get("admins_only", False)
        chat_type = kwargs.get("chat_type", None)
        fltrs = kwargs.get("filters", None)
        if isinstance(prefixes, str):
            prefixes = list(prefixes)

        # Append '/' to the prefixes since it is the most common prefixes
        if "/" not in prefixes:
            prefixes.append("/")

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(
                update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
            ):
                owner = Var.OWNER_ID
                user = update.message.from_user
                is_group = update.message.chat.type in ["group", "supergroup"]

                if owner_only and user.id != owner:
                    await update.message.reply_text(
                        "You are not authorized to use this command."
                    )
                    return

                if admins_only:
                    get_admins = database.get("ADMINS") or []
                    admins = [int(x) for x in get_admins]
                    admins.append(owner)

                    if user.id not in admins:
                        await update.message.reply_text(
                            "You are not authorized to use this command"
                        )
                        return

                if chat_type and chat_type.lower() == "private" and is_group:
                    bot_username = context.bot.username
                    command = update.message.text.split()[0]

                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Click Me!",
                                url=f"https://t.me/{bot_username}?start={command[1:]}",
                            )
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    name = escape(user.full_name)

                    await update.message.reply_text(
                        f"Heya {name}! This command only work in private chat."
                        "\nClick the button bellow to use this command.",
                        reply_markup=reply_markup,
                    )
                    return

                if chat_type and chat_type.lower() == "group" and not is_group:
                    await update.message.reply_text(
                        f"Heya {escape(user.full_name)}! This command only work in group chat."
                    )
                    return

                return await func(update, context, *args, **kwargs)

            self.add_handler(
                PrefixHandler(prefixes, commands, callback=wrapper, filters=fltrs),
                group=0,
            )
            return wrapper

        return decorator

    def on_message(
        self, **kwargs
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for handling messages.

        Keyword Arguments:
            owner_only (bool, optional): Whether the handler should only work for the bot's owner.
                Defaults to False.
            admins_only (bool, optional): Whether the handler should only work for the bot's owner
                and developers. Defaults to False. See the auth command help message for more \
                details.
            filters (telegram.ext.filters, optional): Additional telegram.ext.filters for filtering
                messages. Defaults to None.
        """
        owner_only = kwargs.get("owner_only", False)
        admins_only = kwargs.get("admins_only", False)
        fltrs = kwargs.get("filters", None)

        extra_filter = self._dynamic_filter(owner_only, admins_only, fltrs)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(
                update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
            ):
                return await func(update, context, *args, **kwargs)

            self.add_handler(
                MessageHandler(callback=wrapper, filters=extra_filter), group=1
            )
            return wrapper

        return decorator

    def on_inline(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for handling inline queries.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(
                update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
            ):
                return await func(update, context, *args, **kwargs)

            self.add_handler(InlineQueryHandler(callback=wrapper))
            return wrapper

        return decorator

    def on_callback(
        self,
        pattern: Optional[
            Union[str, Pattern[str], type, Callable[[object], Optional[bool]]]
        ] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for handling button callback queries.

        Arguments:
            pattern (str | re.Pattern <re.compile> | callable | type, optional):
                Pattern to test the callback query data against. For more information, please refer
                to telegram.ext.CallbackQueryHandler documentation.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(
                update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
            ):
                return await func(update, context, *args, **kwargs)

            self.add_handler(CallbackQueryHandler(callback=wrapper, pattern=pattern))
            return wrapper

        return decorator

    def run(self):
        """
        Starts the bot with polling.
        """
        self.run_polling()
