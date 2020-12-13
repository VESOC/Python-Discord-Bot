from discord.ext.commands import Cog, BucketType
from discord.ext.commands import command, cooldown
from discord.ext.commands import BadArgument, CommandOnCooldown
from discord.errors import HTTPException
from discord import Member, Embed
import discord
from typing import Optional
from random import choice, randint
from aiohttp import request
from urllib.request import urlopen, Request
import urllib
import urllib.request
import bs4
import random
import json
import os
import sys


class Fun(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(name='hello', aliases=['hi'], hidden=True, brief='Says hello to the user')
    async def say_hello(self, ctx):
        '''Says hello to the user'''
        await ctx.send(f"{choice(['Hello', 'Hi', 'How are you'])} {ctx.author.mention}")
        # await ctx.author.send(f'You invoked hello from {ctx.guild} {ctx.channel}')

    @command(name='dice', aliases=['roll'], brief='Returns random number between the two arguments.')
    @cooldown(1, 60, BucketType.user)
    async def roll_dice(self, ctx, minimum: Optional[int] = 1, maximum: Optional[int] = 6):
        '''Returns random number between the two arguments.'''
        value = randint(minimum, maximum)
        await ctx.send(f'Result: {value}')

    @roll_dice.error
    async def roll_dice_error(self, ctx, exc):
        if hasattr(exc, 'original'):
            if isinstance(exc.original, HTTPException):
                await ctx.send('Number too large. Try a lower number.')
            elif isinstance(exc.original, ValueError):
                await ctx.send('Please specify both min and max values.')
        else:
            await ctx.send('Unknown Error check error channel.')

    @command(name='slap', aliases=['hit'], brief='Slaps the mentioned user.')
    async def slap_member(self, ctx, member: Member, *, reason: Optional[str] = 'no reason'):
        '''Slaps the mentioned user.'''
        await ctx.send(f'{ctx.author.display_name} slapped {member.mention} for {reason}!')

    @slap_member.error
    async def slap_member_error(self, ctx, exc):
        if isinstance(exc, BadArgument):
            await ctx.send('That member does not exist.')

    @command(name='echo', aliases=['say'], brief='Deletes command message and repeats the given argument.')
    @cooldown(3, 60, BucketType.guild)
    async def echo_message(self, ctx, value: Optional[int] = 10, *, message):
        '''Deletes command message and repeats the given argument.'''
        await ctx.message.delete()
        for _ in range(value):
            await ctx.send(message)

    @command(name='clear', aliases=['c'], brief='Deletes command message and <number> amount of preceeding messages.')
    async def clear_chat(self, ctx, number: int = 1):
        '''Deletes command message and <number> amount of preceeding messages.'''
        await ctx.channel.purge(limit=number+1)

    @command(name='fact', brief='Sends an Embed with a random fact and picture about the animal.')
    @cooldown(3, 60, BucketType.guild)
    async def animal_fact(self, ctx, animal: str = 'dog'):
        '''Sends an Embed with a random fact and picture about the animal.'''
        if (animal := animal.lower()) in ('dog', 'cat', 'panda', 'fox', 'bird', 'koala'):
            FACT_URL = f'https://some-random-api.ml/facts/{animal}'
            IMAGE_URL = f'https://some-random-api.ml/img/{"birb" if animal == "bird" else animal}'
            async with request('GET', IMAGE_URL, headers={}) as response:
                if response.status == 200:
                    data = await response.json()
                    image_url = data['link']
                else:
                    image_url = None
                    ctx.send(f'Image API returned a {response.status} status')
            async with request('GET', FACT_URL, headers={}) as response:
                if response.status == 200:
                    data = await response.json()
                    embed = Embed(title=f'{animal.title()} Fact',
                                  description=data['fact'],
                                  colour=ctx.author.colour)
                    if image_url is not None:
                        embed.set_image(url=image_url)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f'Fact API returned a {response.status} status.')
        else:
            await ctx.send('No facts available for that animal.')

    @command(name='이미지검색', aliases=['image'], brief='Finds image from naver and returns it as an Embed')
    @cooldown(3, 30, BucketType.guild)
    async def search_image(self, ctx, *, Text):
        '''Finds image from naver and returns it as an Embed'''
        randomNum = random.randrange(0, 40)
        location = Text
        enc_location = urllib.parse.quote(location)
        hdr = {'User-Agent': 'Mozilla/5.0'}
        url = 'https://search.naver.com/search.naver?where=image&sm=tab_jum&query=' + enc_location
        req = Request(url, headers=hdr)
        html = urllib.request.urlopen(req)
        bsObj = bs4.BeautifulSoup(html, "html.parser")

        imgfind1 = bsObj.find('div', {'class': 'photo_grid _box'})
        imgfind2 = imgfind1.findAll('a', {'class': 'thumb _thumb'})
        imgfind3 = imgfind2[randomNum]
        imgfind4 = imgfind3.find('img')
        imglink = imgfind4.get('data-source')

        embed = Embed(
            colour=discord.Colour.green()
        )

        embed.add_field(name='검색 : '+Text, value="출처 : 네이버 이미지", inline=False)
        embed.set_image(url=imglink)

        await ctx.send(embed=embed)

    @search_image.error
    async def search_image_error(self, ctx, exc):
        await self.bot.stdout.send(exc)

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up('fun')
        await self.bot.stdout.send('Fun cog ready')


def setup(bot):
    bot.add_cog(Fun(bot))
    # bot.scheduler.add_job()
