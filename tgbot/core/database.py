# Multi functional Telegram assistant bot.
# Copyright (c) 2025, Kallistra <kallistraw@gmail.com>
#
# This file is a part of <https://github.com/kallistraw/Telegram-Bot-Assistant>
# and is released under the "BSD-3-Clause License". Please read the full license in
# <https://github.com/kallistraw/Telegram-Assistant-Bot/blob/main/LICENSE>
"""
This module contains a Redis-like key-value wrapper for MongoDB, PostgreSQL, and SQLite.
"""

# The majority of functions defined here are inspired by Ultroid.
# https://github.com/TeamUltroid/Ultroid
# Very awesome Telegram userbot.
# Seriously, check it out, you'll love it more than you love yourself.

from ast import literal_eval
import json
from logging import Logger
import os
import sys

from humanize import naturalsize

from ..configs import get_var
from ..utils import LOGS

__all__ = [
    "bot_db",
]

Var = get_var()

# MongoDB stuff
MongoClient = server_api = errors = None  # pylint: disable=invalid-name

psycopg2 = sqlite3 = None  # pylint: disable=invalid-name

if Var("MONGO_URI"):
    try:
        from pymongo import MongoClient, errors
    except ImportError:
        LOGS.info("Installing 'pymongo'...")
        os.system(f"{sys.executable} -m pip install -q pymongo")
        from pymongo import MongoClient, errors
elif Var("DATABASE_URL"):
    try:
        import psycopg2
    except ImportError:
        LOGS.info("Installing 'psycopg2'...")
        os.system(f"{sys.executable} -m pip install -q psycopg2-binary")
        import psycopg2
else:
    try:
        import sqlite3
    except ImportError:
        LOGS.info("Using local file as the database.")
        os.system(f"{sys.executable} -m pip install -q sqlite3")
        import sqlite3


class Database:
    # pylint: disable=no-member
    """
    A parent class for the database wrappers.

    Because the failure of the function in this class is very rare, it would not
    raises an :obj:`Exception`. Instead, the :obj:`Exception` will be handled by the logger.
    """

    def __init__(self, logger: Logger = LOGS) -> None:
        """
        Initialize base wrapper.

        Arguments:
            logger (:obj:`logging.Logger`, optional):
                Logging handler to log details. Defaults to the bot's main logger.
        """
        self._cache: dict[int | str, any] = {}
        self.logger = logger

    def re_cache(self) -> None:
        """Clear cache and fetch the new data to remove outdated value."""
        self._cache.clear()
        for key in self.keys():
            self._cache.update({key: self.get_key(key)})

    def set_key(self, key: str, value, cache_only: bool = False) -> bool:
        """
        Store key-value pair to the database cache and server.

        If `cache_only` is set to `True`, will only store the data to cache.

        Arguments:
            key (:obj:`str`):
                The key name.
            value (:obj:`str`):
                The value of the key.
            cache_only (:obj:`bool`):
                Wheter the key-value pair should only be stored in the cache.

        Returns:
            :obj:`bool`: :obj:`True` if the key-value pair stored succesfully.
        """
        _value = self._fetchone(key=value)
        self._cache[key] = _value
        if cache_only:
            return True
        try:
            return self.set(str(key), str(_value))
        except Exception as e:
            self.logger.exception(e)
            return False

    def get_key(self, key: str) -> str | None:
        """
        Returns the cached value of the given key if available; otherwise,
        fetches from the database and caches it.

        May return outdated data if the value has changed in the database.
        Use this for **faster access** when real-time updates are **not** required.

        Arguments:
            key (:obj:`str`):
                The key name in the database.

        Returns:
            value (:obj:`str` or :obj:`None`):
                The value of the given key, or :obj:`None` if the key name is invalid.
        """
        if key in self._cache:
            # Return cached data to avoid unnecessary API requests
            return self._cache[key]

        value = self._fetchone(key)
        self._cache.update({key: value})
        return value

    def del_key(self, key: str) -> bool:
        """
        Remove key-value pair from both cache and database server.

        Arguments:
            key (:obj:`str`):
                The key name in the database.

        Returns:
            :obj:`bool`: :obj:`True` if the deletion is successful.
        """
        if key in self._cache:
            del self._cache[key]
        try:
            self.delete(key)
            return True
        except Exception as e:
            self.logger.exception(e)
            return False

    def _fetchone(self, key: str = None) -> str | None:
        """
        Fetches the latest value directly from the database, bypassing the cache.

        Slower than the cached method but guarantees up-to-date data.
        You might want to use `get()` instead.

        Arguments:
            key (:obj:`str`):
                The key of which value should be fetched.

        Returns:
            value (:obj:`str` or :obj:`None`):
                The value of the given key, or :obj:`None` if the key name is invalid.
        """
        value = None
        if key:
            value = self.get(str(key))
        if value and isinstance(value, str):
            try:
                value = literal_eval(value)
            except (ValueError, SyntaxError):
                pass
        return value

    def rename(self, key: str, new_key: str) -> bool:
        """
        Renames a key without deleting the value.

        Arguments:
            key (:obj:`str`):
                The current key name.
            new_key (:obj:`str`):
                The new key name.

        Returns:
            :obj:`bool`: ``True`` if the key is renamed.
        """
        value = self.get_key(key)
        if value:
            self.del_key(key)
            self.set_key(new_key, value)
            return True
        return False

    # Safe fallbacks
    def ping(self) -> bool:
        """ping fallback"""
        return True

    @property
    def usage(self) -> bool:
        """usage fallback"""
        return False

    def close(self) -> bool:
        """close fallback"""
        return True


