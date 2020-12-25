from discord import Embed, Member, NotFound, Object
from discord.ext.commands import Cog, Greedy, Converter
from discord.ext.commands import CheckFailure, BadArgument
from discord.ext.commands import command, has_permissions, bot_has_permissions
from discord.utils import find
from better_profanity import profanity
from re import search
from typing import Optional
from datetime import datetime, timedelta
from asyncio import sleep

from ..db import db

profanity.load_censor_words_from_file('./data/profanity.txt')


class BannedUser(Converter):
    async def convert(self, ctx, arg):
        if ctx.guild.me.guild_permissions.ban_members:
            if arg.isdigit():
                try:
                    return (await ctx.guild.fetch_ban(Object(id=int(arg)))).user
                except NotFound:
                    raise BadArgument
            banned = [e.user for e in await ctx.guild.bans()]
            if banned:
                if (user := find(lambda u: str(u) == arg, banned)) is not None:
                    return user
                else:
                    raise BadArgument


class Mod(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        self.no_links = (786763641784762388,)
        self.no_images = (786763641784762388,)

    async def kick_members(self, message, targets, reason):
        for target in targets:
            if (message.guild.me.top_role.position > target.top_role.position and not target.guild_permissions.administrator):
                await target.kick(reason=reason)
                embed = Embed(title='Member kicked',
                              colour=0xDD2222, timestamp=datetime.utcnow())
                embed.set_thumbnail(url=target.avatar_url)
                fields = [
                    ('Member',
                        f'{target.name} a.k.a {target.display_name}', False),
                    ('Actioned by', message.author.display_name, False),
                    ('Reason', reason, False)
                ]
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                await self.bot.stdout.send(embed=embed)
            else:
                await message.send(f'{target.display_name} could not be kicked.')

    @command(name='kick')
    @bot_has_permissions(kick_members=True)
    @has_permissions(kick_members=True)
    async def kick_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = 'No reason provided.'):
        if not len(targets):
            await ctx.send('One or more required arguments are missing.')
        else:
            await self.kick_members(ctx.message, targets, reason)
            await ctx.send('Action Completed.')

    @kick_command.error
    async def kick_command_error(self, ctx, exc):
        if isinstance(exc, CheckFailure):
            await ctx.send('Insufficient permissions to perform that task.')

    async def ban_members(self, message, targets, reason):
        for target in targets:
            if (message.guild.me.top_role.position > target.top_role.position and not target.guild_permissions.administrator):
                await target.ban(reason=reason)
                embed = Embed(title='Member banned',
                              colour=0xDD2222, timestamp=datetime.utcnow())
                embed.set_thumbnail(url=target.avatar_url)
                fields = [
                    ('Member',
                        f'{target.name} a.k.a {target.display_name}', False),
                    ('Actioned by', message.author.display_name, False),
                    ('Reason', reason, False)
                ]
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                await self.bot.stdout.send(embed=embed)
            else:
                await message.send(f'{target.display_name} could not be banned.')

    @command(name='ban')
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    async def ban_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = 'No reason provided.'):
        if not len(targets):
            await ctx.send('One or more required arguments are missing.')
        else:
            await self.ban_members(ctx.message, targets, reason)
            await ctx.send('Action Completed.')

    @ban_command.error
    async def ban_command_error(self, ctx, exc):
        if isinstance(exc, CheckFailure):
            await ctx.send('Insufficient permissions to perform that task.')

    @command(name='unban')
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    async def unban_command(self, ctx, targets: Greedy[BannedUser], *, reason: Optional[str] = 'No reason provided.'):
        if not len(targets):
            await ctx.send('One or more required arguments are missing.')
        else:
            for target in targets:
                await ctx.guild.unban(target, reason=reason)

                embed = Embed(title="Member unbanned",
                              colour=0xDD2222, timestamp=datetime.utcnow())
                embed.set_thumbnail(url=target.avatar_url)
                fields = [("Member", target.name, False),
                          ("Actioned by", ctx.author.display_name, False),
                          ("Reason", reason, False)]
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                await self.bot.stdout.send(embed=embed)

            await ctx.send("Action complete.")

    @command(name='clear', aliases=['purge'])
    @bot_has_permissions(manage_messages=True)
    @has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, targets: Greedy[Member], limit: Optional[int] = 1):
        def _check(message):
            return not len(targets) or message.author in targets
        if 0 < limit <= 100:
            with ctx.channel.typing():
                await ctx.message.delete()
                deleted = await ctx.channel.purge(limit=limit, after=datetime.utcnow()-timedelta(days=14), check=_check)
                await ctx.send(f'{len(deleted):,} messages deleted.', delete_after=5)
        else:
            await ctx.send('The limit provided is not within acceptable bounds.')

    @clear_messages.error
    async def clear_messages_error(self, ctx, exc):
        if isinstance(exc, CheckFailure):
            await ctx.send('Insufficient permissions to perform that task.')

    async def mute_members(self, message, targets, hours, reason):
        unmutes = []

        for target in targets:
            if not self.mute_role in target.roles:
                if message.guild.me.top_role.position > target.top_role.position:
                    role_ids = ','.join([str(r.id) for r in target.roles])
                    end_time = datetime.utcnow() + timedelta(seconds=hours) if hours else None

                    db.execute('INSERT INTO mutes VALUES (?, ?, ?)', target.id, role_ids, getattr(
                        end_time, 'isoformat', lambda: None)())

                    await target.edit(roles=[self.mute_role])
                    embed = Embed(
                        title='Member Muted', colour=0xDD2222, timestamp=datetime.utcnow())
                    embed.set_thumbnail(url=target.avatar_url)
                    fields = [
                        ('Member', target.display_name, False),
                        ('Actioned by', message.author.display_name, False),
                        ('Duration',
                            f'{hours:,} hour(s)' if hours else 'Indefinite', False),
                        ('Reason', reason, False)
                    ]
                    for name, value, inline in fields:
                        embed.add_field(
                            name=name, value=value, inline=inline)
                    await self.bot.stdout.send(embed=embed)

                    if hours:
                        unmutes.append(target)
        return unmutes

    @command(name='mute')
    @bot_has_permissions(manage_roles=True)
    @has_permissions(manage_roles=True, manage_guild=True)
    async def mute_command(self, ctx, targets: Greedy[Member], hours: Optional[int], *, reason: Optional[str] = 'No reason provided'):
        if not len(targets):
            await ctx.send('One or more required arguments are missing.')
        else:
            unmutes = await self.mute_members(ctx.message, targets, hours, reason)
            await ctx.send('Action Complete')

            if len(unmutes):
                await sleep(hours*3600)
                await self.unmute_members(ctx, targets)

    @mute_command.error
    async def mute_command_error(self, ctx, exc):
        if isinstance(exc, CheckFailure):
            await ctx.send('Insufficient permissions to perform that task.')

    async def unmute_members(self, ctx, targets, *, reason='Mute time expired'):
        for target in targets:
            if self.mute_role in target.roles:
                role_ids = db.field(
                    'SELECT RoleIDs FROM mutes WHERE UserID = ?', target.id)
                roles = [ctx.guild.get_role(int(id_))
                         for id_ in role_ids.split(',') if len(id_)]
                db.execute('DELETE FROM mutes WHERE UserID = ?', target.id)
                await target.edit(roles=roles)
                embed = Embed(title='Member Unmuted',
                              colour=0xDD2222, timestamp=datetime.utcnow())
                embed.set_thumbnail(url=target.avatar_url)
                fields = [
                    ('Member', target.display_name, False),
                    ('Actioned by', ctx.author.display_name, False),
                    ('Reason', reason, False)
                ]
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                await self.bot.stdout.send(embed=embed)

    @command(name='unmute')
    @bot_has_permissions(manage_roles=True)
    @has_permissions(manage_roles=True, manage_guild=True)
    async def unmute_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = 'No reason provided.'):
        if not len(targets):
            await ctx.send('One or more required arguments is missing')
        else:
            await self.unmute_members(ctx, targets, reason=reason)

    @command(name='addprofanity', aliases=['addcurse'])
    @has_permissions(manage_guild=True)
    async def add_profanity(self, ctx, *words):
        with open('./data/profanity.txt', 'a', encoding='utf-8') as pf:
            pf.write(''.join([f'{w}\n' for w in words]))
        profanity.load_censor_words_from_file('./data/profanity.txt')
        await ctx.send('Action Complete')

    @command(name='removeprofanity', aliases=['delswear'])
    @has_permissions(manage_guild=True)
    async def remove_profanity(self, ctx, *words):
        with open('./data/profanity.txt', 'r', encoding='utf-8') as pf:
            stored = [w.strip() for w in pf.readlines()]
        with open('./data/profanity.txt', 'w', encoding='utf-8') as pf:
            pf.write(
                ''.join([f'{w.strip()}\n' for w in stored if w not in words]))
        profanity.load_censor_words_from_file('./data/profanity.txt')
        await ctx.send('Action Complete')

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('mod')
            self.mute_role = self.bot.guild.get_role(786407510353510432)

    @Cog.listener()
    async def on_message(self, message):
        def _check(m):
            return (m.author == message.author and len(m.mentions) and (datetime.utcnow()-m.created_at).seconds < 60)
        if not message.author.bot:
            if len(list(filter(lambda m: _check(m), self.bot.cached_messages))) >= 3:
                await message.channel.send('Don\'t span mentions!', delete_after=10)
                unmutes = await self.mute_members(message, [message.author], 5, reason='Mention Spam')

                if len(unmutes):
                    await sleep(300)
                    await self.unmute_members(message.guild, [message.author])
        elif profanity.contains_profanity(message.content):
            await message.delete()
            await message.channel.send('You can\'t use that word here.', delete_after=10)
        elif message.channel.id in self.no_links and search(self.url_regex, message.content):
            await message.delete()
            await message.channel.send('You can\'t send links in this channel', delete_after=10)
        elif message.channel.id in self.no_images and any([hasattr(a, 'width') for a in message.attachments]):
            await message.delete()
            await message.channel.send('You can\'t send images in this channel.', delete_after=10)


def setup(bot):
    bot.add_cog(Mod(bot))
