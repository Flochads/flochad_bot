import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import database
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content for prefix tracking
intents.members = True          # Needed to look up users by their username or nickname

class TrackerBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=",",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Initialize database
        await database.setup_db()
        logging.info("Database initialized.")

        # Load cogs
        initial_extensions = [
            "cogs.basic",
            "cogs.tracker",
            "cogs.stats"
        ]
        
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
                logging.info(f"Loaded extension '{extension}'")
            except Exception as e:
                logging.error(f"Failed to load extension {extension}. Error: {e}")

        # Sync slash commands
        logging.info("Syncing slash commands...")
        await self.tree.sync()
        logging.info("Slash commands synced.")

    async def on_ready(self):
        logging.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logging.info("------")

if __name__ == "__main__":
    bot = TrackerBot()
    token = os.getenv("DISCORD_TOKEN")
    
    if not token or token == "your_bot_token_here":
        logging.error("Please set a valid DISCORD_TOKEN in the .env file.")
    else:
        bot.run(token)
