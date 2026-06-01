import discord
from discord.ext import commands

import os

LAST_UPDATED = "2026/06/01 UTC"

class BasicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.owner_id = int(os.getenv("OWNER_ID", 0))

    @commands.command(name="ping", help="Health check for the bot and returns latency.")
    async def ping(self, ctx: commands.Context):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"I am the bone of my sword. (Latency: {latency}ms)\nBtw last updated {LAST_UPDATED}")

    @commands.command(name="echo", help="Repeats the message back to you.")
    async def echo(self, ctx: commands.Context, *, message: str):
        await ctx.send(message)

    @commands.command(name="enablesnipe", help="Enable snipe for a user.")
    async def enablesnipe(self, ctx: commands.Context, user: discord.Member):
        if ctx.author.id != self.owner_id:
            await ctx.send("lol")
            return
        await ctx.send(f"Wishlist and Kakera snipe has been enabled for {user.mention}. I gotchu.")

    @commands.command(name="disablesnipe", help="Disable snipe for a user.")
    async def disablesnipe(self, ctx: commands.Context, user: discord.Member):
        if ctx.author.id != self.owner_id:
            await ctx.send("lol")
            return
        await ctx.send(f"Wishlist and Kakera snipe has been disabled for {user.mention}. I gotchu.")

    @enablesnipe.error
    @disablesnipe.error
    async def snipe_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.send("Could not find that user! Who is Bro?")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Bro thought!")

async def setup(bot: commands.Bot):
    await bot.add_cog(BasicCog(bot))
