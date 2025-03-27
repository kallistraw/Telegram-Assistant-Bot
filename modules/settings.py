"""
Manage the bot's configuratuon.

<b>Available Commands:</b>
- /settings
  The settings home page.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import mention_html

from . import (
    AUTH_LIST,
    BotConfig,
    bot,
    cancel_fallback,
    db,
    process_thumbnail,
    safe_convert,
)


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


@bot.on_callback(pattern=r"^pm_*")
async def pm_menu(update: Update, context: ContextTypes) -> None:
    """Handles PM settings button clicks"""
    query = update.callback_query
    await query.answer()

    home_keyboard = [
        [InlineKeyboardButton("Back", callback_data="pm_home")],
    ]

    menu = query.data.split("_", maxsplit=1)[1]
    if menu == "home":
        keyboard = [
            [
                InlineKeyboardButton("PM Log Group", callback_data="set_pm_group"),
                InlineKeyboardButton("Forum Topic", callback_data="pm_topic"),
            ],
            [
                InlineKeyboardButton("Max Warnings", callback_data="set_max_warning"),
                InlineKeyboardButton("Custom Message", callback_data="pm_message"),
            ],
            [
                InlineKeyboardButton("Force Subscribe", callback_data="set_force_sub"),
            ],
            [
                InlineKeyboardButton("Back", callback_data="settings"),
            ],
        ]
        markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("PM Bot Configrations:", reply_markup=markup)

    elif menu == "topic":
        keyboard = [
            [
                InlineKeyboardButton(
                    "Enable/Disable Topic", callback_data="topic_togle"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Set default emoji", callback_data="set_topic_emoji"
                ),
            ],
        ]
        keyboard.extend(i for i in home_keyboard)

    elif menu == "message":
        pass
    return


# ---- Conversation Stuff ----
SET_MAX_WARNING, SET_PM_GROUP, SET_FORCE_SUB, SET_THUMBNAIL, SET_PREFIX = range(5)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles button clicks that will starts a conversation."""
    query = update.callback_query
    await query.answer()

    option = query.data.split("_", maxsplit=1)[1]
    if option == "thumbnail":
        await query.message.reply_text(
            "Send me an image to set as a custom thumbnail when sending a document.\n"
            "Send /cancel to cancel the operation."
        )
        return SET_THUMBNAIL

    if option == "prefix":
        await query.message.reply_text(
            "Send me a character(s) to set as a prefix.\n"
            "Seperate by space if you sending multiple prefixes.\n"
            "Example: <code>/ $ & , ?</code>\n"
            "Send /cancel to cancel the operation."
        )
        return SET_PREFIX

    if option == "pm_group":
        await update.messate.reply_text(
            "Send the new PM log group username (with @) or ID to forwards user messages to.\n",
        )
        return SET_PM_GROUP

    if option == "max_warning":
        await query.message.reply_text(
            "Send me the number of warnings a user can receive before being banned. (Default: 3)\n"
            "Send /cancel to cancel the operation."
        )
        return SET_MAX_WARNING

    if option == "force_sub":
        await query.message.reply_text(
            "Send me the channel username (with @) or ID a user should subscribe to before they "
            "can use the bot."
        )
        return SET_FORCE_SUB


async def set_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles user input for a new prefixes."""

    msg = update.message
    pref = msg.text.split(" ") if " " in msg.text else msg.text
    prefix = safe_convert(str(pref))

    db.set("PREFIXES", prefix)
    await msg.reply_text(
        f"Prefix updated to: <code>{pref}</code>\n"
        "Restart the bot by using /restart to apply the changes."
    )
    return ConversationHandler.END


async def set_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the received images (photo or document) for configuring a custom thumbnail."""
    msg = update.message

    if msg.photo:
        thumb = await msg.photo[-1].get_file()
    elif msg.document and msg.document.mime_type.startswith("image/"):
        thumb = await msg.document.get_file()
    else:
        await msg.reply_text(
            f"Invalid file type: '{msg.document.mime_type}'\n"
            "Please send an image or type /cancel to exit."
        )
        return SET_THUMBNAIL

    try:
        file = thumb.download_to_drive(BotConfig.THUMBNAIL)
        process_thumbnail(file)
        db.set("CUSTOM_THUMBNAIL", True)
        await msg.reply_text("Custom thumbnail updated.")
    except Exception as e:
        await msg.reply_text(
            f"Failed to process the image: <code>{e}</code>\nPlease try again later."
        )

    return ConversationHandler.END


