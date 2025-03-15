"""The main configurations"""

from decouple import config


# NOTE: Do NOT override this class.
# Make a new one if you really need to do so.
class ConfigVars:
    """This class is used to manage environment variables."""

    __slots__ = ("_variables",)

    def __init__(self):
        self._variables = {
            # Mandatory
            "BOT_TOKEN": config("BOT_TOKEN", default=None),
            "OWNER_ID": config("OWNER_ID", cast=int, default=0),
            # MongoDB
            "MONGO_URI": config("MONGO_URI", default=None),
            # PostgreSQL
            "DATABASE_URL": config("DATABASE_URL", default=None),
            # Optional
            "BOT_LOGGING": config("BOT_LOGGING", cast=bool, default=True),
            "LOG_CHANNEL": config("LOG_CHANNEL", default=""),
            "PREFIXES": config("PREFIXES", cast=lambda v: v.split(), default="/"),
            "API_ID": config("API_ID", cast=int, default=6),
            "API_HASH": config("API_HASH", default="eb06d4abfb49dc3eeb1aeb98ae0f581e"),
        }

        # Convert LOG_CHANNEL to integer or default to OWNER_ID
        try:
            self._variables["LOG_CHANNEL"] = int(self._variables["LOG_CHANNEL"])
        except ValueError:
            self._variables["LOG_CHANNEL"] = self._variables["OWNER_ID"]

    def __call__(self, key):
        return self._variables.get(key)

    def __reduce__(self):
        raise TypeError("<ConfigVars>")

    def __repr__(self):
        return "<ConfigVars>"
