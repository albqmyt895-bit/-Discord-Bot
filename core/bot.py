
import logging
from pathlib import Path

import discord
from discord.ext import commands

from core.database import Database


logger = logging.getLogger("Bot.Core")


class BotCore(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=self._get_intents(),
            help_command=None
        )

        self.db = Database()
        self.base_dir = Path(__file__).resolve().parent.parent
        self._database_ready = False

    @staticmethod
    def _get_intents():
        intents = discord.Intents.default()

        intents.members = True
        intents.message_content = True

        return intents

    async def setup_hook(self):
        # Connect to database
        await self.db.connect()
        self._database_ready = True

        logger.info("Database connected successfully.")

        # Load all extensions automatically
        await self.load_extensions()

        logger.info("Bot setup completed.")

    async def load_extensions(self):
        cogs_dir = self.base_dir / "cogs"

        if not cogs_dir.exists():
            logger.warning("Cogs directory not found.")
            return

        extensions = []

        for file in cogs_dir.rglob("*.py"):

            # Ignore private files and folders
            if file.name.startswith("_"):
                continue

            relative = file.relative_to(cogs_dir)

            if any(part.startswith("_") for part in relative.parts):
                continue

            # Convert file path to Python extension
            relative = file.relative_to(self.base_dir)

            extension = ".".join(
                relative.with_suffix("").parts
            )

            extensions.append(extension)

        # Load extensions
        for extension in sorted(extensions):
            try:
                await self.load_extension(extension)
                logger.info("Loaded extension: %s", extension)

            except Exception:
                logger.exception(
                    "Failed to load extension: %s",
                    extension
                )

    async def close(self):
        try:
            if self._database_ready:
                await self.db.close()
                self._database_ready = False

                logger.info("Database disconnected.")

        finally:
            await super().close()
