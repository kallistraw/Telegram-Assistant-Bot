"""This mofule contains the SQLite database class"""

import json
from logging import Logger
import sqlite3
from typing import Any, Optional

from tgbot.utils.helpers import safe_convert


class SQLite:
    """A very thin SQLite wrapper."""

    def __init__(
        self, logger: Logger, db_path: str = ".bot_data.db", table: str = "storage"
    ) -> None:
        self.db_path = db_path
        self.table = table
        self.logger = logger
        self._connect()
        self._create_table()

    @property
    def name(self) -> str:
        """Returns database service name."""
        return "SQLite"

    def _connect(self) -> None:
        """Establish a connection to the SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.logger.info("Connected to SQLite.")

    def _create_table(self) -> None:
        """Create the key-value storage table if it doesn't exist."""
        self.cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table} (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )
        self.conn.autocommit = True

    def set(self, key: str, value: Any) -> None:
        """
        Store a key-value pair in the database and keeping the value type by using :mod:`piickle`.

        Arguments:
            key (str): The key unique name
            value (`Any`): The data/vaĺue

        Note:
            If the `key` is exist in the database, will replace the existing value.
        """
        json_value = json.dumps(value)
        self.cursor.execute(
            f"""
            INSERT INTO {self.table} (key, value)
            VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
            (key, json_value),
        )

    def get(self, key: str, default: Optional[Any] = None) -> Any | None:
        """
        Retrieve a value from the database and convert it to its orginal type.

        Arguments:
            key (str): The key unique name
            default (`Any`, optional): The default value if the key does not exist.
            Defaults to ``None``

        Returns:
            `Any`: The value of `key`, if the key does not exist, will return the
            value of `default`.
        """
        self.cursor.execute(f"SELECT value FROM {self.table} WHERE key=?", (key,))
        row = self.cursor.fetchone()[0]
        return safe_convert(row) if row else default

    def delete(self, key: str) -> None:
        """
        Remove an entry from the database.

        Arguments:
            key (str): The key unique name.
        """
        self.cursor.execute(f"DELETE FROM {self.table} WHERE key=?", (key,))

    def keys(self) -> list:
        """
        Fetch all keys stored in the database.

        Returns:
            list`: The list of stored keys.
        """
        self.cursor.execute(f"SELECT key FROM {self.table}")
        return [row[0] for row in self.cursor.fetchall()]

    def flush(self) -> None:
        """Clear all stored data."""
        self.cursor.execute(f"DELETE FROM {self.table}")

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
