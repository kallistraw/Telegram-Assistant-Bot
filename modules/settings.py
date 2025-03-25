"""
Manage the bot's configuratuon.

<b>Available Commands:</b>
- /settings
  The settings home page.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, filters
from telegram.helpers import mention_html

from . import BotConfig, bot, db, process_thumbnail


@bot.on_command("settings", admins_only=True, chat_type="private")
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the configuration options with an inline buttons."""
    user = update.message.from_user

    keyboard = [
        [
            InlineKeyboardButton("• Thumbnail", callback_data="set_thumbnail"),
            InlineKeyboardButton("Prefix •", callback_data="set_prefix"),
        ],
        [
            InlineKeyboardButton("• PM Settings", callback_data="pm_home"),
            InlineKeyboardButton("Bot Settings •", callback_data="bot_home"),
        ],
        [
            InlineKeyboardButton("• Back To Home •", callback_data="start"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Heya {mention_html(user.id, user.full_name)}!\n"
        "Choose the buttons below to edit the settings",
        reply_markup=reply_markup,
    )


@bot.on_callback(pattern=r"^set_*")
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button clicks."""
    query = update.callback_query
    await query.answer()

    act = query.data.split("_")[1]
    if act == "thumbnail":
        context.user_data["waiting_thumbnail"] = True
        await query.edit_message_text(
            "Send a photo or image link to set as a thumbnail.\n"
            "Use /cancel to cancel the operation"
        )
        return

    if act == "prefix":
        context.user_data["waiting_input"] = True
        await query.edit_message_text(
            "Send a character(s) to use as a prefix\n"
            "Seperate each character with space if sending multiple characters.\n"
            "Example: <code>! ? , /</code>\n"
            "Use /cancel to cancel the operation"
        )
        return


@bot.on_message(filters=filters.ChatType.PRIVATE)
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles file uploads only when expected."""
    thumb = None
    if context.user_data.get("waiting_thumbnail"):
        attachment = update.message.effective_attachment
        if attachment:
            if isinstance(attachment, tuple):
                thumb = attachment[-1].get_file()

            else:
                mime_type = attachment.mime_type
                extension = (
                    attachment.file_name.split(".")[-1]
                    if "." in attachment.file_name
                    else "None"
                )

                if not mime_type.startswith("image") or extension not in (
                    "png",
                    "jpeg",
                    "jpg",
                ):
                    await update.message.reply_text(
                        f"Invalid file type: '{mime_type}'\n"
                        "Please send an image in PNG, JPG, or JPEG format."
                    )

                else:
                    thumb = await attachment.get_file()
        else:
            await update.message.reply_text(
                "That's not a file! Please send a valid file/image."
            )
            return

    if thumb:
        try:
            thumb.download_to_drive(BotConfig.THUMBNAIL)
            process_thumbnail(thumb)
            db.set("CUSTOM_THUMBNAIL", True)
            await update.message.repliy_text("Settings updated.")
            context.user_data.pop("waiting_thumbnail", None)
        except BaseException as e:
            await update.message.reply_text(f"Failed to process the image: {e}")

    return
