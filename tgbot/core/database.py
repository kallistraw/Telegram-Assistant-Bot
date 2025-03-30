"""This mofule contains the SQLite database class"""

import json
import logging
import sys
from abc import ABC, abstractmethod
from os import PathLike, system
from typing import Any, Optional, Union

from tgbot.configs import ConfigVars as Var
from tgbot.utils import LOGS
from tgbot.utils.helpers import format_size, safe_convert

# To avoid unnecessary imports, this has to be here, unfortunately.
# pylint: disable=C0415,C0103
pymongo = psycopg2 = sqlite3 = None
if Var.DATABASE_URL:
    try:
        import psycopg2
    except ImportError:
        LOGS.info("Installing psycopg2...")
        system(f"{sys.executable} -m pip install -q psycopg2-binary")
        import psycopg2

elif Var.MONGO_URI:
    try:
        import pymongo
    except ImportError:
        LOGS.info("Installing 'pymongo'...")
        system(f"{sys.executable} -m pip install -q pymongo")
        import pymongo

else:
    import sqlite3

    LOGS.info("Using local file as the database.")
# pylint: enable=C0415,C0103


class DatabaseError(Exception):
    """
    Wraps errors from the selected database provider into a single exception.

    Arguments:
        exc_origin (Exception): An Exception instance raised by the database provider
    """

    def __init__(self, exc_origin: Exception) -> None:
        self.provider: str = self._detect_db_type(exc_origin)
        super().__init__(
            f"{self.__class__.__name__} [{self.provider}]: {str(exc_origin)}"
        )

    @staticmethod
    def _detect_db_type(error: Exception) -> str:
        """
        Detects which database provider the error came from.

        Arguments:
            error (Exception): An Exception instance.

        Returns:
            str: The database provider name if the `error` come from a known provider.
        """

        if isinstance(error, psycopg2.Error):
            return "PostgreSQL"

        if isinstance(error, pymongo.errors.PyMongoError):
            return "MongoDB"

        if isinstance(error, sqlite3.Error):
            return "SQLite"

        return "Unknown"


# Because we're dealing with SQL, this is necessary to minimize the risk of SQL injection.
class DatabaseMeta(type):
    """Preventing attribute manipulations in runtime."""

    def __setattr__(cls, key, value):
        raise TypeError(f"Cannot modify or add class attribute: {key}")

    def __delattr__(cls, key):
        raise TypeError(f"Cannot delete class attribute: {key}")


