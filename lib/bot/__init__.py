from discord import Intents
from discord import Embed, File, DMChannel
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import (
    CommandNotFound, BadArgument, MissingRequiredArgument, CommandOnCooldown)
from discord.ext.commands import Context, command
from discord.ext.commands import when_mentioned_or
from discord.errors import HTTPException, Forbidden
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from glob import glob
from asyncio import sleep

from ..db import db

OWNER_IDS = [548015173156470784]
COGS = [path.split('/')[-1][:-3] for path in glob('./lib/cogs/*.py')]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)


def get_prefix(bot, message):
    try:
        prefix = db.field(
            "SELECT Prefix FROM guilds WHERE GuildID = ?", message.guild.id)
    except:
        prefix = '>'
    return when_mentioned_or(prefix)(bot, message)


class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f'{cog} cog ready')

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class Bot(BotBase):
    def __init__(self):
        self.guild = None
        self.cogs_ready = Ready()
        self.scheduler = AsyncIOScheduler()
        self.ready = False
        self.OWNERS = OWNER_IDS

        try:
            with open('./data/banlist.txt', 'r', encoding='utf-8') as f:
                self.banlist = [int(line.strip()) for line in f.readlines()]
        except FileNotFoundError:
            self.banlist = []

        db.autosave(self.scheduler)

        # intents = Intents.default() # Intents.none()
        # intents.members = True

        super().__init__(
            command_prefix=get_prefix,
            owner_ids=self.OWNERS,
            intents=Intents.all()
        )

    def update_db(self):
        db.multiexec('INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)',
                     ((guild.id,) for guild in self.guilds))
        db.multiexec('INSERT OR IGNORE INTO exp (UserID) values (?)',  ((
            member.id,) for member in self.guild.members if not member.bot))  # for guild in self.guilds for member in guild.members
        stored_members = db.column('SELECT UserID FROM exp')
        to_remove = []
        for id_ in stored_members:
            if not self.guild.get_member(id_):
                to_remove.append(id_)
        db.multiexec('DELETE FROM exp WHERE UserID = ?',
                     ((id_ for if_ in to_remove)))
        db.commit()

    def setup(self):
        for cog in COGS:
            self.load_extension(f'lib.cogs.{cog}')
            print(f'{cog} cog loaded')

        print('Setup Complete')

    def run(self, version):
        self.VERSION = version
        print('Running setup...')
        self.setup()
        with open('./lib/bot/token.0', 'r', encoding='utf-8') as tf:
            self.TOKEN = tf.read()
        print('Running bot...')
        super().run(self.TOKEN, reconnect=True)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)
        if ctx.command is not None and ctx.guild is not None:
            if message.author.id in self.banlist:
                await ctx.send('You are banned from using commands.')
            elif not self.ready:
                await ctx.send("I'm not ready to receive commands. Please wait a few seconds.")
            else:
                await self.invoke(ctx)

    async def on_connect(self):
        print('Bot Connected')

    async def on_disconnect(self):
        print('Bot disconnected')

    async def reminder(self):
        await self.stdout.send('Add rules to this string')

    async def on_error(self, err, *args, **kwargs):
        if err == 'on_command_err':
            await args[0].send('Something went wrong')

        await self.stdout.send('On error ' + str(err))
        raise err

    async def on_command_error(self, ctx, exc):
        if any(isinstance(exc, error) for error in IGNORE_EXCEPTIONS):
            await ctx.send('That is not a valid command')
            await ctx.delete()

        elif isinstance(exc, MissingRequiredArgument):
            await ctx.send('One or more required arguments are missing')

        elif isinstance(exc, CommandOnCooldown):
            await ctx.send(f'That command is on {str(exc.cooldown.type).split(".")[-1]} cooldown. Try again in {exc.retry_after:,.2f} seconds.')

        elif hasattr(exc, 'original'):
            await self.stdout.send(exc.original)
            if isinstance(exc.original, HTTPException):
                await ctx.send('HTTPException Occured.')

            elif isinstance(exc.original, Forbidden):
                await ctx.send('No permission.')

            else:
                raise exc.original

        else:
            await self.stdout.send(exc)
            raise exc

    async def on_ready(self):
        if not self.ready:
            self.guild = self.get_guild(784686063499083786)
            self.stdout = self.get_channel(786763641784762388)
            self.scheduler.add_job(
                self.reminder, CronTrigger(hour="8", minute="0", second="0"))
            self.scheduler.start()
            self.update_db()

            # channel = self.get_channel(786025577516761089)
            # await channel.send('테스트봇 온라인')

            # embed = Embed(title='Now Online!',
            #               description='TestBot is online!', colour=0x1f8eee, timestamp=datetime.utcnow())
            # fields = [
            #     ('name', 'value', True),
            #     ('else', 'why', True),
            #     ('non-inline', 'own line', False)
            # ]
            # for name, value, inline in fields:
            #     embed.add_field(name=name,  value=value, inline=inline)
            # embed.add_field(name='Some name', value='Some value', inline=True)
            # embed.set_thumbnail(url=self.guild.icon_url)
            # embed.set_image(url=self.guild.icon_url)
            # embed.set_author(name='Bot', icon_url=self.guild.icon_url)
            # embed.set_footer(text='Some footer text')
            # await channel.send(embed=embed)

            # await channel.send(file=File('./data/images/thunderstorm.png'))

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True
            print('Bot Ready')
            meta = self.get_cog('Meta')
            await meta.set()
        else:
            print('Bot Reconnected')

    async def on_message(self, message):
        if not message.author.bot:
            if isinstance(message.channel, DMChannel):
                member = self.guild.get_member(message.author.id)
                embed = Embed(title='Modmail',
                              colour=member.colour, timestamp=datetime.utcnow())
                embed.set_thumbnail(url=member.avatar_url)
                fields = [
                    ('Member', f'{member.display_name}', False),
                    ('Message', message.content, False)
                ]
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)
                await self.stdout.send(embed=embed)
                await message.channel.send('Message relayed to moderators.')
            await self.process_commands(message)


bot = Bot()
