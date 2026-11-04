
import os
import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
BASE_DIR = Path(__file__).resolve().parent
COGS_DIR = BASE_DIR / "cogs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("Bot")


class DiscordBot(commands.Bot):

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None
        )

    async def load_all_cogs(self):
        if not COGS_DIR.exists():
            logger.warning("Cogs directory does not exist.")
            return

        extensions = []

        for root, dirs, files in os.walk(COGS_DIR):
            dirs[:] = [
                d for d in dirs
                if not d.startswith("_")
            ]

            for filename in files:
                if not filename.endswith(".py"):
                    continue

                if filename.startswith("_"):
                    continue

                file_path = Path(root) / filename
                relative = file_path.relative_to(BASE_DIR)

                extension = ".".join(relative.with_suffix("").parts)
                extensions.append(extension)

        for extension in sorted(extensions):
            try:
                await self.load_extension(extension)
                logger.info("Loaded: %s", extension)
            except Exception:
                logger.exception("Failed to load: %s", extension)
                raise

    async def setup_hook(self):
        await self.load_all_cogs()

        synced = await self.tree.sync()
        logger.info("Synchronized %s slash commands.", len(synced))


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing.")

    bot = DiscordBot()

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
