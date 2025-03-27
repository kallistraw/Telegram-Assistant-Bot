"""
Manage the bot's configuratuon.

<b>Available Commands:</b>
- /settings
  The settings home page.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, filters
from telegram.helpers import mention_html

from . import AUTH_LIST, BotConfig, bot, db, process_thumbnail, safe_convert


@bot.on_command("settings", admins_only=True, chat_type="private")
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the configuration options with an inline buttons."""
    user = update.message.from_user

    keyboard = [
        [
            InlineKeyboardButton("Thumbnail", callback_data="set_thumbnail"),
            InlineKeyboardButton("Prefix", callback_data="set_prefix"),
        ],
        [
            InlineKeyboardButton("PM Bot Settings", callback_data="pm_home"),
        ],
        [
            InlineKeyboardButton("Bot's Statistics", callback_data="bot_stats"),
        ],
        [
            InlineKeyboardButton("Back To Home", callback_data="start"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Heya {mention_html(user.id, user.full_name)}!\n"
        "From here, you can change the settings as you like.\n"
        "Click on the buttons to see more information.",
        reply_markup=reply_markup,
    )
    return


@bot.on_callback(pattern=r"^set_*")
async def settings_(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles thumbnail or prefix button clicks."""
    query = update.callback_query
    await query.answer()

    act = query.data.split("_")[1]
    if act == "thumbnail":
        async with 
        await query.edit_message_text("Send a photo to set as a custom thumbnail.\n")

    elif act == "prefix":
        context.user_data["waiting_prefix"] = True
        await query.edit_message_text(
            "Send a character(s) to use as a prefix\n"
            "Seperate each character with space if sending multiple characters.\n"
            "Example: <code>! ? , /</code>\n"
        )

    return


@bot.on_callback(pattern=r"^pm_*")
async def pm_menu(update: Update, context: ContextTypes) -> None:
    """Handles PM settings button clicks"""
    query = update.callback_query
    await query.answer()

    home_keyboard = [
        InlineKeyboardButton("Back", callback_data="pm_home"),
    ]
    home_markup = InlineKeyboardMarkup(home_keyboard)

    menu = query.split("_", maxsplit=1)[1]
    if menu == "home":
        # Resetting the states
        context.user_data.pop("waiting_new_group", None)
        context.user_data.pop("waiting_max_warning", None)
        context.user_data.pop("waiting_force_sub", None)

        keyboard = [
            [
                InlineKeyboardButton("PM Log Group", callback_data="pm_log_group"),
                InlineKeyboardButton("Forum Topic", callback_data="pm_topic"),
            ],
            [
                InlineKeyboardButton("Max Warnings", callback_data="pm_warning"),
                InlineKeyboardButton("Custom Message", callback_data="pm_message"),
            ],
            [
                InlineKeyboardButton("Force Subscribe", callback_data="pm_force_sub"),
            ],
            [
                InlineKeyboardButton("Back", callback_data="settings"),
            ],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("PM Bot Configrations:", reply_markup=markup)

    elif menu == "log_group":
        context.user_data["waiting_new_group"] = True
        await query.edit_message_text(
            "Send the new PM Log group either by <code>@groupusername</code> or the group's ID.\n",
            reply_markup=home_markup,
        )

    elif menu == "topic":
        keyboard = [
            [
                InlineKeyboardButton(
                    "Enable/Disable Topic", callback_data="topic_togle"
                ),
            ],
            [
                InlineKeyboardButton("Set default emoji", callback_data="topic_emoji"),
            ],
        ]
        keyboard.extend(i for i in home_keyboard)
    elif menu == "force_sub":
        pass
    return


@bot.on_message(
    filters=filters.User(AUTH_LIST)
    & filters.ChatType.PRIVATE
    & filters.Document.ALL
    & ~filters.COMMAND
)
async def _get_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles file uploads for a custom thumbnail."""
    if not context.user_data.get("waiting_thumbnail"):
        return

    thumb = None
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

    if thumb:
        try:
            thumb.download_to_drive(BotConfig.THUMBNAIL)
            process_thumbnail(thumb)
            db.set("CUSTOM_THUMBNAIL", True)
            context.user_data.pop("waiting_thumbnail", None)
            await update.message.repliy_text("Settings updated.")
        except BaseException as e:
            await update.message.reply_text(f"Failed to process the image: {e}")

    return


@bot.on_message(
    filters=filters.User(AUTH_LIST)
    & filters.ChatType.PRIVATE
    & filters.TEXT
    & ~filters.COMMAND
)
async def _get_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles user input for a new prefixes."""
    if not context.user_data.get("waiting_prefix"):
        return

    msg = update.message
    pref = msg.text.split(" ") if " " in msg.text else msg.text
    prefix = safe_convert(pref)

    db.set("PREFIXES", prefix)
    context.user_data.pop("waiting_prefix", None)
    _type = "Multi Prefixes" if isinstance(prefix, list) else "Single Prefix"
    await msg.reply_text(f"Prefix updated to: <code>{pref}</code>\nType: {_type}")
