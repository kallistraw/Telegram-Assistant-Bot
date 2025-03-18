# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
# pylint: disable=missing-function-docstring
"""This module contains some helper functions."""

import importlib
import os
import traceback
from types import MappingProxyType

from . import LOGS

__all__ = (
    "load_modules",
    "is_dangerous",
    "TempCache",
    "censors",
)

_bot_cache: dict[str | int, any] = {}


# Why not...
class TempCache:
    """Caching logic that can handle different data types."""

    def __init__(self, cache_dict: dict[str | int, any] = None) -> None:
        """
        Initialize with an external dictionary (or create a new one if None).

        Arguments:
            cache_dict (:obj:`dict`):
                A dictionary to use as a temporary cache storage.
        """
        self.cache = cache_dict if cache_dict is not None else {}

    def set(self, key: str | int, value: any) -> bool:
        """Set a value in the cache."""
        self.cache[key] = value
        return True

    def get(self, key: str | int, default=None) -> any:
        """Retrieve a value from the cache."""
        return self.cache.get(key, default)

    def delete(self, key: str) -> bool:
        """Delete a key from the cache."""
        if key not in self.cache:
            LOGS.error("No such key: %s", key)
            return False
        self.cache.pop(key, None)
        return True

    # Data type handler #
    @property
    def list(self):

        class ListWrapper:
            """Handling lists."""  # Hehe...

            def __init__(self, parent) -> None:
                self.parent = parent

            def set(self, key: str | int, value: any) -> bool:
                """Set or extend a value to a list in the cache."""
                if key not in self.parent.cache:
                    self.parent.cache[key] = []

                if isinstance(value, list):
                    self.parent.cache[key].extend(
                        x for x in value if x not in self.parent.cache[key]
                    )
                elif value not in self.parent.cache[key]:
                    self.parent.cache[key].append(value)
                return True

            def delete(self, key: str | int, value: any) -> bool:
                """Remove a value from a list in the cache."""
                if key in self.parent.cache and isinstance(
                    self.parent.cache[key], list
                ):
                    try:
                        self.parent.cache[key].remove(value)
                        if not self.parent.cache[key]:
                            del self.parent.cache[key]  # Remove empty list
                            return True
                        return True
                    except ValueError:
                        return False
                return False

        return ListWrapper(self)

    @property
    def dict(self):

        class DictWrapper:
            """Handling dictionaries."""  # Hehe(2)...

            def __init__(self, parent) -> bool:
                self.parent = parent

            def set(self, dict_key: str | int, sub_key: str | int, value: any) -> bool:
                """Set or append a value inside a dictionary in the cache."""
                if dict_key not in self.parent.cache:
                    self.parent.cache[dict_key] = {}

                if isinstance(self.parent.cache[dict_key], dict):
                    if sub_key in self.parent.cache[dict_key]:
                        existing_value = self.parent.cache[dict_key][sub_key]
                        if isinstance(existing_value, list):
                            existing_value.append(value)
                        else:
                            new_value = [existing_value, value]
                            self.parent.cache[dict_key][sub_key] = new_value
                    else:
                        self.parent.cache[dict_key][sub_key] = value
                return True

            def get(
                self,
                dict_key: str | int,
                sub_key: str | int = None,
                default=None,
            ) -> any:
                """Retrieve a value from a dictionary in the cache."""
                if sub_key:
                    return self.parent.cache.get(dict_key, {}).get(sub_key, default)
                return self.parent.cache.get(dict_key, {})

            def delete(self, dict_key: str | int, sub_key: str | int):
                """Delete a key inside a dictionary in the cache."""
                if dict_key in self.parent.cache and isinstance(
                    self.parent.cache[dict_key], dict
                ):
                    self.parent.cache[dict_key].pop(sub_key, None)
                    if not self.parent.cache[dict_key]:  # Remove empty dictionaries
                        del self.parent.cache[dict_key]

        return DictWrapper(self)

    @property
    def tuple(self):
        class TupleWrapper:
            """Handling tuples."""

            def __init__(self, parent):
                self.parent = parent

            def set(self, key: str | int, value: any) -> bool:
                """Set or add a value to a tuple in the cache."""
                if key not in self.parent.cache:
                    self.parent.cache[key] = (value,)
                elif (
                    isinstance(self.parent.cache[key], tuple)
                    and value not in self.parent.cache[key]
                ):
                    self.parent.cache[key] += (value,)
                return True

            def delete(self, key: str | int, value: any) -> bool:
                """Remove a value from a tuple in the cache."""
                if key in self.parent.cache and isinstance(
                    self.parent.cache[key], tuple
                ):
                    new_tuple = tuple(x for x in self.parent.cache[key] if x != value)
                    self.parent.cache[key] = new_tuple
                    if not new_tuple:
                        del self.parent.cache[key]
                    return True
                return False

        return TupleWrapper(self)

    def clear(self) -> bool:
        """Clear the entire cache."""
        self.cache.clear()
        return True


