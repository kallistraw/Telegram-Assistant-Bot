from telethon import events
from . import tgbot_cmd, BotDB, bot, var, log


@tgbot_cmd(command="start")
async def start(event):
    await event.reply("Hello! I'm your assistant bot.")
    sender = event.sender_id
    if sender != var.OWNER_ID and sender not in BotDB.get("DEVS"):
        BotDB.add_user(sender)
