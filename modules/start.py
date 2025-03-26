"""
<b>Available commands:</b>
- /start
- /home
  The bot's main menu.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from modules import bot

SOURCE = "https://github.com/kallistraw/Telegram-Assistant-Bot"

buttons = [
    [
        InlineKeyboardButton("Help", callback_data="help"),
        InlineKeyboardButton("Source", url=SOURCE),
    ],
]

start_markup = InlineKeyboardMarkup(buttons)


@bot.on_command(["start", "home"])
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Welcome the user if they visited the bot for the first time or else greet them.
    """
    first_time = False
    user = update.effective_user

    if user.id not in context.bot_data.get("USER_IDS", []):
        context.bot_data.setdefault("USER_IDS", []).append(user.id)
        first_time = True

    me = context.bot.first_name

    if first_time:
        text = f"Hello {user.first_name}!\n\nMy name is {me}, nice to meet you!"
    else:
        text = f"Welcome back, {user.first_name}!"
    await update.message.reply_text(
        text, reply_markup=start_markup, reply_to_message_id=update.message.id
    )


@bot.on_callback()
async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles help button callbacks"""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Available helps:\n`None`")
    return
