from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import errors
from . import var, log
from telethon import events
import traceback

# This wrapper thingy is inspired by https://github.com/TeamUltroid/Ultroid/tree/main/pyUltroid/startup/_database.py
# Special Thanks to every developers of Ultroid
class MongoDB:
    def __init__(self, uri, dbname="TGBotDB", collection="data"):
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=10000)
            self.db = self.client[dbname]
            self.collection = self.db[collection]
            self.collection.create_index("_id")
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Connection Error: {e}\n{tb}"
            log.error(err)
            self.client = None

    def __repr__(self):
        return f"<MongoDB (db: {self.db.name}, collection: {self.collection.name}, total_keys: {self.count_keys()})>"

    def ping(self):
        """Check if the database is reachable."""
        try:
            self.client.admin.command("ping")
            return True
        except errors.PyMongoError:
            return False

    def count_keys(self):
        """Count the number of stored key-value pairs."""
        return self.collection.count_documents({})

    def set(self, key, value):
        """Store or update a key-value pair."""
        try:
            self.collection.update_one({"_id": key}, {"$set": {"value": value}}, upsert=True)
            return True
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Set Key Error: {e}\n{tb}"
            log.error(err)
            return False, err

    def get(self, key):
        """Retrieve a value by key."""
        try:
            doc = self.collection.find_one({"_id": key}, {"_id": 0, "value": 1})
            return doc["value"] if doc else None
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Get Key Error: {e}\n{tb}"
            log.error(err)
            return None, err

    def delete(self, key):
        """Remove a key-value pair."""
        try:
            result = self.collection.delete_one({"_id": key})
            return result.deleted_count > 0
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Delete Key Error: {e}\n{tb}"
            log.error(err)
            return False, err

    def keys(self):
        """List all stored keys."""
        try:
            return [doc["_id"] for doc in self.collection.find({}, {"_id": 1})]
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Keys Error: {e}\n{tb}"
            log.error(err)
            return [], err

    def flushall(self):
        """Delete all key-value pairs in the collection."""
        try:
            self.collection.delete_many({})
            return True
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Flush All Error: {e}\n{tb}"
            log.error(err)
            return False, err

    def usage(self):
        """Return the database size in bytes."""
        try:
            return self.db.command("dbstats")["dataSize"]
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Usage Error: {e}\n{tb}"
            log.error(err)
            return 0, err

    
    def add_user(self, group_key, user_id):
        """Add a user ID to a list without resetting existing values."""
        try:
            self.collection.update_one(
                {"_id": group_key}, 
                {"$addToSet": {"value": user_id}},  # Prevents duplicates
                upsert=True
            )
            return True
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Add User Error: {e}\n{tb}"
            log.error(err)
            return False, err

    def get_users(self, group_key):
        """Retrieve the list of user IDs from a group (e.g., 'admins')."""
        try:
            doc = self.collection.find_one({"_id": group_key}, {"_id": 0, "value": 1})
            return doc["value"] if doc else []
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Get Users Error: {e}\n{tb}"
            log.error(err)
            return [], err

    def remove_user(self, group_key, user_id):
        """Remove a user ID from the list."""
        try:
            self.collection.update_one(
                {"_id": group_key}, 
                {"$pull": {"value": user_id}}  # Removes user_id from the list
            )
            return True
        except errors.PyMongoError as e:
            tb = traceback.format_exc()
            err = f"MongoDB Remove User Error: {e}\n{tb}"
            log.error(err)
            return False, err

BotDB = MongoDB(var.MONGO_URI, dbname="TGBotDB", collection="data")
