import discord
from discord.ext import commands, tasks
import database
from utils.visualization import generate_heatmap
import re
import datetime
import os
import logging

class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tracking_channel_id = int(os.getenv("TRACKING_CHANNEL_ID", 0))
        self.owner_id = int(os.getenv("OWNER_ID", 0))
        self.hourly_topk_alert.start()

    def cog_unload(self):
        self.hourly_topk_alert.cancel()

    async def _build_topk_embed(self, guild_id: int, since: datetime.datetime, hours: float, label: str, limit: int = 5):
        """Returns (embed, fallback_message). Exactly one is non-None."""
        stats = await database.get_kakera_stats(guild_id, since, limit=limit)
        if not stats or stats[0] is None:
            return None, f"No kakera was spawned in the last {label}."

        total_k, avg_k, _max_k, count, top_rolls = stats
        top_claimers = await database.get_top_claimers(guild_id, since, limit=limit)

        embed = discord.Embed(
            title=f"Kakera Spawn Stats (Last {label})",
            color=discord.Color.gold()
        )
        embed.add_field(name="Total Spawned", value=f"**{total_k:,}** Kakera", inline=False)
        embed.add_field(name="Total Rolls", value=f"**{count:,}**", inline=False)
        embed.add_field(name="Average per Roll", value=f"**{avg_k:,.2f}** Kakera", inline=False)

        hourly_total = total_k / hours if hours > 0 else total_k
        hourly_rolls = count / hours if hours > 0 else count
        embed.add_field(name="Hourly Averages", value=f"**{hourly_total:,.2f}** Kakera/hr\n**{hourly_rolls:,.2f}** Rolls/hr", inline=False)

        if top_rolls:
            huge_pulls_text = ""
            for char_name, value in top_rolls:
                display_name = char_name if char_name and char_name != "Unknown" else "Unknown Character"
                huge_pulls_text += f"**{value:,}** ({display_name})\n"
            embed.add_field(name="Huge Pulls", value=huge_pulls_text, inline=False)

        if top_claimers:
            winners_text = ""
            for u_name, c_name, val in top_claimers:
                winners_text += f"**{u_name}**: {c_name} ({val:,})\n"
            embed.add_field(name="Biggest Winners", value=winners_text, inline=False)

        return embed, None

    @commands.command(name="server", help="Generate a heatmap for overall server activity.")
    async def server_stats(self, ctx: commands.Context):
        async with ctx.typing():
            timestamps = await database.get_server_stats(ctx.guild.id)
            
            if not timestamps:
                await ctx.send("No activity logged for this server yet.")
                return

            buf = generate_heatmap(timestamps, title=f"Server Activity Heatmap: {ctx.guild.name}")
            if buf is None:
                await ctx.send("Failed to generate heatmap.")
                return

            file = discord.File(fp=buf, filename="server_heatmap.png")
            await ctx.send(file=file)

    @commands.command(name="stats", help="Generate a heatmap for a specific user's activity. You can provide a username, ID, or ping them.")
    async def user_stats(self, ctx: commands.Context, user: discord.Member = None):
        user = user or ctx.author
        async with ctx.typing():
            timestamps = await database.get_user_stats(ctx.guild.id, user.id)
            
            if not timestamps:
                await ctx.send(f"No activity logged for user {user.display_name}.")
                return

            buf = generate_heatmap(timestamps, title=f"User Activity Heatmap: {user.display_name}")
            if buf is None:
                await ctx.send("Failed to generate heatmap.")
                return

            file = discord.File(fp=buf, filename="user_heatmap.png")
            await ctx.send(file=file)

    @user_stats.error
    async def user_stats_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send(f"Could not find that user! You can try using their User ID instead.")

    @commands.command(name="command", help="Generate a heatmap for a specific command's usage.")
    async def command_stats(self, ctx: commands.Context, command_name: str):
        async with ctx.typing():
            command_name_lower = command_name.lower().strip()
            timestamps = await database.get_command_stats(ctx.guild.id, command_name_lower)
            
            if not timestamps:
                await ctx.send(f"No activity logged for command '{command_name_lower}'.")
                return

            buf = generate_heatmap(timestamps, title=f"Command Activity Heatmap: '{command_name_lower}'")
            if buf is None:
                await ctx.send("Failed to generate heatmap.")
                return

            file = discord.File(fp=buf, filename="command_heatmap.png")
            await ctx.send(file=file)

    @commands.command(name="top", help="Shows the most frequent commands used in a specific time frame (e.g. 20m, 20h, 20d).")
    async def top_commands(self, ctx: commands.Context, time_frame: str):
        match = re.match(r"^(\d+)([mhd]?)$", time_frame.lower().strip())
        if not match:
            await ctx.send("Invalid time frame format. Please use a number followed by 'm', 'h', or 'd' (e.g., `20m`, `12h`, `5d`).")
            return
            
        amount_str, unit = match.groups()
        amount = int(amount_str)
        
        if amount <= 0:
            await ctx.send("Please specify a time frame greater than 0.")
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        if unit == 'm':
            delta = datetime.timedelta(minutes=amount)
            unit_name = "minutes"
        elif unit == 'd':
            delta = datetime.timedelta(days=amount)
            unit_name = "days"
        else:
            # Default to hours if 'h' or no unit is provided
            delta = datetime.timedelta(hours=amount)
            unit_name = "hours"
            
        since = now_utc - delta
        
        async with ctx.typing():
            top_cmds = await database.get_top_commands(ctx.guild.id, since)
            
            if not top_cmds:
                await ctx.send(f"No commands were logged in the last {amount} {unit_name}.")
                return
                
            embed = discord.Embed(
                title=f"Top Commands (Last {amount} {unit_name})",
                color=discord.Color.blurple()
            )
            
            description = ""
            for idx, (cmd_name, count) in enumerate(top_cmds, 1):
                description += f"**{idx}.** `{cmd_name}` - {count} uses\n"
                
            embed.description = description
            await ctx.send(embed=embed)

    @commands.command(name="huge", help="Shows kakera spawn stats, huge pulls, and biggest winners for a time frame (e.g. 20m, 20h, 20d). Optional second arg sets how many pulls/winners to show (default 5, max 20).")
    async def top_kakera(self, ctx: commands.Context, time_frame: str, count: int = 5):
        match = re.match(r"^(\d+)([mhd]?)$", time_frame.lower().strip())
        if not match:
            await ctx.send("Invalid time frame format. Please use a number followed by 'm', 'h', or 'd' (e.g., `20m`, `12h`, `5d`).")
            return

        amount_str, unit = match.groups()
        amount = int(amount_str)

        if amount <= 0:
            await ctx.send("Please specify a time frame greater than 0.")
            return

        if count <= 0:
            await ctx.send("Please specify a count greater than 0.")
            return

        if count > 20:
            await ctx.send("Maximum count is 20.")
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)

        if unit == 'm':
            delta = datetime.timedelta(minutes=amount)
            unit_name = "minutes"
            hours = amount / 60.0
        elif unit == 'd':
            delta = datetime.timedelta(days=amount)
            unit_name = "days"
            hours = amount * 24.0
        else:
            # Default to hours if 'h' or no unit is provided
            delta = datetime.timedelta(hours=amount)
            unit_name = "hours"
            hours = float(amount)

        since = now_utc - delta

        async with ctx.typing():
            embed, msg = await self._build_topk_embed(ctx.guild.id, since, hours, f"{amount} {unit_name}", limit=count)
            if embed:
                await ctx.send(embed=embed)
            else:
                await ctx.send(msg)

    async def _build_claims_embeds(self, guild_id: int, since: datetime.datetime, label: str):
        """Returns (list_of_embeds, fallback_message). Exactly one is non-None."""
        HARD_LIMIT = 200
        claims = await database.get_claims_chronological(guild_id, since, limit=HARD_LIMIT + 1)

        truncated = len(claims) > HARD_LIMIT
        if truncated:
            claims = claims[:HARD_LIMIT]

        if not claims:
            return None, f"No claims were logged in the last {label}."

        top3 = await database.get_top_claims_by_value(guild_id, since, limit=3)

        PAGE_SIZE = 20
        pages = [claims[i:i + PAGE_SIZE] for i in range(0, len(claims), PAGE_SIZE)]
        total_pages = len(pages)
        embeds = []

        for page_num, page in enumerate(pages, 1):
            lines = []
            for user_name, character_name, value, timestamp in page:
                try:
                    dt = datetime.datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%Y/%m/%d %H:%M")
                except Exception:
                    time_str = "??:??"
                lines.append(f"`{time_str}` **{user_name}**: {character_name} ({value:,})")

            footer_parts = [f"Page {page_num}/{total_pages}"]
            if truncated and page_num == total_pages:
                footer_parts.append(f"Showing first {HARD_LIMIT} claims only")

            embed = discord.Embed(
                title=f"Claims Log (Last {label})" if page_num == 1 else None,
                description="\n".join(lines),
                color=discord.Color.teal()
            )

            if page_num == 1:
                embed.add_field(name="Total Claims", value=f"**{len(claims):,}**", inline=False)
                if top3:
                    top3_lines = []
                    for u_name, c_name, val, ts in top3:
                        try:
                            dt = datetime.datetime.fromisoformat(ts)
                            ts_str = dt.strftime("%Y/%m/%d %H:%M")
                        except Exception:
                            ts_str = "??:??"
                        top3_lines.append(f"`{ts_str}` **{u_name}**: {c_name} ({val:,})")
                    embed.add_field(name="Top 3 Biggest Claims", value="\n".join(top3_lines), inline=False)

            embed.set_footer(text=" • ".join(footer_parts))
            embeds.append(embed)

        return embeds, None

    @commands.command(name="jews", help="Lists all claims in chronological order for a time frame (e.g. 20m, 20h, 20d).")
    async def claims_log(self, ctx: commands.Context, time_frame: str):
        match = re.match(r"^(\d+)([mhd]?)$", time_frame.lower().strip())
        if not match:
            await ctx.send("Invalid time frame format. Please use a number followed by 'm', 'h', or 'd' (e.g., `24h`, `7d`, `30m`).")
            return

        amount_str, unit = match.groups()
        amount = int(amount_str)

        if amount <= 0:
            await ctx.send("Please specify a time frame greater than 0.")
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)

        if unit == 'm':
            delta = datetime.timedelta(minutes=amount)
            unit_name = "minutes"
        elif unit == 'd':
            delta = datetime.timedelta(days=amount)
            unit_name = "days"
        else:
            delta = datetime.timedelta(hours=amount)
            unit_name = "hours"

        since = now_utc - delta

        async with ctx.typing():
            embeds, msg = await self._build_claims_embeds(ctx.guild.id, since, f"{amount} {unit_name}")
            if embeds:
                for embed in embeds:
                    await ctx.send(embed=embed)
            else:
                await ctx.send(msg)

    @commands.command(name="enablehuge", help="Enable hourly huge alerts in the tracking channel (owner only).")
    async def enable_topk(self, ctx: commands.Context):
        if ctx.author.id != self.owner_id:
            await ctx.send("lol")
            return
        await database.set_topk_alert_enabled(True)
        await ctx.send("Hourly huge alerts enabled. I gotchu.")

    @commands.command(name="disablehuge", help="Disable hourly huge alerts (owner only).")
    async def disable_topk(self, ctx: commands.Context):
        if ctx.author.id != self.owner_id:
            await ctx.send("lol")
            return
        await database.set_topk_alert_enabled(False)
        await ctx.send("Hourly huge alerts disabled.")

    @tasks.loop(time=[datetime.time(hour=h, minute=41, tzinfo=datetime.timezone.utc) for h in range(24)])
    async def hourly_topk_alert(self):
        if not await database.get_topk_alert_enabled():
            return
        if not self.tracking_channel_id:
            return

        channel = self.bot.get_channel(self.tracking_channel_id)
        if channel is None:
            logging.warning(f"Hourly topk alert: tracking channel {self.tracking_channel_id} not found.")
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        since = now_utc - datetime.timedelta(hours=1)
        embed, msg = await self._build_topk_embed(channel.guild.id, since, hours=1.0, label="1 hour")

        try:
            if embed:
                await channel.send(embed=embed)
            else:
                await channel.send(msg)
        except discord.DiscordException as e:
            logging.error(f"Failed to send hourly topk alert: {e}")

    @hourly_topk_alert.before_loop
    async def before_hourly_topk_alert(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
