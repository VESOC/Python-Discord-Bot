from discord import Intents
from discord import Embed, File
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import (
    CommandNotFound, BadArgument, MissingRequiredArgument, CommandOnCooldown)
from discord.ext.commands import Context, command
from discord.errors import HTTPException, Forbidden
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from glob import glob
from asyncio import sleep

from ..db import db

PREFIX = '>'
OWNER_IDS = [548015173156470784]
COGS = [path.split('/')[-1][:-3] for path in glob('./lib/cogs/*.py')]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)


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
        self.PREFIX = PREFIX
        self.guild = None
        self.cogs_ready = Ready()
        self.scheduler = AsyncIOScheduler()
        self.ready = False

        db.autosave(self.scheduler)

        # intents = Intents.default() # Intents.none()
        # intents.members = True

        super().__init__(
            command_prefix=PREFIX,
            owner_ids=OWNER_IDS,
            intents=Intents.all()
        )

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
            if self.ready:
                await self.invoke(ctx)
            else:
                await ctx.send("I'm not ready to receive commands. Please wait a few seconds.")

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
        raise

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
        else:
            print('Bot Reconnected')

    async def on_message(self, message):
        await self.process_commands(message)


bot = Bot()
