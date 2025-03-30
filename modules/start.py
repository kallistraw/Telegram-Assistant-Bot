"""
<b>Available commands:</b>
- /start
- /home
  The bot's main menu.
"""

import time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.helpers import mention_html

from . import AUTH_LIST, OWNER_ID, StartTime, bot, format_time

# NOTE: If you use a fork, you should change the URL into your forked repository URL.
SOURCE = "https://github.com/kallistraw/Telegram-Assistant-Bot"

start_keyboard = [
    [
        InlineKeyboardButton("Help", callback_data="help"),
        InlineKeyboardButton("Settings", callback_data="settings"),
    ],
    [
        InlineKeyboardButton("Statistics", callback_data="stats"),
    ],
]

start_markup = InlineKeyboardMarkup(start_keyboard)


@bot.on_command(["start", "home"])
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Welcome the user if they visited the bot for the first time or else greet them.
    """
    user = update.effective_user
    get_owner = await context.bot.get_chat(OWNER_ID)
    owner = mention_html(OWNER_ID, get_owner.full_name)
    mention_user = mention_html(user.id, user.full_name) if user else "there"

    users = context.bot_data.get("USER_IDS", [])
    if user and user.id not in users:
        users.append(user.id)

    me = context.bot.full_name

    if user and user.id in AUTH_LIST:
        await update.message.reply_text(
            f"Heya {mention_user}! What can I help you with?", reply_markup=start_markup
        )
    text = (
        f"Heya {mention_user}! My name is {me}, nice to meet you!\nYou can send {owner} a message"
        f" through me. Just send your message here and I will forward it to {owner}."
    )
    keyboard = InlineKeyboardButton("Source", url=SOURCE)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)


@bot.on_callback(pattern="help")
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles help-related callbacks"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Available helps:\n`None`")
    return


@bot.on_callback(pattern="stats")
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button clicks and show the bot's statistics."""
    query = update.callback_query
    users = context.bot_data.get("USER_IDS", [])
    time_ = time.time() - StartTime
    await query.answer(
        f"Bot Statistics\n• Uptime: {format_time(time_)}\n• Total users: {len(users)}",
        show_alert=True,
    )
