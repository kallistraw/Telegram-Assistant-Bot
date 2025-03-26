# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
# pylint: disable=C0116
"""This module contains some helper functions."""
import ast
import json
import os
from types import MappingProxyType
from typing import Any, Collection, Optional, Union

from . import LOGS

__all__ = (
    "censors",
    "get_files",
    "is_dangerous",
    "safe_convert",
    "TempCache",
)


# ----------------------------------------------------------------------------------------------- #
# Handling data types for storing it from Telegram to database


def safe_convert(value: str) -> Union[list, dict, int, float, bool, str]:
    """
    Converts a string into the correct Python data type.

    Handles int, float, list, dict, and bool` safely.
    Useful for handling Telegram message.

    Arguments:
        value (str): The string to be converted.

    Returns:
        int: If the value is a number.
        float: If the value is a float.
        list: If the value is a Python list.
        dict: If the value is a Python dictionary.
        bool: If the value is a Boolean.
        str: If the value is none of the above.
    """
    value = value.strip()

    # Try to parse JSON (for lists/dicts)
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to evaluate numbers, lists, and other basic types
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        pass

    # Check for boolean values
    if value.lower() in ("true", "false"):
        return value.lower() == "true"

    # Try parsing as a number
    try:
        return int(value) if value.lstrip("-").isdigit() else float(value)
    except ValueError:
        pass

    return value  # Default: return as a string


# ----------------------------------------------------------------------------------------------- #
# Cache manager


# Why not...
class TempCache:
    """Cache manager that can handle different data types easily."""

    def __init__(self, cache_dict: Optional[dict]) -> None:
        """
        Initialize with an external dictionary (or create a new one if None).

        Arguments:
            cache_dict (dict, optional):
                The dictionary to use as a temporary cache storage.
        """
        self.cache = cache_dict if cache_dict is not None else {}

    def set(self, key: Union[str, int], value: Union[str, int]) -> bool:
        """Set a value in the cache."""
        self.cache[key] = value
        return True

    def get(self, key: Union[str, int], default: object = None) -> Any:
        """Retrieve a value from the cache."""
        return self.cache.get(key, default)

    def delete(self, key: Union[str, int]) -> bool:
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

            def set(self, key: Union[str, int], value: Any) -> bool:
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

            def delete(self, key: Union[str, int], value: Any) -> bool:
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

            def __init__(self, parent) -> None:
                self.parent = parent

            def set(
                self, dict_key: Union[str, int], sub_key: Union[str, int], value: Any
            ) -> bool:
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
                dict_key: Union[str, int],
                sub_key: Optional[Union[str, int]] = None,
                default=None,
            ) -> Any:
                """Retrieve a value from a dictionary in the cache."""
                if sub_key:
                    return self.parent.cache.get(dict_key, {}).get(sub_key, default)
                return self.parent.cache.get(dict_key, {})

            def delete(self, dict_key: Union[str, int], sub_key: Union[str, int]):
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

            def set(self, key: Union[str, int], value: Any) -> bool:
                """Set or add a value to a tuple in the cache."""
                if key not in self.parent.cache:
                    self.parent.cache[key] = (value,)
                elif (
                    isinstance(self.parent.cache[key], tuple)
                    and value not in self.parent.cache[key]
                ):
                    self.parent.cache[key] += (value,)
                return True

            def delete(self, key: Union[str, int], value: Any) -> bool:
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


# ----------------------------------------------------------------------------------------------- #
# Miscellaneous


def get_files(
    directory: str, extensions: Union[str, Collection[str]], recursive: bool = False
) -> list:
    """
    Fetch all files with the given extension(s) from the specified directory.

    Example:
    .. code-block:: python

        directory_path = "/path/to/directory"

        # Get all Python files inside 'directory_path'
        py_files = get_files(directory_path, ".py")
        print(f"Found {len(py_files)} Python files:\n" + "\n".join(py_files)

        # Get all Python and Ruby files from 'directory_path'
        py_rb_files = get_files(directory_path, [".py", ".rb"])
        print(f"Found {len(py_rb_files)} Python and Ruby files:\n" + "\n".join(py_files)

        # Get all TXT files recursively
        txt_files = get_files(directory_path, ".txt", recursive=True)
        print(f"Found {len(txt_files)} TXT files:\n" + "\n".join(txt_files))

    Arguments:
        directory (str):
            The path to directory.
        extensions (str` or list` of str):
            The extension(s) of the files.
        recursive (bool, optional):
            If set to ``True`, will search files recursively. Defaults to ``False``

    Returns:
        files (list):
            Àll file that ends with :param:`extensions`.
    """
    if not os.path.isdir(directory):
        raise ValueError(f"Invalid directory: {directory}")

    if isinstance(extensions, str):
        extensions = list(extensions)

    if recursive:
        files = []
        for _root, _dirs, _files in os.walk(directory):
            for f in _files:
                if any(f.endswith(ext) for ext in extensions):
                    files.append(f)
        return files

    files = [
        f for f in os.listdir(directory) if any(f.endswith(ext) for ext in extensions)
    ]
    return files


# ----------------------------------------------------------------------------------------------- #
# Safety-related helpers


# If you don't know or you're not sure what you're doing,
# It's best to NOT touch this thing below.
# This is for YOUR safety, preventing accidental dangerous operations,
# and preventing trolls from ruining your system.

# inspired by:
# https://github.com/Danish-00


class KeepSafe:  # pylint: disable=C0115
    def __init__(self) -> None:
        self._data = MappingProxyType(
            {
                "All": (
                    "run_shell",
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
                ),
            }
        )

    __module__ = "builtins"

    __class__ = type

    def __dir__(self) -> list:
        return ["get"]

    def __repr__(self) -> str:
        return "<built-in function KeepSafe>"

    def __call__(self) -> str:
        raise TypeError("KeepSafe object is not callable")

    def __str__(self) -> str:
        return "<built-in function KeepSafe>"

    def get(self) -> str:
        return self._data


def is_dangerous(cmd: str) -> bool:
    """
    Determine wheter an operation is considered dangerous or not.

    Arguments:
        cmd (str): The string of the operation.

    Returns:
        bool: ``True`` if it's dangerous.
    """
    return any(d in cmd for d in KeepSafe().get()["All"])


def censors(text: str) -> str:
    """Censors sensitive information from output."""
    if not text:
        return text

    _env = os.environ
    for key in _env:
        if any(k in key.lower() for k in KeepSafe().get()["Keys"]):
            text = text.replace(_env[key], "")

    return text
