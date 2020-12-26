from discord.ext.commands import Cog
from discord.ext.commands import command, has_permissions
from discord import Embed
from datetime import datetime, timedelta
from random import choice
from ..db import db

numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


class Reactions(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.polls = []
        self.giveaways = []

    @command(name='createpoll', aliases=['poll'])
    @has_permissions(manage_guild=True)
    async def create_poll(self, ctx, hours: int, question: str, *options):
        if len(options) > 10:
            await ctx.send('You can only supply a maximum of 10 options.')
        else:
            embed = Embed(title='Poll', description=question,
                          colour=ctx.author.colour, timestamp=datetime.utcnow())
            fields = [
                ('Options', '\n'.join(
                    f'{numbers[idx]} {op}' for idx, op in enumerate(options)), False),
                ('Instructions', 'React to cast a vote!', False)
            ]
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
            message = await ctx.send(embed=embed)

            for emoji in numbers[:len(options)]:
                await message.add_reaction(emoji)
            self.polls.append((message.channel.id, message.id))
            self.bot.scheduler.add_job(self.complete_poll, 'date', run_date=datetime.now(
            )+timedelta(seconds=hours*3600), args=[message.channel.id, message.id])

    async def complete_poll(self, channel_id, message_id):
        message = await self.bot.get_channel(channel_id).fetch_message(message_id)
        most_voted = max(message.reactions, key=lambda r: r.count)
        await message.channel.send(f'The results are in and option {most_voted.emoji} was the most popular with {most_voted.count-1}')
        self.polls.remove((message.channel.id, message.id))

    @command(name='giveaway')
    @has_permissions(manage_guild=True)
    async def create_giveaway(self, ctx, mins: int, *, description: str):
        embed = Embed(title='Giveaway', description=description,
                      colour=ctx.author.colour, timestamp=datetime.utcnow())
        fields = [
            ('End Time',
             f'{datetime.utcnow()+timedelta(seconds=mins*60)} UTC', False)
        ]
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
        message = await ctx.send(embed=embed)
        await message.add_reaction('✅')
        self.giveaways.append((message.channel.id, message.id))
        self.bot.scheduler.add_job(self.complete_giveaway, 'date', run_date=datetime.now(
        )+timedelta(seconds=mins*60), args=[message.channel.id, message.id])

    async def complete_giveaway(self, channel_id, message_id):
        message = await self.bot.get_channel(channel_id).fetch_message(message_id)
        if len((entrants := [u for u in await message.reactions[0].users().flatten() if not u.bot])) > 0:
            winner = choice(entrants)
            await message.channel.send(f'Congratulations {winner.mention} - you won the giveaway!')
        else:
            await message.channel.send('Giveaway ended - no one entered!')
        self.giveaways.remove((message.channel.id, message.id))

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.colours = {
                '🔴': self.bot.guild.get_role(787596422165954593),
                '🟡': self.bot.guild.get_role(787596349122150420),
                '🟢': self.bot.guild.get_role(790392198759579688),
                '🔵': self.bot.guild.get_role(790392229985255456),
                '🟣': self.bot.guild.get_role(790392269218906122),
                '⚫': self.bot.guild.get_role(790392322822373376)
            }
            self.reaction_message = await self.bot.get_channel(786025577516761089).fetch_message(790390195848740864)
            self.bot.cogs_ready.ready_up('reactions')

    # @Cog.listener()
    # async def on_reaction_add(self, reaction, user):
    #     print(f'{user.display_name} reacted with {reaction.emoji.name}')

    # @Cog.listener()
    # async def on_reaction_remove(self, reaction, user):
    #     print(f'{user.display_name} removed reaction of {reaction.emoji.name}')

    @Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.bot.ready and payload.message_id == self.reaction_message.id:
            current_colours = filter(
                lambda r: r in self.colours.values(), payload.member.roles)
            await payload.member.remove_roles(*current_colours, reason='Colour role reaction', atomic=False)
            await payload.member.add_roles(self.colours[payload.emoji.name], reason='Colour role reaction')
            await self.reaction_message.remove_reaction(payload.emoji, payload.member)
        elif payload.message_id in (poll[1] for poll in self.polls):
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            for reaction in message.reactions:
                if not payload.member.bot and payload.member in await reaction.users().flatten() and reaction.emoji != payload.emoji.name:
                    await message.remove_reaction(reaction.emoji, payload.member)
        elif payload.emoji.name == '⭐':
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            if not message.author.bot and payload.member.id != message.author.id:
                msg_id, stars = db.record(
                    'SELECT StarMessageID, Stars FROM starboard WHERE RootMessageID = ?',  message.id) or (None, 0)
                embed = Embed(
                    title='Starred Message', colour=message.author.colour, timestamp=datetime.utcnow())
                fields = [
                    ('Author', message.author.mention, False),
                    ('Content', message.content or 'See attachment', False),
                    ('Stars', stars+1, False)
                ]
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                if len(message.attachments):
                    embed.set_image(url=message.attachments[0].url)
                if not stars:
                    star_message = await self.bot.stdout.send(embed=embed)
                    db.execute('INSERT INTO starboard (RootMessageID, StarMessageId) VALUES (?, ?)',
                               message.id, star_message.id)
                else:
                    star_message = await self.bot.stdout.fetch_message(msg_id)
                    await star_message.edit(embed=embed)
                    db.execute(
                        'UPDATE starboard SET Stars = Stars + 1 WHERE RootMessageID = ?', message.id)
            else:
                await message.remove_reaction(payload.emoji, payload.member)

    # @Cog.listener()
    # async def on_raw_reaction_remove(self, payload):
    #     member = self.bot.guild.get_member(payload.user_id)
    #     if self.bot.ready and payload.message_id == self.reaction_message.id:
    #         await member.remove_roles(self.colours[payload.emoji.name], reason='Colour role reaction')


def setup(bot):
    bot.add_cog(Reactions(bot))
