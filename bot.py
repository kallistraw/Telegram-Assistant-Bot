from misc.configs import bot, var
from utils import loader, logger

async def main():
#    await bot.start(bot_token=var.BOT_TOKEN)
    loader.load_modules()  # Load all modules
    logger.log.info("🤖 Bot is running...")
    await bot.run_until_disconnected()


with bot:
    bot.loop.run_until_complete(main())