class BaseDatabase(ABC, metaclass=DatabaseMeta):
    """
    This is the base class for the database classes with in-memory database.

    Arguments:
        name (str): The database provider name.
        logger (logging.Logger, optional): The logger instance for the database provider.
            Defaults to ``logging.getLogger(__name__)``.

    Attributes:
        cache (dict[str | int | float], Any]): The in-memory database.
        logger (logging.Logger, optional): The logger instance for the database provider.
    """

    __slots__ = (
        "cache",
        "logger",
        "__name",
    )

    def __init__(
        self, name: str, logger: logging.Logger = logging.getLogger(__name__)
    ) -> None:
        self.cache: dict[Union[str, int, float], Any] = {}
        self.logger: logging.Logger = logger
        self.logger.setLevel(logging.INFO)
        self.__name: str = name

    @property
    def name(self) -> str:
        """
        Returns the database provider name.

        Returns:
            str: The database provider name (e.g., PostgreSQL)
        """
        return self.__name

    def set(
        self, key: Union[str, int, float], value: Any, in_memory: bool = False
    ) -> None:
        """
        Stores a key-value pair in an in-memory database and the database server.

        Arguments:
            key (str | int | float): The key unique identifier.
            value (Any): The data/vaĺue to store it in the database.
            in_memory(bool, optional): Whether the key-value pair should only be stored in the
                in-memory database or not. Defaults to ``False``.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        if isinstance(value, str):
            value = safe_convert(value)

        self.cache[key] = value
        if in_memory:
            return

        self.insertone(key, value)
        return

    def get(self, key: Union[str, int, float], default: Any = None) -> Any:
        """
        Retrieves the value of the given key from the in-memory database if the key exists, or will
        fetch the value from the database server if the key does not exists.

        Arguments:
            key(str | int | float): The key unique identifier.
            default(Any, optional): The default value if the key does not exists in both the
                in-memory database and the database server.
        Returns:
            Any: The value of the given key or the value of `default` if the key does not exists.
        """
        if isinstance(key, str):
            key = safe_convert(key)

        if key in self.cache:
            return self.cache[key]

        value = self.fetchone(key, default)
        self.cache[key] = value
        return value

    def pop(self, key: Union[str, int, float]) -> None:
        """
        Deletes the given key and its value from the in-memory database and the database server.

        Arguments:
            key(str | int | float): The key unique identifier.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        if key in self.cache:
            del self.cache[key]

        self.deleteone(key)

    def refresh(self) -> dict:
        """
        Clears the in-memory database and fetch all key-value pairs stored in the database server
        to then store it in the in-memory database.

        Returns:
            dict: The new in-memory database.

        Raises:
            DatabaseError
        """
        self.cache.clear()
        for key, value in self.fetchall(pattern="*"):
            self.cache[key] = value

        return self.cache

    @abstractmethod
    def deleteone(self, key: Union[str, int, float]) -> None:
        """
        This method must be implemented by subclasses to store/update a key-value pairs to the
        database server.

        Arguments:
            key(str | int | float): The key unique identifier.

        Raises:
            DatabaseError
        """

    @abstractmethod
    def insertone(self, key: Union[str, int, float], value: Any) -> None:
        """
        This method must be implemented by subclasses to store/update a key-value pairs to the
        database server.

        Arguments:
            key(str | int | float): The key unique identifier.
            value(Any): The value of `key`.

        Raises:
            DatabaseError
        """

    @abstractmethod
    def fetchone(self, key: Union[str, int, float], default: Any = None) -> Any:
        """
        This method must be implemented by subclasses to fetch the value of the given key from the
        database server.

        Arguments:
            key(str | int | float): The key unique identifier.
            default(Any, optional): The default value if the key does not exists. Defaults to
                ``None``.

        Returns:
            Any: The value of the given key, if the key does not exists will returns the value of
                `default`.

        Raisee:
            DatabaseError
        """

    @abstractmethod
    def fetchall(self, pattern: str) -> Union[dict[Union[str, int, float], Any], list]:
        """
        This method must be implemented by subclasses to fetch all stored data in the database
        server.

        Arguments:
            pattern(str): A pattern to decide what type of data should be returned. Can be either
                `"key"` for returning a list of stored keys, `"value"` for returning a list of
                stored values, or `"*"` for returning key-value pairs in a form of dictionary.

        Returns:
            dict[str | int | float, Any] | list: A dictionary of the key-value pairs, or a list of
                either keys or values.
        """

    @abstractmethod
    def flushall(self) -> None:
        """
        This method must be implemented by subclasses to deletes all stored data in the database
        server.
        """

    @abstractmethod
    @property
    def usage(self) -> str:
        """
        This method must be implemented by subclasses to retrieves the total size of the database.

        Returns:
            str: The total size of the database.
        """

    @abstractmethod
    def close(self) -> None:
        """
        This method must be implemented by subclasses to close the database connection.
        """


