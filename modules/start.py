from telethon import events
from . import (
    bot,
    var,
    BotDB,
    log,
    i
    )

@bot.on(events.NewMessage(pattern=f"{i}start"))
async def start(event):
    await event.reply("Hello! I'm your assistant bot.")
    sender = event.sender_id
    if sender != var.OWNER_ID and sender not in var.ADMINS:
        BotDB.add_user(sender)