class MongoDB(Database):
    """Key-value based wrapper for MongoDB."""

    def __init__(self, uri, db_name="TGBot") -> None:
        """
        Initialize MongoDB connection.

        Arguments:
            uri (:obj:`str`):
                MongoDB URI (or connection string).
            db_name (:obj:`str`, optional):
                The database name. Defaults to `"TGBot"`
        """
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        super().__init__()

    def __repr__(self) -> str:
        cluster = self.db.command("ismaster")
        name = cluster.get("setName") if "me" in cluster else "Unknown"
        keys = self.count_keys()
        return f"<MongoDB\n -db: {name}\n -total_keys: {keys}\n>"

    @property
    def name(self) -> str:
        """Database service name"""
        return "MongoDB"

    @property
    def usage(self) -> str:
        """Returns the database size in a human-readable format"""
        stats = self.db.command("dbStats")
        return naturalsize(stats["dataSize"], binary=True)

    def ping(self) -> bool:
        """Check if the database is reachable"""
        try:
            self.db.admin.command("ping")
            return True
        except errors.PyMongoError:
            return False

    def set(self, key: str, value: str) -> bool:
        """
        Stores a key-value pair to MongoDB database.

        Arguments:
            key (:obj:`str`):
                The key name.
            value (:obj:`str`):
                The value of the key.

        Returns:
            :obj:`True` if the key-value pair stored successfully.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        collection = self.db[key]
        if key in self.keys():
            collection.replace_one({"_id": key, "value": str(value)})
        else:
            collection.insert_one({"_id": key, "value": str(value)})
        return True

    def get(self, key: str) -> str | None:
        """
        Retrieves the value of the given key from the database.

        Arguments:
            key (:obj:`str`):
                The key name.

        Returns:
            value (:obj:`str`, or :obj:`None`):
                The value of the given key, or :obj:`None` if the key name is invalid.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        collection = self.db[key]
        value = None
        if k := collection.find_one({"_id": key}):
            value = k["value"]
            return value
        return value

    def delete(self, key: str) -> bool:
        """
        Deletes a key-value pair from the database.

        Arguments:
            key (:obj:`str`):
                The key name.

        Returns:
            :obj:`True` if the key-value pair is deleted successfully.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self.db.drop_collection(key)
        return True

    def count_keys(self) -> int:
        """
        Count the total number of keys in the database.

        Returns:
            :obj:`int`

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        return len(self.db.list_collection_names())

    def keys(self, pattern: str = "*") -> list:
        """
        Retrieves all available keys from the database.

        Arguments:
            pattern (:obj:`str`, optional):
                A pattern that should be used to filter the results. Defaults to `"*"` (all).

        Returns:
            :obj:`list` of all available keys that matches the pattern

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        collections = self.db.list_collection_names()
        if pattern == "*":
            return collections
        return [col for col in collections if pattern in col]

    def flush_all(self) -> bool:
        """
        Deletes all keys in the database.

        Returns:
            :obj:`True` if the process is successful.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        for collection in self.db.list_collection_names():
            self.db.drop_collection(collection)
        self._cache.clear()
        return True

    def close(self) -> bool:
        """
        Closes the database connection.

        Returns:
            :obj:`True` if the connection is closed.
        """
        self.client.close()
        return True


