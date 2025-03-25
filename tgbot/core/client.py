# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""This module contain the :class:`telegram.ext.Application` subclass."""

import asyncio
from functools import wraps
from html import escape
from io import BytesIO
from logging import Logger
from re import Pattern
import sys
import traceback
from typing import Any, Callable, Collection, Optional, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import InvalidToken, RetryAfter
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
    "Client",
]

Var = ConfigVars()


class Client(Application):
    """
    A very simple subclass of `telegram.ext.Application` with Pyrogram-style decorators.
    """

    def __init__(self, log_group_id: int, logger: Logger = LOGS, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cache: dict[str | int, Any] = {}
        self.log_group_id = log_group_id
        self.bot_info = None
        self.logger = logger

        self.logger.info("Initializing bot client...")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._async_init())
        self.add_error_handler(self.error_handler)

    async def _async_init(self) -> None:
        """
        Asynchronously initialize the bot and fetch its info.
        """
        try:
            await self.bot.initialize()
        except InvalidToken:
            self.logger.error(
                "Your bot token is invalid/expired,"
                "get a new one from @BotFather and put it in the .env file."
            )
            sys.exit(1)

        self.bot_info = await self.bot.get_me()
        me = self.bot_info
        self.logger.info("Bot initialized! Username: @%s, ID: %s", me.username, me.id)
        return

    def __repr__(self) -> str:
        name = f"@{self.bot_info.username}" if self.bot_info else "Unknown"
        return f"<Telegram.Client name: {name}>"

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
        text = update.message.text
        chat = update.message.chat
        user = update.message.from_user

        err = (
            "⚠️ <b>An error Occurred</b>\n\n"
            f"<b>Chat:</b> <code>{escape(chat.title)} (chat.id)</code>\n"
            f"<b>From user:</b> <a href='tg://user?id={user.id}'>{escape(user.first_name)}</a>\n"
            f"<b>Message:</b> <code>{escape(text)}</code>\n"
            # f"<pre>{escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        )

        error_message = err + f"\n\n<pre>{escape(tb_str)}</pre>"

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

    def _dynamic_filter(
        self,
        owner_only: bool = False,
        admins_only: bool = False,
        fltrs: Optional[filters.BaseFilter] = None,
    ) -> Optional[filters.BaseFilter]:
        """
        Dynamically return :obj:`telegram.ext.filters.MessageFilter`.
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

    def on_command(
        self,
        commands: Union[str, Collection[str]],
        prefixes: Optional[Union[str, Collection[str]]],
        **kwargs,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for handling commands.
        For more information, read the official :class:`telegram.ext.PrefixHandler` documentation.

        Arguments:
            commands (:obj:`str` | Collection[:obj:`str`]): Command names
                (e.g., ``'start'`` or ``['ping', 'p']``).
            prefixes (:obj:`str` | Collection[:obj:`str`], optional): Allowed prefixes
                (e.g., ``'/'`` or ``['/', '!']``). Defaults to the value of ``PREFIXES`` in the
                database or in `.env` file. If not present in the database or `.env` file, will
                use `'/'`.

        Keyword arguments:
            owner_only (:obj:`bool`, optional): Whether the command should only work for the bot's
                owner. Defaults to ``False``.
            admins_only (:obj:`bool`, optional): Whether the command should only work for the bot's
                owner and admins. Defaults to ``False``. See the `auth` command help message for
                more details.
            chat_type (:obj:`str`, optional): If set to `"group"` the command will only work in
                groups. If set to `"private"`, will only work in private messages. Defaults to
                ``None``.
            filters (:mod:`telegram.ext.filters`, optional): Additional :mod:`telegram.ext.filters`
                for filtering messages. Defaults to ``None``.
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

        @wraps
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

                if chat_type.lower() == "private" and is_group:
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

                if chat_type.lower() == "group" and not is_group:
                    await update.message.reply_text(
                        f"Heya {escape(user.full_name)}! This command only work in group chat."
                    )
                    return

                return await func(update, context, *args, **kwargs)

            self.add_handler(
                PrefixHandler(prefixes, commands, callback=wrapper, filters=fltrs)
            )
            return wrapper

        return decorator

    def on_message(
        self, **kwargs
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for handling messages.

        Keyword Arguments:
            owner_only (:obj:`bool`, optional): Whether the handler should only work for the bot's
                owner. Defaults to ``False``.
            admins_only (:obj:`bool`, optional): Whether the handler should only work for the bot's
                owner and developers. Defaults to ``False``. See the `auth` command help message
                for more details.
            filters (:mod:`telegram.ext.filters`, optional): Additional :mod:`telegram.ext.filters`
                for filtering messages. Defaults to ``None``.
        """
        owner_only = kwargs.get("owner_only", False)
        admins_only = kwargs.get("admins_only", False)
        fltrs = kwargs.get("filters", None)

        extra_filter = self._dynamic_filter(owner_only, admins_only, fltrs)

        @wraps
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_handler(MessageHandler(callback=func, filters=extra_filter))
            return func

        return decorator

    def on_inline(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for handling inline queries.
        """

        @wraps
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_handler(InlineQueryHandler(callback=func))
            return func

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
            pattern (:obj:`str` | :func:`re.Pattern <re.compile>` | :obj:`callable` | :obj:`type`,\
             optional):
                Pattern to test the callback query data against. For more information, please refer
                to :class:`telegram.ext.CallbackQueryHandler` documentation.
        """

        @wraps
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_handler(CallbackQueryHandler(callback=func, pattern=pattern))
            return func

        return decorator

    def run(self):
        """
        Starts the bot with polling.
        """
        self.run_polling()
