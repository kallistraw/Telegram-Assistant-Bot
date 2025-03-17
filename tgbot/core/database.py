"""
This module contains a Redis-like key-value wrapper for MongoDB, PostgreSQL, and SQLite.
"""

from ast import literal_eval

# The majority of functions defined here are inspired by Ultroid.
# https://github.com/TeamUltroid/Ultroid
# Very awesome Telegram userbot.
# Seriously, check it out, you'll love it more than you love yourself.
import json
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


class _Database:
    # pylint: disable=no-member
    """A parent class for the database wrappers."""

    def __init__(self):
        self._cache: dict[int | str, any] = {}

    def re_cache(self):
        """Clear cache and fetch the new data to remove outdated value."""
        self._cache.clear()
        for key in self.keys():
            self._cache.update({key: self.get_key(key)})

    def set_key(self, key: str, value, cache_only: bool = False):
        """
        Store key-value pair to the database cache and server.

        If `cache_only` is set to `True`, will only store the data to cache.
        """
        _value = self._fetchone(key=value)
        self._cache[key] = _value
        if cache_only:
            return True
        return self.set(str(key), str(_value))

    def get_key(self, key: str):
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

    def _fetchone(self, key: str = None) -> any:
        """
        Fetches the latest value directly from the database, bypassing the cache.

        Slower than the cached method but guarantees up-to-date data.
        You might want to use `get()` instead.
        """
        data = None
        if key:
            data = self.get(str(key))
        if data and isinstance(data, str):
            try:
                data = literal_eval(data)
            except (ValueError, SyntaxError):
                pass
        return data

    def rename(self, old_key, new_key):
        """Renames a key without deleting the value."""
        value = self.get_key(old_key)
        if value:
            self.del_key(old_key)
            self.set_key(new_key, value)
            return True
        return False

    # Safe fallbacks
    def ping(self):
        """ping fallback"""
        return True

    @property
    def usage(self):
        """usage fallback"""
        return False

    def keys(self):
        """keys fallback"""
        return []

    def close(self):
        """close fallback"""
        return True


class MongoDB(_Database):
    """Key-value based wrapper for MongoDB."""

    def __init__(self, uri, db_name="TGBot"):
        """Initialize MongoDB."""
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        super().__init__()

    def __repr__(self):
        cluster = self.db.command("ismaster")
        name = cluster.get("setName") if "me" in cluster else "Unknown"
        keys = self.count_keys()
        return f"<MongoDB\n -db: {name}\n -total_keys: {keys}\n>"

    @property
    def name(self):
        """Database service name"""
        return "MongoDB"

    @property
    def usage(self):
        """Returns the database size in a human-readable format"""
        stats = self.db.command("dbStats")
        return naturalsize(stats["dataSize"], binary=True)

    def ping(self):
        """Check if the database is reachable"""
        try:
            self.db.admin.command("ping")
            return True
        except errors.PyMongoError:
            return False

    def set(self, key, value):
        """Stores a key-value pair."""
        collection = self.db[key]
        if key in self.keys():
            collection.replace_one({"_id": key, "value": str(value)})
        else:
            collection.insert_one({"_id": key, "value": str(value)})
        return True

    def get(self, key):
        """Retrieves the value of the given key."""
        collection = self.db[key]
        if k := collection.find_one({"_id": key}):
            return k["value"]
        return False

    def delete(self, key):
        """Deletes a key-value pair."""
        self.db.drop_collection(key)
        return True

    def count_keys(self):
        """Returns the total number of keys."""
        return len(self.db.list_collection_names())

    def keys(self, pattern="*"):
        """Retrieves all available keys."""
        collections = self.db.list_collection_names()
        if pattern == "*":
            return collections
        return [col for col in collections if pattern in col]

    def flush_all(self):
        """Deletes all keys."""
        for collection in self.db.list_collection_names():
            self.db.drop_collection(collection)
        self._cache.clear()
        return True

    def close(self):
        """Closes the database connection."""
        self.client.close()
        return True


class PostgreSQL(_Database):
    """Key-value based wrapper for PostgreSQL."""

    def __init__(self, dsn):
        """Initialize PostgreSQL."""
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
            CREATE TABLE IF NOT EXISTS TGBot (
                key TEXT PRIMARY KEY,
                value JSONB NOT NULL
            );
        """
        )
        return True

    def __repr__(self):
        keys = self.count_keys()
        return f"<PostgeSQL\n -total_keys: {keys}\n>"

    @property
    def name(self):
        """Database service name"""
        return "PostgreSQL"

    @property
    def usage(self):
        """Get the database size in pretty-bytes."""
        cmd = "SELECT pg_size_pretty(pg_relation_size(current_database()));"
        self.cur.execute(cmd)
        return self.cur.fetchone()[0]

    def set(self, key, value):
        """Set a key-value pair."""
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

    def get(self, key):
        """Get a value by key."""
        try:
            self.cur.execute("SELECT value FROM TGBot WHERE key = %s;", (key,))
        except Exception as e:
            LOGS.exception(e)
            return None

        result = self.cur.fetchall()
        if not result:
            return None
        if len(result) >= 1:
            for value in result:
                if value[0]:
                    return value[0]

    def delete(self, key):
        """Delete a key."""
        self.cur.execute("DELETE FROM TGBot WHERE key = %s;", (key,))
        return True

    def keys(self):
        """List all available keys."""
        self.cur.execute("SELECT key FROM TGBot;")
        return [row[0] for row in self.cur.fetchall()]

    def count_keys(self):
        """Get the number of stored keys."""
        self.cur.execute("SELECT COUNT(*) FROM TGBot;")
        return self.cur.fetchone()[0]

    def flush_all(self):
        """Delete all keys."""
        self._cache.clear()
        return self.cur.execute("DELETE FROM TGBot;")

    def close(self):
        """Close the database connection."""
        self.cur.close()
        return self.conn.close()


class SQLite(_Database):
    """Key-value based wrapper for SQLite."""  # Yes, I'm lazy.

    def __init__(self, db_path="TGBot.db"):
        """Initialize SQLite."""
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._setup_table()
        super().__init__()

    def __repr__(self):
        keys = len(self.keys())
        return f"<SQLite\n -total_keys: {keys}\n>"

    def _setup_table(self):
        """Setup KV Table."""
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
    def name(self):
        """Database service name."""
        return "SQLite"

    def set(self, key, value):
        """
        Store a key-value pair or update the value of an existing key
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

    def get(self, key):
        """Retrieve value from the given key."""
        self.cursor.execute("SELECT value, type FROM TGBot WHERE key=?", (key,))
        result = self.cursor.fetchone()
        return json.loads(result[0]) if result else None

    def delete(self, key):
        """Delete a key-value pair."""
        self.cursor.execute("DELETE FROM TGBot WHERE key=?", (key,))
        self.conn.commit()
        return True

    def keys(self):
        """Get all keys."""
        self.cursor.execute("SELECT key FROM TGBot")
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        """Close the database connection."""
        self.conn.close()
        return True


# Lazy loading database instance
_DB_INSTANCE = None


def bot_db():
    """Returns the database instance (MongoDB, PostgreSQL, or SQLite)."""
    global _DB_INSTANCE
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
