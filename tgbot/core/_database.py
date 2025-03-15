"""
This module contains a Redis-like key-value wrapper for MongoDB, Postgresql, and SQLite.
"""

# The majority of functions defined here are inspired by Ultroid.
# https://github.com/TeamUltroid/Ultroid
# Very awesome Telegram userbot.
# Seriously, check it out, you'll love it more than you love yourself.
import json
import os
import sys
from ast import literal_eval

from .. import Var
from ..utils import LOGS

# MongoDB stuff
MongoClient = server_api = errors = None  # pylint: disable=invalid-name

psycopg2 = sqlite3 = None  # pylint: disable=invalid-name

if Var("MONGO_URI"):
    try:
        from pymongo import MongoClient, errors, server_api
    except ImportError:
        LOGS.info("Installing 'pymongo'...")
        os.system(f"{sys.executable} -m pip install -q pymongo")
        from pymongo import MongoClient, errors, server_api
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


class _Database:
    """A parent class which serves as a base wrapper."""

    def __init__(self, *args, **kwargs):
        self._cache: dict[str | None, any | None] = {}

    def re_cache(self):
        """Clear cache and fetch the new data to remove outdated value."""
        self._cache.clear()
        for key in self.keys():
            self._cache.update({key: self.get_key(key)})

    def ping(self):
        return True

    @property
    def usage(self):
        return False

    def keys(self):
        return []

    # TODO: WHAT IS THISSS...?
    def set_key(self, key: str, value, cache_only: bool = False):
        """
        Store key-value pair to the database cache and server.

        If `cache_only` is set to `True`, will only store the data to cache.
        """
        value = self._fetchone(data=value)
        self._cache[key] = value
        if cache_only:
            return
        return self.set(str(key), str(value))

    def get_key(self, key: str) -> any | None:
        """
        Returns the cached value if available; otherwise,
        fetches from the database and caches it.

        May return outdated data if the value has changed in the database.

        Use this for **faster access** when real-time updates are **not** required.
        """
        if key in self._cache:
            # Return cached data to avoid unnecessary API requests
            return self._cache[key]

        value = self._fetchone(key)
        self._cache.update({key: value})
        return value

    def del_key(self, key: str):
        """Remove key-value pair from both cache and database server."""
        if key in self._cache:
            del self._cache[key]
        self.delete(key)
        return True

    def _fetchone(self, key: str = None, data=None) -> any | None:
        """
        Fetches the latest value directly from the database, bypassing the cache.

        Slower than the cached method but guarantees up-to-date data.
        You might want to use `set()` instead.
        """
        if key:
            data = self.get(str(key))
        if data and isinstance(data, str):
            try:
                data = literal_eval(data)
            except (ValueError, SyntaxError):
                pass
        return data

    def close(self):
        """Close the database connection."""
        return True

    def delete(self):
        return True

    def get(self):
        return True

    def set(self):
        return True


class MongoDB(_Database):
    """Key-value based wrapper for MongoDB."""

    def __init__(self, uri, dbname="TGBotDB"):
        """Initialize MongoDB connection."""
        self.client = MongoClient(
            uri,
            server_api=server_api.ServerApi(
                version="1", strict=True, deprecation_errors=True
            ),
        )
        self.db = self.client[dbname]
        super().__init__()

    def __repr__(self):
        name = self.db.name
        keys = self.count_keys()
        return f"<MongoDB\n -db: {name}\n -total_keys: {keys}\n>"

    @property
    def name(self):
        return "MongoDB"

    @property
    def usage(self):
        """Return the database size in bytes."""
        return self.db.command("dbstats")["dataSize"]

    def ping(self):
        """Check if the database is reachable"""
        try:
            self.db.admin.command("ping")
            return True
        except errors.PyMongoError:
            return False

    def keys(self):
        """Get all stored keys."""
        return self.db.list_collection_names()

    def set(self, key, value):
        """Store or update a key-value pair."""
        # TODO
        return None


