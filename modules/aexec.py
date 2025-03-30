"""
Execute Python code asynchronously.

<b>Available commands:</b>
- /exec <code>python_code</code>
- /py <code>python_code</code>
  Execute <code>python_code</code>

<b>NOTE:</b>
This command could be <i>very dangerous</i> if you don't know what you're doing.
Please do NOT use this command if you are unfamiliar with python code.
"""

import json
import sys
import time
import traceback
from html import escape
from io import BytesIO, StringIO
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import mention_html

# Import all functions, classes, etc.
# So that we don't need to import it when using the exec command.
from . import (  # noqa: F401
    AUTH_LIST,
    FORUM_TOPIC,
    LOG_GROUP_ID,
    LOGS,
    MAX_WARNING,
    OWNER_ID,
    PM_GROUP_ID,
    BotConfig,
    Var,
    _bot_cache,
    _module_cache,
    bot,
    bot_cache,
    censors,
    db,
    format_time,
    get_files,
    is_dangerous,
    load_modules,
    module_cache,
    process_thumbnail,
    safe_convert,
)

try:
    import black
except ImportError:
    black = None


def _parser(text=None, **kwargs) -> Any:
    """Parse Python data types into a more readable format"""
    if text:
        if isinstance(text, dict):
            try:
                text = json.dumps(text, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass

        if isinstance(text, list):
            text = "[\n  " + ",\n  ".join(map(str, text)) + "\n]"

        if black:
            try:
                text = black.format_str(str(text), mode=black.Mode())
            except Exception:
                pass

    return print(text, **kwargs)


async def async_exec(
    code: str, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Any:
    """Executes the given Python code asynchronously."""
    # pylint: disable=W0122
    exec(
        (
            "async def _async_exec(update, context): "
            + "\n message = update.message"
            + "\n chat = update.effective_chat"
            + "\n reply = await message.reply_to_message if message.reply_to_message else None"
            + "\n app = bot"
            + "\n p = print = _parser"
            + "\n locals_ = locals()"
        )
        + "".join(f"\n {line}" for line in code.split("\n"))
    )

    return await locals()["_async_exec"](update, context)


HEADER = (
    "<b>• Python Eval</b> <i>(in {})</i>\n"
    "<pre><code class='language-python'>\n"
    "{}</code></pre>\n\n"
    "<b>• Output:</b>"
)


@bot.on_command(["exec", "py"], admins_only=True)
async def aexec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Executes Python code and returns the output."""
    # pylint: disable=R0914

    # We need the raw message here to capture the `\n` which is not included in `context.args`
    try:
        cmd = update.message.text.split(maxsplit=1)[1]
    except IndexError:
        await update.message.reply_text(
            escape("Usage: /exec <python-code>\nRead more info in /help exec")
        )
        return

    reply_msg = await update.message.reply_text("<i><code>Processing...</code></i>")

    if black:
        try:
            cmd = black.format_str(cmd, mode=black.Mode())
        except Exception:
            pass

    user = update.message.from_user

    # Handling dangerous code
    if is_dangerous(cmd) and user.id != OWNER_ID:
        await context.bot.send_message(
            LOG_GROUP_ID,
            "<b>Malicious activity detected!</b>\n\n"
            f"<b>User:</b> {mention_html(user.id, user.full_name)}"
            f"<b>Code:</b>\n <pre><code>{escape(cmd)}</code></pre>",
        )
        await reply_msg.edit_text("<b>Malicious code, operation aborted.</b>")
        return

    # Capture stdout & stderr
    old_stdout, old_stderr = sys.stdout, sys.stderr
    redirected_output, redirected_error = StringIO(), StringIO()
    sys.stdout, sys.stderr = redirected_output, redirected_error

    start_time = time.time()
    result, error = None, None

    try:
        result = await async_exec(cmd, update, context)
    except Exception:
        error = traceback.format_exc()

    elapsed_time = time.time() - start_time
    sys.stdout, sys.stderr = old_stdout, old_stderr

    # Retrieve outputs
    output = (
        error
        or redirected_error.getvalue()
        or redirected_output.getvalue()
        or str(result)
        or "Success"
    )

    final_message = (
        HEADER.format(format_time(elapsed_time), escape(cmd))
        + f"\n<pre>{censors(escape(output))}</pre>"
    )

    if len(final_message) > 4096:
        await reply_msg.delete()
        with BytesIO(output.encode()) as file:
            file.name = "output.txt"
            await update.message.reply_document(
                document=file,
                caption=HEADER.format(format_time(elapsed_time), escape(cmd)),
            )
        return

    await reply_msg.edit_text(final_message)
