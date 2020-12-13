from discord import Member
from discord.ext.commands import Cog, Greedy
from discord.ext.commands import CheckFailure
from discord.ext.commands import command, has_permissions

from ..db import db


class Misc(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(name='prefix', brief='Change Bot Prefix')
    async def change_prefix(self, ctx, new: str):
        if ctx.author.id in self.bot.OWNERS:
            if len(new) > 5:
                await ctx.send('The prefix can not be more than 5 characters in length.')
            else:
                db.execute(
                    'UPDATE guilds SET Prefix = ? WHERE GuildID = ?', new, ctx.guild.id)
                await ctx.send(f'Prefix set to {new}')
        else:
            await ctx.send('You don\'t have permission to use this command.')

    @change_prefix.error
    async def change_prefix_error(self, ctx, exc):
        if isinstance(exc, CheckFailure):
            await ctx.send("You need the Manage Server permission to do that.")

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("misc")


def setup(bot):
    bot.add_cog(Misc(bot))
