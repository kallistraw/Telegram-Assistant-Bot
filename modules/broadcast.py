from . import bot
from . import BotDB
from . import log
from . import tgbot_cmd
from . import var


@tgbot_cmd(command="broadcast")
async def broadcast(event, args):
    reply = await event.get_reply_message()
    if not (reply and args):
        return await event.reply(
            f"Usage:\n`{i}broadcast Your message here` or reply to a message"
        )

    message = reply if reply else args
    users = BotDB.get_users()
    total = 0
    suc = 0

    for user_id in users:
        total += 1
        try:
            await bot.send_message(user_id, message)
            suc += 1
        except Exception as e:
            log.error(f"Failed to send message to {user_id}: {e}")

    return await event.reply(
        f"Total users: {total} users.\nMessage sent to {suc} users.\nFailed to send to {total - suc} users."
    )


@tgbot_cmd(command="bc")
async def bc(event, args):
    return await broadcast(event, args)
