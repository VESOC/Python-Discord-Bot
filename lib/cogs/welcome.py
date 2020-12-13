from discord import Forbidden
from discord.ext.commands import Cog
from discord.ext.commands import command

from ..db import db


class Welcome(Cog):
    def __init__(self, bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("welcome")

    @Cog.listener()
    async def on_member_join(self, member):
        db.execute('INSERT INTO exp (UserID) VALUES (?)', member.id)
        await self.bot.get_channel(787594810911359006).send(f'Welcome to **{member.guild.name}** {member.mention}! Head over to <784686063499083788> to say hi.')
        try:
            await member.send(f'Welcome to **{member.guild.name}**! Enjoy your stay!')
        except Forbidden:
            pass
        await member.add_roles(*(member.guild.get_role(id_) for id_ in (787596422165954593, 787596349122150420)))

        # await member.edit(roles=[*member.roles, *[member.guild.get_role(id_) for id_ in (787596422165954593, 787596349122150420)]])

    @Cog.listener()
    async def on_member_remove(self, member):
        db.execute('DELETE FROM exp WHERE UserID = ?', member.id)
        await self.bot.get_channel(787594810911359006).send(f'{member.display.name} has left {member.guild.name}')


def setup(bot):
    bot.add_cog(Welcome(bot))
