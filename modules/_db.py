from telethon import events
from . import bot, BotDB, var, log, tgbot_cmd, i


@tgbot_cmd(command="get")
async def _database(event, args):
    if args:
        if args[0] == "db":
            _db = BotDB.get(args[1])
            return await event.reply(f"{_db}")

        elif args[0] == "keys":
            _keys = BotDB.keys()
            return await event.reply(f"{_keys}")

    return await event.reply(
        f"**Usage**:\n`{i}get keys` - Return all available keys in database\n`{i}get db <key>` - Get the value of <key>"
    )


@tgbot_cmd(command="setdb")
async def setkeydb(event, args):
    if args:
        key, value = args[0], args[1]
        _set = BotDB.set(key, value)
        return await event.reply(f"**BotDB Updated!**\nKey: `{key}`\nValue: {value}")

    return await event.reply(
        f"**Usage:**\n- `{i}setdb <key> <value>`\n  Store key in database with the corresponding value.\n\n**Example:**\n- `{i}setdb DEVS 12345678`\n  Add a user with id `12345678` to the bot devs list."
    )
