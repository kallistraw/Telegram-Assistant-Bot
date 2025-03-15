"""This module contains some helper functions."""

import importlib
import os
import traceback

from . import LOGS
from .. import _tgbot_cache


def load_modules(directory: str):
    """
    Dynamically imports all Python files inside the given directory.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    module_dir = os.path.join(base_dir, directory)
    if not os.path.exists(module_dir):
        raise FileNotFoundError(
            f"Expected '{base_dir}/{directory}', but got '{module_dir}' instead."
        )

    for file in os.listdir(module_dir):
        if file.endswith(".py") and not file.startswith("__"):
            module_name = f"{module_dir}.{file[:-3]}"
            try:
                importlib.import_module(module_name)

            except Exception as e:
                # debugging-purpose
                # pylint: disable=import-outside-toplevel
                import sys

                tb = traceback.format_exc()
                LOGS.error("Failed to load %s: %s\n%s", module_name, e, tb)
                sys.exit()


def is_dangerous(cmd: str) -> bool:
    """
    Used to determine wheter something is considered dangerous or not.

    This function is deisgned for internal use only, however, you can still use it.

    Args:
        cmd (:obj:`str`): The string to be analyzed.

    Returns:
        :obj:`bool`: `True` if it's dangerous.
    """
    # TODO
    return True