class SQLite(BaseDatabase, metaclass=DatabaseMeta):
    """
    A very thin SQLite wrapper.

    Arguments:
        db_path (str | PathLike, optional): A file or path/to/file where the data should be
            stored in.

    Attributes:
        db_path (str): A file or path/to/file whete the data is stored.
        conn (sqlite3.Connection | None): SQLite connection.
        cursor (sqlite3.Cursor | None): SQLite cursor.

    Raises:
        DatabaseError
    """

    __slots__ = ("db_path", "conn", "cursor")

    def __init__(self, db_path: Union[str, PathLike] = ".bot_data.db") -> None:
        """
        Initializes SQLite connection.
        """
        if not isinstance(db_path, (str, PathLike)):
            raise DatabaseError(
                sqlite3.Error(
                    "'db_path' should be either str or os.PathLike, not '{type(db_path)}'"
                )
            )
        self.db_path: Union[str, PathLike] = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self._connect()
        self._create_table()
        super().__init__("SQLite", logging.getLogger("sqlite3"))

    def _connect(self) -> None:
        """
        Establish a connection to the SQLite database.

        Raises:
            DatabaseError
        """
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.cursor = self.conn.cursor()
            self.logger.info("Connected to SQLite.")
        except sqlite3.Error as e:
            if self.conn:
                self.conn.close()
            raise DatabaseError(e) from e

    def _create_table(self) -> None:
        """Create the main table if it doesn't exist."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ? (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """,
            (self.table,),
        )
        self.conn.autocommit = True

    @property
    def table(self) -> str:
        """
        Returns the main table name.

        Returns:
            str: The main table name.
        """
        return "BotDB"

    @property
    def usage(self) -> str:
        """
        Returns the database size in human-readable format.

        Returns:
            str: The database size in human-readable format. (e.g., 100KB)
        """
        self.cursor.execute("PRAGMA page_count;")
        page_count = self.cursor.fetchone()[0]

        self.cursor.execute("PRAGMA page_size;")
        page_size = self.cursor.fetchone()[0]

        byte_size = page_count * page_size
        return format_size(byte_size)

    def insertone(self, key: Union[str, int, float], value: Any) -> None:
        """
        Stores a key-value pair to the database server.

        Note:
            If the `key` is exist in the database, will replace the existing value.

        Arguments:
            key (str | int | float): The key unique identifier.
            value (Any): The value of the key.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        if isinstance(value, str):
            value = safe_convert(value)

        json_value = json.dumps(value)
        try:
            self.cursor.execute(
                """
                INSERT INTO ? (key, value)
                VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
                (self.table, key, json_value),
            )
        except sqlite3.Error as e:
            raise DatabaseError(e) from e

    def fetchone(
        self, key: Union[str, int, float], default: Optional[Any] = None
    ) -> Any:
        """
        Retrieve a value from the database and convert it to its orginal type.

        Arguments:
            key (str | int | float): The key unique identifier.
            default (Any, optional): The default value if the key does not exist. Defaults to
                ``None``.

        Returns:
            Any: The value of `key`, if the key does not exist, will return the value of `default`.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        try:
            self.cursor.execute(
                "SELECT value FROM ? WHERE key=?",
                (
                    self.table,
                    key,
                ),
            )
            row = self.cursor.fetchone()
            return safe_convert(row[0]) if row else default
        except sqlite3.Error as err:
            raise DatabaseError(err) from err

    def deleteone(self, key: Union[str, int, float]) -> None:
        """
        Remove an entry from the database.

        Arguments:
            key (str | int | float): The key unique identifier.
        """
        if isinstance(key, str):
            key = safe_convert(key)

        self.cursor.execute(
            "DELETE FROM ? WHERE key=?",
            (
                self.table,
                key,
            ),
        )

    def fetchall(
        self, pattern: str = "key"
    ) -> Union[dict[Union[str, int, float], Any], list]:
        """
        Retrieves all stored data in the .db file.

        Arguments:
            pattern (str, optional): A patterns to decide what type of data should be returned.
                Can be either `"*"` to returns all key-value pairs, `"key"` to returns all stored
                keys, or `"value"` to returns all stored values.

        Returns:
            dict[str | int | float, Any] | list: If `pattern="*"`, all key-value pairs will be
                returned in a form of Python dictionary. Otherwise, a list of keys or values will
                be returned.

        Raises:
            DatabaseError
        """
        if pattern not in ("*", "key", "value"):
            raise DatabaseError(
                sqlite3.Error(
                    f"Invalid pattern: '{pattern}'. The pattern must be either '*', 'key', or "
                    "'value'."
                )
            )

        try:
            self.cursor.execute("SELECT ? FROM ?", (pattern, self.table))
            rows = self.cursor.fetchall()

            if pattern == "*":
                return dict(rows)
            return [row[0] for row in rows]
        except sqlite3.Error as e:
            raise DatabaseError(e) from e

    def flushall(self) -> None:
        """Clear all stored data."""
        self.cache.clear()
        self.cursor.execute("DELETE FROM ?", (self.table,))

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()


class PostgreSQL(BaseDatabase, metaclass=DatabaseMeta):
    """
    Key-value based wrapper for PostgreSQL.

    Arguments:
        dsn (str): PostgreSQL database url (or connection string).
            It should look someting like this:
                `"postgresql://<username>@<host>:<port>/<database-name>"`
            Or if you set a password:
                `"postgresql://<username>:<password>@<host>:<port>/<database-name>

    Attributes:
        conn (psycopg2.extensions.connection | None): PostgreSQL connection.
        cursor (psycopg2.extensions.cursor | None): PostgreSQL cursor.

    Raises:
        DatabaseError
    """

    __slots__ = ("conn", "cursor")

    def __init__(self, dsn: str) -> None:
        """
        Initializes PostgreSQL connection.
        """
        self.conn: Optional[psycopg2.extensions.connection] = None
        self.cursor: Optional[psycopg2.extensions.cursor] = None
        super().__init__("PostgreSQL", logging.getLogger("psycopg"))
        try:
            self.conn.autocommit = True
            self.conn = psycopg2.connect(dsn=dsn)
            self.cursor: psycopg2.extensions.cursor = self.conn.cursor()
            self._init_db()
        except psycopg2.Error as err:
            if self.conn:
                self.conn.close()

            raise DatabaseError(err) from err

    def _init_db(self) -> None:
        """Creates the main table if it doesn't exist."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ? (
                key TEXT PRIMARY KEY,
                value JSONB
            );
        """,
            (self.table,),
        )

    @property
    def table(self) -> str:
        """
        Returns the main table name.

        Returns:
            str: The main table name.
        """
        return "BotDB"

    @property
    def usage(self) -> str:
        """Retrieves the database size in human-readable format"""
        cmd = "SELECT pg_size_pretty(pg_database_size(current_database)));"
        self.cursor.execute(cmd)
        return self.cursor.fetchone()[0]

    def insertone(self, key: Union[str, int, float], value: Any) -> None:
        """
        Stores a key-value pair to the database server.

        Note:
            If the `key` is exist in the database, will replace the existing value.

        Arguments:
            key (str | int | float): The key unique identifier.
            value (Any): The value of the key.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        value = safe_convert(value)

        try:
            self.cursor.execute(
                """
                INSERT INTO {self.table} (key, value)
                VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value;
            """,
                (key, value),
            )
        except psycopg2.Error as err:
            raise DatabaseError(err) from err

    def fetchone(self, key: Union[str, int, float], default: Any = None) -> Any:
        """
        Retrieves a value from the database and convert it to its orginal type.

        Argumentsù:
            key (str | int | float): The key unique identifier.
            default (Any, optional): The default value if the key does not exist. Defaults to
                ``None``.

        Returns:
            Any: The value of `key`, if the key does not exist, will return the value of `default`.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        try:
            self.cursor.execute(
                "SELECT value FROM ? WHERE key = %s;",
                (
                    self.table,
                    key,
                ),
            )
            result = self.cursor.fetchone()
            return result[0] if result else default
        except psycopg2.Error as err:
            raise DatabaseError(err) from err

    def delete(self, key: Union[str, int, float]) -> None:
        """
        Deletes a key-value pair from the database.

        Arguments:
            key (str | int | float): The key unique identifier.
        """
        if isinstance(key, str):
            key = safe_convert(key)

        if isinstance(key, (tuple, set)):
            key = list(key)

        self.cursor.execute(
            "DELETE FROM ? WHERE key = ?;",
            (
                self.table,
                key,
            ),
        )

    def fetchall(
        self, pattern: str = "key"
    ) -> Union[dict[Union[str, int, float], Any], list]:
        """
        Retrieves all stored data in PostgreSQL's server.

        Arguments:
            pattern (str, optional): A patterns to decide what type of data should be returned.
                Can be either `"*"` to returns all key-value pairs, `"key"` to returns all stored
                keys, or `"value"` to returns all stored values.

        Returns:
            dict[str | int | float, Any] | list: If `pattern="*"`, all key-value pairs will be
                returned in a form of Python dictionary. Otherwise, a list of keys or values will
                be returned.

        Raises:
            DatabaseError
        """
        if pattern not in ("*", "key", "value"):
            raise DatabaseError(
                psycopg2.Error(
                    f"Invalid pattern: '{pattern}'. The pattern must be either '*', 'key', or "
                    "'value'."
                )
            )

        try:
            self.cursor.execute(
                "SELECT ? FROM ?;",
                (
                    pattern,
                    self.table,
                ),
            )
            rows = self.cursor.fetchall()
            if pattern == "*":
                return dict(rows)
            return [row[0] for row in rows]
        except psycopg2.Error as err:
            raise DatabaseError(err) from err

    def count_keys(self) -> int:
        """Counts the number of stored keys in the database."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM ?;", (self.table,))
            return self.cursor.fetchone()[0]
        except psycopg2.Error as err:
            raise DatabaseError(err) from err

    def flushallll(self) -> None:
        """Removes all stored data."""
        self.cache.clear()
        self.cursor.execute("DELETE FROM ?;", (self.table,))

    def close(self) -> None:
        """Closes the database connection."""
        self.cursor.close()
        self.conn.close()


class MongoDB(BaseDatabase):
    """
    Key-value based wrapper for MongoDB.

    Arguments:
        uri (str): MongoDB URI/connection string.
        collection_name (str, optional): The main collection name. Defaults to `"bot_data"`.
        db_name (str, optional): The database name. Defaults to `"BotDB"`.

    Attributes:
        client (pymongo.MongoClient | None): MongoDB client instance.
        collection (pymongo.collection.Collection | None): The main collection.
        db (pymongo.database.Database | None) MongoDB database instance.

    Raises:
        DatabaseError
    """

    __slots__ = (
        "client",
        "collection",
        "db",
    )

    def __init__(
        self,
        uri,
        db_name: Optional[str] = "BotDB",
        collection_name: Optional[str] = "bot_data",
    ) -> None:
        """
        Initializes MongoDB client.
        """
        self.client: Optional[pymongo.MongoClient] = None
        self.collection: Optional[pymongo.collection.Collection] = None
        self.db: Optional[pymongo.database.Database] = None
        super().__init__("MongoDB", logging.getLogger("pymongo"))
        try:
            self.client = pymongo.MongoClient(
                uri,
                server_api=pymongo.server_api.ServerApi("1", deprecation_errors=True),
            )
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
        except pymongo.errors.PyMongoError as err:
            raise DatabaseError(err) from err

    @property
    def usage(self) -> str:
        """
        Returns the database size in human-readable format.

        Returns:
            str: The database size in human-readable format. (e.g., 100KB)
        """
        return format_size(self.db.command("dbstats")["dataSize"])

    def count_keys(self) -> int:
        """
        Counts the number of stored key-value pairs in the MongoDB database server.

        Returns:
            int: The number of stored key-value pairs.
        """
        return self.collection.count_documents({})

    def insertone(self, key: Union[str, int, float], value: Any) -> None:
        """
        Stores a key-value pair to the MongoDB database server.

        Note:
            If the key is exists in the database server, will overwrite the existing value.

        Arguments:
            key (str | int | float): The key unique identifier.
            value (Any): The corresponding value.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        if isinstance(value, str):
            value = safe_convert(value)

        try:
            self.collection.update_one(
                {key: {"$exists": True}}, {"$set": {key: value}}, upsert=True
            )
        except pymongo.errors.PyMongoError as e:
            raise DatabaseError(e) from e

    def fetchone(self, key: Union[str, int, float], default: Any = None) -> Any:
        """
        Retrieves a value of the given key from the MongoDB database server.

        Arguments:
            key (str | int | float): The key unique identifier.

        Returns:
            Any: The value of the given key.

        Raises:
            DatabaseError
        """
        if isinstance(key, str):
            key = safe_convert(key)

        try:
            doc = self.collection.find_one({key: {"$exists": True}}, {key: 1, "_id": 0})
            return doc["value"] if doc else default
        except pymongo.errors.PyMongoError as e:
            raise DatabaseError(e) from e

    def deleteone(self, key: Union[str, int, float]) -> None:
        """
        Removes a key-value pairs from the MongoDB database server.

        Arguments:
            key (str | int | float): The key unique identifier.
        """
        if isinstance(key, str):
            key = safe_convert(key)

        self.collection.delete_one({key: {"$exists": True}})

    def fetchall(
        self, pattern: str = "key"
    ) -> Union[dict[Union[str, int, float], Any], list]:
        """
        Retrieves all stored data from the MongoDB database server.

        Arguments:
            pattern (str, optional): A patterns to decide what type of data should be returned.
                Can be either `"*"` to returns all key-value pairs, `"key"` to returns all stored
                keys, or `"value"` to returns all stored values.

        Returns:
            dict[str | int | float, Any] | list: If `pattern="*"`, all key-value pairs will be
                returned in a form of Python dictionary. Otherwise, a list of keys or values will
                be returned.

        Raises:
            DatabaseError
        """
        if pattern not in ("*", "key", "value"):
            raise DatabaseError(
                pymongo.errors.PyMongoError(
                    f"Invalid pattern: '{pattern}'. The pattern must be either '*', 'key', or "
                    "'value'."
                )
            )

        try:
            docs = self.collection.find({}, {"_id": 0})
            if pattern == "*":
                return docs

            return docs.keys() if pattern == "key" else docs.values()
        except pymongo.errors.PyMongoError as e:
            raise DatabaseError(e) from e

    def flushall(self) -> None:
        """Deletes all key-value pairs in the collection."""
        self.collection.delete_many({})

    def close(self) -> None:
        """Closes the MongoDB database connection."""
        self.client.close()