class PostgreSQL(Database):
    """Key-value based wrapper for PostgreSQL."""

    def __init__(self, dsn) -> None:
        """
        Initialize PostgreSQL connection.

        Arguments:
            dsn (:obj:`str`):
                PostgreSQL database url (or connection string).
                It should look someting like this:
                `"postgresql://<username>@<host>:<port>/<database-name>"`
                or if you set a password:
                `"postgresql://<username>:<password>@<host>:<port>/<database-name>
        """
        super().__init__()
        self.dsn = dsn
        self.conn = None
        self.cur = None
        try:
            self.conn = psycopg2.connect(dsn=dsn)
            self.conn.autocommit = True
            self.cur = self.conn.cursor()
            self._init_db()
        except psycopg2.OperationalError as e:
            self.logger.error("OperationalError: %s", e)
            if self.conn:
                self.close()
            sys.exit(1)
        except psycopg2.ProgrammingError as e:
            self.logger.error("ProgrammingError: %s", e)
            if self.conn:
                self.close()
            sys.exit(1)
        except psycopg2.InterfaceError as e:
            self.logger.error("InterfaceError: %s", e)
            if self.conn:
                self.close()
            sys.exit(1)
        except psycopg2.DatabaseError as e:
            self.logger.error("DatabaseError: %s", e)
            if self.conn:
                self.close()
            sys.exit(1)
        except Exception as e:
            self.logger.error(e)
            if self.conn:
                self.close()
            sys.exit(1)

    def _init_db(self) -> bool:
        """
        Ensure the table exists.

        Returns:
            :obj:`True` if the table is exist or created successfully.
        """
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS TGBot (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL
            );
        """
        )
        return True

    def __repr__(self) -> str:
        """Returns PostgreSQL details"""
        self.cur.execute("SELECT current_user;")
        name = self.cur.fetchone()[0]
        self.cur.execute("SELECT current_database()")
        db_name = self.cur.fetchone()[0]
        keys = self.count_keys()
        return f"<PostgeSQL\n  name: {name}\n  database: {db_name}\n  total_keys: {keys}\n>"

    @property
    def name(self) -> str:
        """Database service name"""
        return "PostgreSQL"

    @property
    def usage(self) -> str:
        """Get the database size in human-readable format"""
        cmd = "SELECT pg_size_pretty(pg_database_size(TGBot));"
        self.cur.execute(cmd)
        return self.cur.fetchone()[0]

    def set(self, key: str, value: str) -> bool:
        """
        Stores a key-value pair to the database.

        Arguments:
            key (:obj:`str`):
                The key name.
            value (:obj:`str`):
                The value of the key.

        Returns:
            :obj:`True` if the key-value pair stored successfully.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self.cur.execute(
            """
            INSERT INTO TGBot (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value;
        """,
            (key, str(value)),
        )
        return True

    def get(self, key: str) -> str | None:
        """
        Retrieves the value of the given key from the database.

        Arguments:
            key (:obj:`str`):
                The key name.

        Returns:
            value (:obj:`str`, or :obj:`None`):
                The value of the given key, or :obj:`None` if the key name is invalid.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        try:
            self.cur.execute("SELECT value FROM TGBot WHERE key = %s;", (key,))
            result = self.cur.fetchone()
            return result[0] if result else None
        except Exception as e:
            self.logger.exception(e)
            return None

    def delete(self, key: str) -> bool:
        """
        Deletes a key-value pair from the database.

        Arguments:
            key (:obj:`str`):
                The key name.

        Returns:
            :obj:`True` if the key-value pair is deleted successfully.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self.cur.execute("DELETE FROM TGBot WHERE key = %s;", (key,))
        return True

    def keys(self) -> list:
        """
        Retrieves all available keys from the database.

        Arguments:
            pattern (:obj:`str`, optional):
                A pattern that should be used to filter the results. Defaults to `"*"` (all).

        Returns:
            :obj:`list` of all available keys that matches the pattern

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self.cur.execute("SELECT key FROM TGBot;")
        return [row[0] for row in self.cur.fetchall()]

    def count_keys(self) -> int:
        """Get the number of stored keys in the database."""
        self.cur.execute("SELECT COUNT(*) FROM TGBot;")
        return self.cur.fetchone()[0]

    def flush_all(self) -> bool:
        """
        Deletes all keys in the database.

        Returns:
            :obj:`True` if the process is successful.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self._cache.clear()
        self.cur.execute("DELETE FROM TGBot;")
        return True

    def close(self) -> bool:
        """
        Closes the database connection.

        Returns:
            :obj:`True` if the connection is closed.
        """
        self.cur.close()
        self.conn.close()
        return True


