
import os
import asyncio
import logging

from dotenv import load_dotenv
from core.bot import BotCore


# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("Bot")


async def main():

    if not TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Please configure your bot token."
        )

    bot = BotCore()

    try:
        async with bot:
            logger.info("Starting Discord bot...")
            await bot.start(TOKEN)

    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")

    except Exception:
        logger.exception("Bot encountered an unexpected error.")
        raise


if __name__ == "__main__":
    asyncio.run(main())
