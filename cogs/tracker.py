import discord
from discord.ext import commands
import os
import datetime
import database
import re

class TrackerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.target_bot_id = int(os.getenv("TARGET_BOT_ID", 0))
        self.target_prefix = os.getenv("TARGET_PREFIX", ".")
        self.tracking_channel_id = int(os.getenv("TRACKING_CHANNEL_ID", 0))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
            
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        # 1. Track prefix commands in the specific channel
        if message.channel.id == self.tracking_channel_id and not message.author.bot:
            if message.content.startswith(self.target_prefix):
                # Extract command name
                content_without_prefix = message.content[len(self.target_prefix):].strip()
                if content_without_prefix:
                    command_name = content_without_prefix.split()[0].lower()
                    await database.log_activity(
                        guild_id=message.guild.id,
                        user_id=message.author.id,
                        timestamp=now_utc,
                        command_type="prefix",
                        command_name=command_name
                    )

        # 2. Track slash commands from the target bot
        if message.author.id == self.target_bot_id:
            # Check for kakera rolls in embeds
            if message.embeds:
                for embed in message.embeds:
                    if embed.description and re.search(r"Claims:\s*#[\d,]+", embed.description) and re.search(r"Likes:\s*#[\d,]+", embed.description):
                        # Extract the kakera value using regex
                        match = re.search(r'\b([\d,]+)\b[*_~\s]*<a?:kakera:\d+>', embed.description)
                        if match:
                            kakera_value = int(match.group(1).replace(',', ''))
                            character_name = embed.title or (embed.author.name if getattr(embed.author, "name", None) else None)
                            if not character_name:
                                character_name = "Unknown"
                            await database.log_kakera(message.guild.id, now_utc, kakera_value, character_name)
                        break

            if hasattr(message, "interaction_metadata") and message.interaction_metadata is not None:
                # For discord.py 2.4.0+ interaction metadata
                user_id = message.interaction_metadata.user.id
                command_name = getattr(message.interaction_metadata, "name", "button_click")
                if command_name:
                    await database.log_activity(
                        guild_id=message.guild.id,
                        user_id=user_id,
                        timestamp=now_utc,
                        command_type="slash",
                        command_name=command_name.lower()
                    )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Only care about messages from the target bot
        if after.author.id != self.target_bot_id:
            return
            
        if not after.embeds:
            return
            
        # Check if it's a Mudae character roll embed
        for idx, after_embed in enumerate(after.embeds):
            if after_embed.description and re.search(r"Claims:\s*#[\d,]+", after_embed.description) and re.search(r"Likes:\s*#[\d,]+", after_embed.description):
                
                # Check if the message or embed was actually edited
                is_edited = False
                if before.content != after.content:
                    is_edited = True
                elif before.embeds and len(before.embeds) > idx:
                    if before.embeds[idx].to_dict() != after_embed.to_dict():
                        is_edited = True
                else:
                    is_edited = True # If before didn't have the embed but after does
                    
                if is_edited:
                    if after_embed.footer and after_embed.footer.text and "Belongs to " in after_embed.footer.text:
                        claimed_user = after_embed.footer.text.split("Belongs to ")[1].strip()
                        claimed_user = claimed_user.split("~")[0].strip()

                        match = re.search(r'\b([\d,]+)\b[*_~\s]*<a?:kakera:\d+>', after_embed.description)
                        kakera_value = 0
                        if match:
                            kakera_value = int(match.group(1).replace(',', ''))

                        character_name = after_embed.title or (after_embed.author.name if getattr(after_embed.author, "name", None) else "Unknown")

                        now_utc = datetime.datetime.now(datetime.timezone.utc)
                        await database.log_kakera_claim(after.guild.id, claimed_user, character_name, kakera_value, now_utc)
                break

async def setup(bot: commands.Bot):
    await bot.add_cog(TrackerCog(bot))
