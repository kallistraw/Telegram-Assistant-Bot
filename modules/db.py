from telethon import events
from . import bot, BotDB, var, log, i



# TODO: database module
@bot.on(events.NewMessage(pattern=f"{i}get"))
async def _database(event):
    sender = event.sender_id
    if sender != var.OWNER_ID:
        return await event.reply("You are not allowed to use this command!")
    try:
        args = event.text.split(" ", maxsplit=2)
        flag = args[1]
    except IndexError:
        flag = False
    if flag:
        if flag == "db":
            _db = BotDB.get(args[2])
            return await event.reply(f"{_db}")
        elif flag == "keys":
            keys = BotDB.keys()
            return await event.reply(f"{keys}")
        
    return await event.reply(f"Usage:\n`{args[0]} keys` - Return all available keys in database\n`{args[0]} db <key>` - Get the value from the <key>")

@bot.on(events.NewMessage(pattern=rf"{i}setdb ?(.*)"))
async def setkeydb(event):
    args = event.pattern_match.group(2).strip()
    arg = args.split()
    p = event.text.split(" ", maxsplit=1)[0]
    key = arg[0]
    value = arg[1]
    if args:
        _set = BotDB.set(key, value)
        if _set is True:
            return await event.reply(f"**BotDB Updated!**\nKey: `{key}`\nValue: {value}")
        elif _set[False]:
            return await event.reply(f"Opss... something went wrong.\n{_set['err']}")
    return await event.reply(f"**Usage:**\n- `{p} <key> <value>`\n  Store key in database with the corresponding value.\n\n**Example:**\n- `{p} ADMINS 12345678`\n  Add a user with id `12345678` to the bot admin list.")
