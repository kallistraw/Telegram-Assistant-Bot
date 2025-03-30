"""This module contain anti-spam function."""

import time

from telegram import Update
from telegram.ext import ContextTypes, filters
from telegram.helpers import mention_html

from . import AUTH_LIST, MAX_WARNING, OWNER_ID, bot, db

# Spam tracking dictionary
user_messages = {}
TIME_WINDOW = db.get("TIME_WINDOW", 5)  # Defaults to 5 seconds
MESSAGE_LIMIT = db.get("MESSAGE_LIMIT", 5)  # Max messages in the time window

_WARNING_MSG = (
    "You've been warned for spamming, please kindly <i>wait for reply</i>.\n"
    "Your current warning count is {}.\n"
    "You will get <i>blocked</i> from texting {} if your warning counts reached {}."
)


@bot.on_message(filters=filters.ChatType.PRIVATE & ~filters.User(AUTH_LIST))
async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Checks if user messages reach the `MESSAGE_LIMIT` in the amount of `TIME_WINDOW` seconds.
    """
    user = update.message.from_user
    current_time = time.time()

    # Track messages in a time window
    if user.id not in user_messages:
        user_messages[user.id] = []
    user_messages[user.id].append(current_time)

    # Remove old messages
    user_messages[user.id] = [
        t for t in user_messages[user.id] if current_time - t < TIME_WINDOW
    ]

    if len(user_messages[user.id]) > MESSAGE_LIMIT:
        get_owner = await context.bot.get_chat(OWNER_ID)

        warn_count = context.user_data.get("WARNING_COUNT", 0) + 1
        context.user_data["WARNING_COUNT"] = warn_count
        warn_per_max = f"{warn_count}/{MAX_WARNING}"

        if warn_count >= MAX_WARNING:
            await update.message.reply_text("You've been blocked for spamming!")
            context.bot_data[f"BLOCKED_{user.id}"] = True  # Blocks user
        else:
            await update.message.reply_text(
                _WARNING_MSG.format(
                    warn_per_max,
                    mention_html(OWNER_ID, get_owner.full_name),
                    MAX_WARNING,
                )
            )