class SQLite(Database):
    """Key-value based wrapper for SQLite."""  # Yes, I'm lazy.

    def __init__(self, db_path="TGBot.db") -> None:
        """
        Initialize SQLite connection.

        Arguments:
            db_path (:obj:`str`, optional):
            A file name or path to file which will be used to store the data.
            Defaults to `TGBot.db`
        """
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._setup_table()
        super().__init__()

    def __repr__(self) -> str:
        keys = len(self.keys())
        return f"<SQLite\n -total_keys: {keys}\n>"

    def _setup_table(self) -> bool:
        """
        Ensure the table exists.

        Returns:
            :obj:`True` if the table is exist or created successfully.
        """
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS TGBot (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )
        self.conn.commit()
        return True

    @property
    def name(self) -> str:
        """Database service name."""
        return "SQLite"

    def set(self, key: str, value: str) -> bool:
        """
        Stores a key-value pair to the database.

        Arguments:
            key (:obj:`str`):
                The key name.
            value (:obj:`str`):
                The value of the key.

        Returns:
            :obj:`True` if the key-value pair stored successfully.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        json_value = json.dumps(value)

        self.cursor.execute(
            """
            INSERT INTO TGBot (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
            (key, json_value),
        )
        self.conn.commit()
        return True

    def get(self, key: str) -> str | None:
        """
        Retrieves the value of the given key from the database.

        Arguments:
            key (:obj:`str`):
                The key name.

        Returns:
            value (:obj:`str`, or :obj:`None`):
                The value of the given key, or :obj:`None` if the key name is invalid.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self.cursor.execute("SELECT value, type FROM TGBot WHERE key=?", (key,))
        result = self.cursor.fetchone()
        return json.loads(result[0]) if result else None

    def delete(self, key: str) -> bool:
        """
        Deletes a key-value pair from the database.

        Arguments:
            key (:obj:`str`):
                The key name.

        Returns:
            :obj:`True` if the key-value pair is deleted successfully.

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self.cursor.execute("DELETE FROM TGBot WHERE key=?", (key,))
        self.conn.commit()
        return True

    def keys(self) -> list:
        """
        Retrieves all available keys from the database.

        Arguments:
            pattern (:obj:`str`, optional):
                A pattern that should be used to filter the results. Defaults to `"*"` (all).

        Returns:
            :obj:`list` of all available keys that matches the pattern

        May raise an ``Exception`` if the process is failed due to server-related issue.
        """
        self.cursor.execute("SELECT key FROM TGBot")
        return [row[0] for row in self.cursor.fetchall()]

    def close(self) -> bool:
        """
        Closes the database connection.

        Returns:
            :obj:`True` if the connection is closed.
        """
        self.cursor.close()
        self.conn.close()
        return True


# Lazy loading database instance
_DB_INSTANCE = None


def bot_db():
    """Returns the database instance (MongoDB, PostgreSQL, or SQLite)."""
    global _DB_INSTANCE  # pylint: disable=global-statement
    if _DB_INSTANCE is None:
        _DB_INSTANCE = _init_db()
    return _DB_INSTANCE


def _init_db():
    """Initialize the database instance based on available configs."""
    try:
        if Var("MONGO_URI"):
            return MongoDB(Var("MONGO_URI"))
        if Var("DATABASE_URL"):
            return PostgreSQL(Var("DATABASE_URL"))

        LOGS.warning("No DB requirements found! Using local database for now.")
        return SQLite()
    except BaseException as e:
        LOGS.exception(e)
        return None
