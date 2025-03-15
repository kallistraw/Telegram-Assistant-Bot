from . import *


@bot.on_cmd("get")
async def _database(update, context):
    help_text = (
        f"**Usage**:\n"
        f"• `{i}get keys` - Return all available keys in database\n"
        f"• `{i}get db <key>` - Get the value of <key>"
    )


@bot.on_cmd("setdb")
async def setkeydb(update, context):
    help_text = (
        "**Usage:**\n"
        f"• `{i}setdb <key> <value>`\n"
        "  Store key in database with the corresponding value.\n\n"
        "**Example:**\n"
        f"- `{i}setdb PREFIXES ! / ?`\n"
        "  Update allowed prefixes with `!`, `/`, and `?`.\n\n"
        "More on `What else can you configure with this` later..."  # TODO
    )
