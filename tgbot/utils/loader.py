"""This module contain a loader function which load the bot's modules."""

import importlib
import os
import traceback

from tgbot.utils import LOGS, _bot_cache
from tgbot.utils.helpers import TempCache, get_files

_cache = TempCache(_bot_cache)


def load_modules(directory: str) -> None:
    """
    Dynamically imports all Python files in the given directory,
    excluding files that start with '__'.

    Arguments:
        directory (str): The directory path to import modules from.
    """
    if not os.path.exists(directory):
        raise FileNotFoundError(
            "Directory '%s' does not exists! Make sure that you are in the correct path."
        )

    modules = get_files(directory, ".py")
    LOGS.info("• Loading %s modules from '%s'...", len(modules), directory)

    for filename in sorted(modules):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            module_path = os.path.join(directory, filename)

            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    module.__package__ = os.path.basename(directory)
                    spec.loader.exec_module(module)
                    _cache.dict.set("loaded_modules", directory, module_name)
            except ModuleNotFoundError as e:
                LOGS.error("Missing dependency in '%s': %s", module_name, e.name)
            except Exception as e:
                LOGS.error("Failed to import '%s': %s", module_name, e)
                LOGS.error("\n%s", traceback.format_exc())
