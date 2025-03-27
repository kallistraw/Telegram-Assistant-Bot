"""
Manage database within Telegram.

<b>Available commands:</b>
- /getdb key
  Get the value of <code>key</code> from the database.

- /setdb key value
  Store a key-value pair to the database.
  Use <code>-e</code> or <code>--extend</code> to extend/append the existing value

- /keys
  Get all available keys in the databse.

<b>Example:</b>
- /setdb PREFIXES ['?', '/', '!']
  Update allowed prefixes with <code>!</code>, <code>/</code>, and <code>?</code>
- /setdb -e PREFIXES $
  Add <code>$</code> to the allowed prefixes

  To add multiple item to the list:
- /setdb -e PREFIXES [':', '*']
"""

from html import escape

from telegram import Update
from telegram.ext import ContextTypes

from . import bot, db

PROCESS = "<i><code>Processing...</code></i>"


@bot.on_command("getdb", admins_only=True)
async def get_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retrieves value stored in the database using its key name."""
    message = await update.message.reply_text(PROCESS)
    help_text = (
        "<b>Usage:</b>\n"
        "- /getdb key"
        "  Get the value of <code>key</code>"
        "<b>Example:</b>\n"
        "- /getdb PREFIXES"
    )
    if len(context.args) < 1:
        await message.edit_text(help_text)
        return

    value = db.get(context.args[0], None)
    text = (
        f"<b>SQLite</b>\n"
        f"<b>Key:</b> <code>{escape(context.args[0])}</code>\n"
        f"<b>Value:</b> <code>{escape(value)}</code>"
    )

    await message.edit_text(text)


@bot.on_command("setdb", admins_only=True)
async def set_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stores a key-value pair to the database."""
    message = await update.message.reply_text(PROCESS)
    help_text = (
        "<b>Usage:</b>\n- /setdb [flags] key value\n\nRead more in /help database"
    )

    try:
        args = update.message.text.strip().split(maxsplit=2)
    except IndexError:
        await message.edit_text(help_text)
        return

    key = args[1]
    value = args[2]
    text = "<b>Key-value pair stored.</b>"

    if value in ("-e", "--extend"):
        try:
            value = value.split(maxsplit=1)[1]
        except IndexError:
            await message.edit_text(help_text)
            return

        existing_value = db.get(key, None)
        if not existing_value:
            await message.edit_text(f"No such Key: <code>{escape(key)}</code>")
            return

        if isinstance(existing_value, list):
            if isinstance(value, list):
                existing_value.extend(x for x in value if x not in existing_value)
            elif value not in existing_value:
                existing_value.append(value)

        elif isinstance(existing_value, tuple) and value not in existing_value:
            existing_value += (value,)

        else:
            existing_value = f"{existing_value} {value}"

        value = existing_value
        text.replace("stored", "updated")

    db.set(key, value)
    final_text = (
        f"{text}\n"
        f"• <b>Key:</b> <code>{escape(key)}</code>\n"
        f"• <b>Value:</b> <code>{escape(value)}</code>"
    )
    await message.edit_text(final_text)
    return


@bot.on_command("keys", admins_only=True)
async def get_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Returns all stored keys in the database."""
    message = await update.message.reply_text(PROCESS)
    _keys = sorted(db.keys())
    keys = "".join(
        f"\n• <code>{escape(k)}</code>"
        for k in _keys
        if not k.startswith("_")  # Default configuration
    )

    text = "<b>Available keys:</b>"
    await message.edit_text(f"{text}\n{keys}")
    return
