from decouple import config


## NOTE: For whatever reason, do NOT override this class. (unless you know what you're doing)
## Make a new one if you really need to do so.
class ConfigVars:
    __slots__ = ("_settings",)

    def __init__(self):
        self._settings = {
            # Mandatory
            "BOT_TOKEN": config("BOT_TOKEN", default=None),
            "MONGO_URI": config("MONGO_URI", default=None),
            "OWNER_ID": config("OWNER_ID", cast=int, default=0),
            # Optional
            "BOT_LOGGING": config("BOT_LOGGING", cast=bool, default=False),
            "LOG_CHANNEL": config("LOG_CHANNEL", cast=int, default=0),
            "PREFIXES": config("PREFIXES", cast=lambda v: v.split(), default="/"),
            "API_ID": config("API_ID", cast=int, default=6),
            "API_HASH": config("API_HASH", default="eb06d4abfb49dc3eeb1aeb98ae0f581e"),
        }

    def __call__(self, key):
        return self._settings.get(key)

    def __reduce__(self):
        raise TypeError("<ConfigVars>")

    def __repr__(self):
        return "<ConfigVars>"
