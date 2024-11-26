import discord
from discord.ext import commands
import aiohttp
import asyncio
from typing import Optional


class Anime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    async def fetch_image(self, ctx, endpoint: str):
        """Fetch an image from the Nekos Best API"""
        url = f"https://nekos.best/api/v2/{endpoint}"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                image_url = data["results"][0]["url"]
                embed = discord.Embed(color=discord.Color.random())
                embed.set_image(url=image_url)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Failed to fetch {endpoint} image. Please try again later.")

    @commands.command()
    @commands.is_nsfw()
    async def waifu(self, ctx):
        """Fetch a random waifu image"""
        await self.fetch_image(ctx, "waifu")

    @commands.command()
    async def neko(self, ctx):
        """Fetch a random neko image"""
        await self.fetch_image(ctx, "neko")

    @commands.command()
    @commands.is_nsfw()
    async def kitsune(self, ctx):
        """Fetch a random kitsune image"""
        await self.fetch_image(ctx, "kitsune")

    @commands.command()
    async def husbando(self, ctx):
        """Fetch a random husbando image"""
        await self.fetch_image(ctx, "husbando")

    @commands.command()
    async def anime_quote(self, ctx):
        """Fetch a random anime quote"""
        url = "https://animechan.vercel.app/api/random"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                embed = discord.Embed(
                    title="Anime Quote", color=discord.Color.blue())
                embed.add_field(
                    name="Anime", value=data["anime"], inline=False)
                embed.add_field(name="Character",
                                value=data["character"], inline=False)
                embed.add_field(
                    name="Quote", value=data["quote"], inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to fetch anime quote. Please try again later.")

    @commands.command()
    async def anime(self, ctx, *, anime_name: str):
        """Fetch information about an anime using Jikan API"""
        url = f"https://api.jikan.moe/v4/anime?q={anime_name}&limit=1"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data['data']:
                    anime = data['data'][0]
                    title = anime.get('title', 'Unknown Title')
                    synopsis = anime.get('synopsis', 'No synopsis available.')
                    image_url = anime.get('images', {}).get(
                        'jpg', {}).get('large_image_url', '')
                    score = anime.get('score', 'N/A')
                    episodes = anime.get('episodes', 'Unknown')
                    status = anime.get('status', 'Unknown')

                    embed = discord.Embed(
                        title=title, description=synopsis, color=discord.Color.purple())
                    if image_url:
                        embed.set_thumbnail(url=image_url)
                    embed.add_field(name="Score", value=score, inline=True)
                    embed.add_field(name="Episodes",
                                    value=episodes, inline=True)
                    embed.add_field(name="Status", value=status, inline=True)

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("No anime found with that name.")
            else:
                await ctx.send("Failed to fetch anime information. Please try again later.")

    @commands.command()
    async def manga(self, ctx, *, manga_name: str):
        """Fetch information about a manga using Jikan API"""
        url = f"https://api.jikan.moe/v4/manga?q={manga_name}&limit=1"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data['data']:
                    manga = data['data'][0]
                    title = manga.get('title', 'Unknown Title')
                    synopsis = manga.get('synopsis', 'No synopsis available.')
                    image_url = manga.get('images', {}).get(
                        'jpg', {}).get('large_image_url', '')
                    score = manga.get('score', 'N/A')
                    volumes = manga.get('volumes', 'Unknown')
                    chapters = manga.get('chapters', 'Unknown')
                    status = manga.get('status', 'Unknown')

                    embed = discord.Embed(
                        title=title, description=synopsis, color=discord.Color.green())
                    if image_url:
                        embed.set_thumbnail(url=image_url)
                    embed.add_field(name="Score", value=score, inline=True)
                    embed.add_field(name="Volumes", value=volumes, inline=True)
                    embed.add_field(name="Chapters",
                                    value=chapters, inline=True)
                    embed.add_field(name="Status", value=status, inline=True)

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("No manga found with that name.")
            else:
                await ctx.send("Failed to fetch manga information. Please try again later.")


async def setup(bot):
    await bot.add_cog(AnimeCog(bot))
