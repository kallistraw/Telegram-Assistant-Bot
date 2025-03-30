"""This module contains message forwarding handlers"""

from asyncio import sleep
from html import escape
from random import choice

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ForumIconColor
from telegram.error import RetryAfter, TelegramError
from telegram.ext import ContextTypes, filters
from telegram.helpers import mention_html

from . import (
    AUTH_LIST,
    FORUM_TOPIC,
    LOG_GROUP_ID,
    MAX_WARNING,
    OWNER_ID,
    PM_GROUP_ID,
    bot,
)

COLORS = [
    ForumIconColor.RED,
    ForumIconColor.BLUE,
    ForumIconColor.GREEN,
    ForumIconColor.PURPLE,
    ForumIconColor.YELLOW,
    ForumIconColor.PINK,
]


_FORWARDED_MSG = (
    "Your message has been forwarded, please kindly <i>wait for reply</i>.\n"
    "If you spamming, you will get a warning. Your current warning count is {}.\n"
    "You will get <i>blocked</i> from texting {} when your warning counts reached {}."
)


@bot.on_callback(pattern=r"^changeemoji_")
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle emoji selection and update the forum topic emoji."""
    query = update.callback_query
    await query.answer()

    _, topic_id, file_id = query.data.split("_")
    topic_id = int(topic_id)

    chat_id = PM_GROUP_ID

    await context.bot.edit_forum_topic(
        chat_id=chat_id, message_thread_id=topic_id, icon_custom_emoji_id=file_id
    )
    return


async def user_handler_topic(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles incoming private messages and sends them to the user's forum topic."""
    user = update.message.from_user
    user_topic = context.user_data.get("topic_id", None)
    bot_ = context.bot

    # Create a forum topic for new users
    if not user_topic:
        try:
            topic = await bot_.create_forum_topic(
                PM_GROUP_ID, user.full_name, icon_color=choice(COLORS)
            )
            topic_id = topic.message_thread_id
            context.user_data["topic_id"] = topic_id
            stickers = await bot_.get_forum_topic_icon_stickers()
            keyboard = []
            for sticker in stickers:
                emoji = sticker.emoji
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            emoji,
                            callback_data=f"changeemoji_{topic_id}_{sticker.file_id}",
                        )
                    ]
                )

            reply_markup = InlineKeyboardMarkup(keyboard)

            text = (
                "Choose an emoji for the forum topic below (optional).\n"
                "You can set a default emoji in the <code>{i}settings</code> section."
            )

            await bot_.send_message(
                PM_GROUP_ID,
                text,
                message_thread_id=topic_id,
                reply_markup=reply_markup,
            )

        except TelegramError as e:
            await bot_.send_message(
                LOG_GROUP_ID,
                f"An error occurred while creating a forum topic for new user: {e}",
            )

    await forward_to_owner(update, context, user_topic)
    return


async def owner_handler_topic(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Forwards the bot's owner/admins replies from the topic back to the user."""
    await forward_to_user(update, context)


async def user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles incoming private messages and forwards them to either the chat id in
    :const:`tgbot.modules.PM_GROUP_ID` or the owner's private message.
    """
    await forward_to_owner(update, context)


async def owner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Forwards the bot's owner/admins replies either from the chat id in
    :const:`tgbot.modules.PM_GROUP_ID` or the bot's owner private message back to the user
    """
    await forward_to_user(update, context)


if FORUM_TOPIC:
    fltrs = filters.User(AUTH_LIST) & filters.Chat(PM_GROUP_ID)
    bot.on_message(filters=fltrs)(owner_handler_topic)
    bot.on_message(filters=filters.ChatType.PRIVATE)(user_handler_topic)
else:
    if PM_GROUP_ID:
        fltrs = filters.User(AUTH_LIST) & filters.Chat(PM_GROUP_ID)
    else:
        fltrs = filters.User(OWNER_ID)
    bot.on_message(filters=fltrs)(owner_handler)
    bot.on_message(filters=filters.ChatType.PRIVATE)(user_handler)


async def forward_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """A helper function to forward the bot's owner/admins message back to the user"""
    reply = update.message.reply_to_message
    if (
        FORUM_TOPIC
        and update.message.is_topic_message
        and reply
        and not reply.from_user.is_bot
        and reply.from_user.id not in AUTH_LIST
    ):
        try:
            await update.message.forward(reply.from_user.id)
        except RetryAfter as e:
            await sleep(e.retry_after)
            await update.message.forward(reply.from_user.id)
        except TelegramError as e:
            await update.message.reply_text(
                f"An error occurred while forwarding your message: {e}"
            )
        return

    if reply and not reply.from_user.is_bot and reply.from_user.id not in AUTH_LIST:
        try:
            await update.message.forward(reply.from_user.id)
        except RetryAfter as e:
            await sleep(e.retry_after)
            await update.message.forward(reply.from_user.id)
        except TelegramError as e:
            await update.message.reply_text(
                f"An error occurred while forwarding your message: {e}"
            )
        return

    return


async def forward_to_owner(
    update: Update, context: ContextTypes.DEFAULT_TYPE, topic_id: int | None = None
) -> None:
    """A helper function to forward user messages to the bot's owner/admins"""

    owner = context.bot.get_chat(OWNER_ID)
    _owner = mention_html(OWNER_ID, owner.first_name)

    user = update.message.from_user
    warning_count = context.user_data.get("warning_count")
    warn_per_max = f"{warning_count}/{MAX_WARNING}"
    mention_user = mention_html(user.id, user.full_name)

    is_blocked = context.bot_data.get(f"BLOCKED_{user.id}")
    if is_blocked:
        await update.message.reply_text(
            f"Opsie, looks like you was blocked from texting {_owner}.\n"
            f"Reason:\n{escape(is_blocked)}"
        )
        return

    if PM_GROUP_ID:
        try:
            await update.message.forward(PM_GROUP_ID, message_thread_id=topic_id)
            if context.user_data.get("is_first_time", True):
                await update.message.reply_text(
                    _FORWARDED_MSG.format(warn_per_max, MAX_WARNING, _owner)
                )

                context.user_data["is_first_time"] = False
        except RetryAfter as e:
            await sleep(e.retry_after)
            await update.message.forward(PM_GROUP_ID, message_thread_id=topic_id)
        except TelegramError as e:
            await context.bot.send_message(
                LOG_GROUP_ID,
                f"An error occurred while forwarding message from {mention_user}: {e}\n"
                f"Message: {update.message.text}",
            )
        return

    try:
        await update.message.forward(OWNER_ID)
        if context.user_data.get("is_first_time", True):
            await update.message.reply_text(
                _FORWARDED_MSG.format(warn_per_max, MAX_WARNING, _owner)
            )

            context.user_data["is_first_time"] = False
    except RetryAfter as e:
        await sleep(e.retry_after)
        await update.message.forward(OWNER_ID)
    except TelegramError as e:
        await context.bot.send_message(
            LOG_GROUP_ID,
            f"An error occurred while forwarding message from {mention_user}: {e}\n"
            f"Message: {update.message.text}",
        )

    return