async def invalid_input(update: Update, context):
    """Handle messages that are not images or /cancel."""
    await update.message.reply_text(
        "That's not an image! Please send an image or type /cancel to exit."
    )
    return SET_THUMBNAIL


async def set_force_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle messages that contain a Telegram channel identifier for configuring 'Force Subscribe'
    """
    msg = update.message.text.strip()

    channel_id = msg if "@" in msg else None
    if not channel_id:
        try:
            channel_id = int(msg)
        except ValueError:
            await update.message.reply_text(
                "Invalid input.\n"
                "Please send the channel username (starting with @) or the channel ID (-100...)."
            )
            return SET_FORCE_SUB

    # Attempt to fetch channel info
    try:
        channel = await context.bot.get_chat(channel_id)
    except TelegramError as err:
        error_message = str(err).lower()

        if "chat not found" in error_message:
            await update.message.reply_text(
                "The channel does not exist.\nEnsure the username/ID is correct."
            )
        elif (
            "bot was kicked" in error_message or "bot is not a member" in error_message
        ):
            await update.message.reply_text(
                "The bot is not in the channel or lacks admin permissions.\n"
                "Please add the bot as an admin before proceeding."
            )
        else:
            await update.message.reply_text(
                f"Failed to get channel info: <code>{err}</code>\n"
                "Please ensure the bot has access to the channel."
            )

        return SET_FORCE_SUB

    db.set("FORCE_SUB", channel.id)
    await update.message.reply_text(
        f"Force subscribe channel set to: {channel.title} (@{channel.username})"
        "Restart the bot by using /restart to apply the changes."
    )

    return ConversationHandler.END


async def set_max_warning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle messages for MAX_WARNING configuration."""
    msg = update.message.text.strip()
    try:
        max_warn = int(msg)
    except ValueError:
        await update.message.reply_text(
            "Invalid input.\nPlease send the maximum warning in a form of number (e.g., 4 or 5)"
        )
        return SET_MAX_WARNING

    db.set("MAX_WARNING", max_warn)
    await update.message.reply_text(f"MAX_WARNING set to {max_warn}.")
    return ConversationHandler.END


async def set_pm_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle messages that contain a Telegram group identifier for configuring message forwarding.
    """
    msg = update.message.text.strip()

    group_id = msg if "@" in msg else None
    if not group_id:
        try:
            group_id = int(msg)
        except ValueError:
            await update.message.reply_text(
                "Invalid input.\n"
                "Please send the group username (starting with @) or the group ID (-100...)."
            )
            return SET_PM_GROUP

    # Attempt to fetch group info
    try:
        group = await context.bot.get_chat(group_id)
    except TelegramError as err:
        error_message = str(err).lower()

        if "chat not found" in error_message:
            await update.message.reply_text(
                "The group does not exist.\nEnsure the username/ID is correct."
            )
        elif (
            "bot was kicked" in error_message or "bot is not a member" in error_message
        ):
            await update.message.reply_text(
                "The bot is not in the group or lacks admin permissions.\n"
                "Please add the bot as an admin before proceeding."
            )
        else:
            await update.message.reply_text(
                f"Failed to get group info: <code>{err}</code>\n"
                "Please ensure the bot has access to the group."
            )

        return SET_PM_GROUP

    db.set("PM_LOG_GROUP", group.id)
    await update.message.reply_text(
        f"PM log group set to: {group.title}\n"
        "Restart the bot by using /restart to apply the changes."
    )

    return ConversationHandler.END


reg_filters = (
    filters.User(AUTH_LIST) & filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND
)

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_click, pattern="^set_*")],
    states={
        SET_FORCE_SUB: [MessageHandler(reg_filters, set_force_sub)],
        SET_MAX_WARNING: [MessageHandler(reg_filters, set_max_warning)],
        SET_PM_GROUP: [MessageHandler(reg_filters, set_pm_group)],
        SET_PREFIX: [MessageHandler(reg_filters, set_prefix)],
        SET_THUMBNAIL: [
            MessageHandler(
                (
                    filters.User(AUTH_LIST) & filters.PHOTO
                    | filters.Document.IMAGE & filters.ChatType.PRIVATE
                ),
                set_thumbnail,
            ),
            MessageHandler(~filters.COMMAND, invalid_input),
        ],
    },
    fallbacks=[cancel_fallback],
)

bot.add_handler(conv_handler, group=2)