class PostgreSQL(_Database):
    """Key-value based wrapper for PostgreSQL."""

    def __init__(self, dsn):
        self.dsn = dsn
        self.conn = None
        self.cur = None
        try:
            self.conn = psycopg2.connect(dsn=dsn)
            self.conn.autocommit = True
            self.cur = self.conn.cursor()
            self._init_db()
        except Exception as e:
            LOGS.error(e)
            if self.conn:
                self.close()
            sys.exit()
        super().__init__()

    def _init_db(self):
        """Ensure the key-value table exists."""
        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL
            );
        """
        )

    def __repr__(self):
        keys = self.count_keys()
        return f"<PostgeSQL\n -total_keys: {keys}\n>"

    @property
    def name(self):
        return "PostgreSQL"

    @property
    def usage(self):
        """Get the database size in pretty-bytes."""
        self.cur.execute("SELECT pg_size_pretty(pg_relation_size(current_database()));")
        return self.cur.fetchone()[0]

    def set(self, key, value):
        """Set a key-value pair."""
        self.cur.execute(
            """
            INSERT INTO kv_store (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value;
        """,
            (key, json.dumps(value)),
        )
        return True

    def get(self, key):
        """Get a value by key."""
        self.cur.execute("SELECT value FROM kv_store WHERE key = %s;", (key,))
        result = self.cur.fetchone()
        return json.loads(result[0]) if result else None

    def append(self, key, new_value):
        """Append a new item to a JSON list stored in the key."""
        self.cur.execute("SELECT value FROM kv_store WHERE key = %s;", (key,))
        result = self.cur.fetchone()

        if result:
            existing_value = json.loads(result[0])
            if not isinstance(existing_value, list):
                # Convert to list if it's not
                existing_value = [existing_value]

            existing_value.append(new_value)
            self.set(key, existing_value)
        else:
            # Create a new list with the value
            self.set(key, [new_value])
        return True

    def delete(self, key):
        """Delete a key."""
        self.cur.execute("DELETE FROM kv_store WHERE key = %s;", (key,))

    def exists(self, key):
        """Check if a key exists."""
        self.cur.execute("SELECT 1 FROM kv_store WHERE key = %s;", (key,))
        return self.cur.fetchone() is not None

    def keys(self):
        """List all available keys."""
        self.cur.execute("SELECT key FROM kv_store;")
        return [row[0] for row in self.cur.fetchall()]

    def count_keys(self):
        """Get the number of stored keys."""
        self.cur.execute("SELECT COUNT(*) FROM kv_store;")
        return self.cur.fetchone()[0]

    def flush_all(self):
        """Delete all keys (DANGEROUS)."""
        self.cur.execute("DELETE FROM kv_store;")

    def close(self):
        """Close the database connection."""
        self.cur.close()
        self.conn.close()


class SQLite(_Database):
    """Key-value based wrapper for SQLite."""  # Yes, I'm lazy.

    def __init__(self, db_path="kv_store.db"):
        """Initialize SQLite connection."""
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._setup_table()
        super().__init__()

    def __repr__(self):
        keys = self.count_keys()
        return f"<SQLite\n -total_keys: {keys}\n>"

    def _setup_table(self):
        """Setup KV Table."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        )
        self.conn.commit()
        return True

    @property
    def name(self):
        return "SQLite"

    def set(self, key, value):
        """
        Store a key-value pair or update the value of an existing key
        """
        json_value = json.dumps(value)

        self.cursor.execute(
            """
            INSERT INTO kv_store (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
            (key, json_value),
        )
        self.conn.commit()

    def get(self, key):
        """Retrieve value from the given key."""
        self.cursor.execute("SELECT value, type FROM kv_store WHERE key=?", (key,))
        result = self.cursor.fetchone()
        return json.loads(result[0]) if result else None

    def delete(self, key):
        """Delete a key-value pair."""
        self.cursor.execute("DELETE FROM kv_store WHERE key=?", (key,))
        self.conn.commit()

    def keys(self):
        """Get all keys."""
        self.cursor.execute("SELECT key FROM kv_store")
        return [row[0] for row in self.cursor.fetchall()]

    def items(self):
        """Get all key-value pairs."""
        self.cursor.execute("SELECT key, value FROM kv_store")
        return dict(self.cursor.fetchall())

    def close(self):
        """Close the database connection."""
        self.conn.close()


# Technically, this is a class, not a function...
def BotDB():  # pylint: disable=ìnvalid-name
    try:
        if MongoClient:
            return MongoDB(Var("MOMGO_URI"))
        elif psycopg2:
            return PostgreSQL(Var("DATABASE_URL"))
        else:
            LOGS.warning("No DB requirements found! Using local database for now.")
            return SQLite()
    except BaseException as e:
        LOGS.exception(e)
    exit()
