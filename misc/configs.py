from decouple import config
from telethon.sync import TelegramClient

class var:
    # Mandatory
    API_ID = config("API_ID", cast=int, default=6)
    API_HASH = config("API_HASH", default="eb06d4abfb49dc3eeb1aeb98ae0f581e")
    BOT_TOKEN = config("BOT_TOKEN", default=None)
    MONGO_URI = config("MONGO_URI", default=None)
    OWNER_ID = config("OWNER_ID", cast=int, default=0)

    # Optional
    BOT_LOGGING = config("BOT_LOGGING", cast=bool, default=False)
    LOG_CHANNEL = config("LOG_CHANNEL", cast=int, default=0)
    PREFIXES = config("PREFIXES", cast=list, default=["/"])

bot = TelegramClient("TGBot", var.API_ID, var.API_HASH).start(bot_token=var.BOT_TOKEN)
