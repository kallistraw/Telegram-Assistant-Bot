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
# Formatter


def format_time(value: float, precision: int = 2) -> str:
    """
    Convert a time duration into a human-readable format with multiple units.

    Arguments:
        value(float): The time value in seconds.
        precision(int): Number of decimal places for sub-second values.
    Returns:
        (str): Formatted time string like "1d 14h 6m".
    """
    units = [
        (31540000, "years"),  # years (approx 365.25 days)
        (2.628e6, "months"),  # months (approx 30.44 days)
        (604800, "weeks"),  # weeks
        (86400, "d"),  # days
        (3600, "h"),  # hours
        (60, "m"),  # minutes
        (1, "s"),  # seconds
    ]

    subsecond_units = [
        (1e-3, "ms"),  # milliseconds
        (1e-6, "µs"),  # microseconds
        (1e-9, "ns"),  # nanoseconds
    ]

    # Handle sub-second values separately
    if value < 1:
        for factor, suffix in subsecond_units:
            if value >= factor:
                return f"{value / factor:.{precision}f}{suffix}"
        return f"{value:.{precision}f}s"  # Default to seconds if too small

    # Convert larger values
    parts = []
    for factor, suffix in units:
        if value >= factor:
            count = int(value // factor)
            value %= factor
            parts.append(f"{count}{suffix}")

    return " ".join(parts)


def format_size(size_bytes):
    """Convert a byte size into a human-readable format."""
    if size_bytes == 0:
        return "0B"

    size_units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_units) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_units[i]}"


# ----------------------------------------------------------------------------------------------- #
# Handling data types for storing it from Telegram to database


def safe_convert(value: str) -> Union[list, dict, int, float, bool, str]:
    """
    Converts a string into the correct Python data type.

    Handles int, float, list, dict, and bool safely.
    Useful for handling Telegram message.

    Arguments:
        value (str): The string to be converted.

    Returns:
        (int | float | list | dict | bool | str): The converted value, or the value itself if the
            conversion could not find the expected type.
    """
    value = value.strip()

    # Try to parse JSON first
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to evaluate numbers, lists, and other basic types
    try:
        return ast.literal_eval(value)
    except (ValueError, SyntaxError):
        pass

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
            """Handling tuples."""  # Hehe(3)^_^

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

    Arguments:
        directory (str): The path to directory.
        extensions (str or list of str): The extension(s) of the files.
        recursive (bool, optional): If set to `True`, will search files recursively. Defaults
            to `False`

    Returns:
        files (list): Àll file that ends with `extensions` inside `directory`.
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
# and preventing trolls from ruining your OS.

# inspired by:
# https://github.com/Danish-00


class KeepSafe:  # pylint: disable=C0115
    def __init__(self) -> None:
        self._data = MappingProxyType(
            {
                "All": (
                    "BOT_TOKEN",
                    "base64",
                    "async_exec",
                    "call_back",
                    "get_me",
                    "exec",
                    "os.system",
                    "from os import",
                    "subprocess",
                    "await locals()",
                    "await globals()",
                    "KeepSafe",
                    ".flushall",
                    ".env",
                    "ADMINS",
                    "rm -rf",
                    "shutdown",
                    "reboot",
                    "halt",
                    "poweroff",
                    "mkfs",
                    "dd",
                    "sys.exit",
                    "from sys import",
                    ":(){ :|: & };:",
                ),
                "Keys": (
                    "bot_token",
                    "mongo_uri",
                    "database_url",
                    "api_id",
                    "api_hash",
                ),
            }
        )

    __module__ = "builtins"

    __class__ = type

    def __dir__(self) -> list:
        return []

    def __repr__(self) -> str:
        return f"<built-in function {self.__class__.__name__}"

    def __call__(self) -> str:
        raise TypeError(f"{self.__class__.__name__} object is not callable")

    def get(self) -> str:
        return self._data


def is_dangerous(cmd: str) -> bool:
    """
    Determine whether a code or shell command is considered dangerous or not.

    Arguments:
        cmd (str): The code or shell command.

    Returns:
        bool: `True` if it's dangerous.
    """
    return any(d in cmd for d in KeepSafe().get()["All"])


def censors(text: str) -> str:
    """Censors sensitive information."""
    if not text:
        return text

    _env = os.environ
    for key in _env:
        if any(k in key.lower() for k in KeepSafe().get()["Keys"]):
            text = text.replace(_env[key], "")

    return text
