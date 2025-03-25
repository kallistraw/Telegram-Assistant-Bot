"""
Broadcast your message to all the bot's users.

<b>Available Commands:</b>
- /brodcast <code>your_message_here</code> or reply to a message
  /bc <code>your_message_here</code> or reply to a message
  Forwards your message to all users in the bot database.
"""

from asyncio import sleep
from html import escape
from io import BytesIO

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from . import bot


@bot.on_command(["broadcast", "bc"], admins_only=True)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forwards a message to all users in the bot's database."""
    message = await update.message.reply_text("<i><code>Processing...</code></i>")
    reply = update.message.reply_to_message

    if context.args:
        bc_msg = " ".join(a for a in context.args)
    elif reply:
        bc_msg = reply.text_markdown_v2_urled
    else:
        await message.edit_text(
            f"<b>Usage:</b>\n"
            f"- /broadcast {escape('<Your-messsage>')} or reply to a message"
        )
        return

    users = context.bot_data.get("USER_IDS", [])
    suc = 0
    fail = []

    await message.edit_text(f"`Broadcasting to {len(users)} users...")
    for user_id in users:
        try:
            await context.bot.send_message(
                user_id, bc_msg, parse_mode=ParseMode.MARKDOWN_V2
            )
            suc += 1
        except Exception as e:
            fail.append(
                f"Failed to send message to tg://user?id={user_id}: {escape(e)}"
            )
        await sleep(0.5)

    text = f"\n\nMessage has been sent to <i>{suc} users</i>\n"

    if len(fail) >= 1:
        fail_str = "\n".join(er for er in fail)
        if len(fail_str) > 4096:
            with BytesIO(fail_str.encode()) as f:
                f.name = "broadcast_error.txt"
                log_msg = await context.bot.send_document(
                    bot.log_channel, caption="Failed broadcast", document=f
                )
        else:
            log_msg = await context.bot.send_message(bot.log_channel, fail_str)

        text = text + (
            f"<b>Failed</b> to send message to {len(users) - {suc}} users.\n"
            f"Check the <a href='{escape(log_msg.link)}'>log message</a> for more info."
        )

    await message.edit_text(text)
    return