_util_cache = TempCache(_bot_cache)


def load_modules(directory: str):
    """
    Dynamically imports all Python files inside the given directory.

    The directory should be placed in the root directory of this project.
    Or pass the directory like so: `path/to/module_dir`
    """
    # Get the root directory.
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    module_dir = os.path.join(base_dir, str(directory))
    if not os.path.exists(module_dir):
        raise FileNotFoundError(f"No such directory: '{module_dir}'")

    for file in os.listdir(module_dir):
        if file.endswith(".py") and not file.startswith("__"):
            module_name = f"{module_dir}.{file[:-3]}"
            try:
                importlib.import_module(module_name)
                _util_cache.dict.set("loaded_plugins", directory, module_name)

            except Exception as e:
                # debugging-purpose
                # pylint: disable=import-outside-toplevel
                import sys

                tb = traceback.format_exc()
                LOGS.error("Failed to load %s: %s\n%s", module_name, e, tb)
                sys.exit()


# If you don't know or you're not sure what you're doing,
# It's best to NOT touch this thing below.
# This is for YOUR safety, preventing accidental dangerous operations,
# and preventing trolls from ruining your system.

# inspired by:
# https://github.com/Danish-00


class KeepSafe:  # pylint: disable=missing-class-docstring
    def __init__(self) -> None:
        self.__data = MappingProxyType(
            {
                "All": (
                    "BOT_TOKEN",
                    "DeleteAccountRequest",
                    "base64",
                    "bash",
                    "call_back",
                    "get_me",
                    'get_entity("me")',
                    "get_entity('me')",
                    "exec",
                    "os.system",
                    "subprocess",
                    "await locals()",
                    "await globals()",
                    "async_eval",
                    ".session.save()",
                    ".auth_key.key",
                    "KeepSafe",
                    ".flushall",
                    ".env",
                    "DEVS",
                ),
                "Cmds": (
                    "rm -rf",
                    "shutdown",
                    "reboot",
                    "halt",
                    "poweroff",
                    "mkfs",
                    "dd",
                    ":(){ :|: & };:",
                ),
                "Keys": (
                    "bot_token",
                    "api_id",
                    "api_hash",
                    "mongo_uri",
                    "database_url",
                ),
            }
        )

    __module__ = "builtins"

    __class__ = type

    def __dir__(self) -> list:
        return []

    def __repr__(self) -> str:
        return "<built-in function KeepSafe>"

    def __call__(self) -> str:
        raise TypeError("KeepSafe object is not callable")

    def __str__(self) -> str:
        return "<built-in function KeepSafe>"

    def get(self) -> str:
        return self.__data


def is_dangerous(cmd: str) -> bool:
    """
    Determine wheter something is considered dangerous or not.

    Args:
        cmd (:obj:`str`): The string to be analyzed.

    Returns:
        :obj:`bool`: `True` if it's dangerous.
    """
    return any(c in cmd for c in KeepSafe().get()["Cmds"]) or any(
        d in cmd for d in KeepSafe().get()["All"]
    )


def censors(text: str) -> str:
    """Censors sensitive information from output."""
    if not text:
        return text

    _env = os.environ
    for key in _env:
        if any(k in key.lower() for k in KeepSafe().get()["Keys"]):
            text = text.replace(_env[key], "")

    return text
