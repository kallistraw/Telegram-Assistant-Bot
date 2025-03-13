import asyncio

from . import *
from .utils.helper import load_modules


async def main():
    LOGS.info("Initializing...")
    load_modules()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
