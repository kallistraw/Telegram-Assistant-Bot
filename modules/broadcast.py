from telethon import events
from . import (
    bot,
    var,
    BotDB,
    log,
    )

@bot.on(events.NewMessage(pattern="/broadcast"))
async def broadcast(event):
    if event.sender_id not in BotDB.get("ADMINS"):
        return await event.reply("⚠️ You don't have permission to use this command.")

    reply = await event.get_reply_message()
    args = event.text.split(maxsplit=1)
    if not reply and len(args) < 2:
        return await event.reply("Usage: `/broadcast Your message here` or reply to a message")

    message = reply if reply else args[1]
    users = BotDB.get_users()

    for user_id in users:
        try:
            await bot.send_message(user_id, message)
        except Exception as e:
            log.error(f"Failed to send message to {user_id}: {e}")

    await event.reply(f"Broadcast send to {len(users)} users!")
