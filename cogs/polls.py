import discord
from discord.ext import commands
import asyncio
from typing import List
import aiohttp
import json
import random


class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}
        self.strawpoll_api_key = "YOUR_STRAWPOLL_API_KEY"
        self.strawpoll_api_url = "https://api.strawpoll.com/v3/polls"
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    async def get_random_image(self):
        safe_categories = ['smile', 'wave', 'thumbsup', 'dance']
        category = random.choice(safe_categories)
        url = f"https://nekos.best/api/v2/{category}"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if 'results' in data and len(data['results']) > 0:
                    return data['results'][0].get('url')
        return 'https://example.com/default_image.png'

    @commands.group(invoke_without_command=True)
    async def poll(self, ctx, question: str, *options: str):
        """Create a poll with multiple options"""
        if len(options) > 10:
            await ctx.send("You can only have up to 10 options.")
            return

        if len(options) < 2:
            await ctx.send("You need at least 2 options.")
            return

        reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣',
                     '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

        description = []
        for x, option in enumerate(options):
            description.append(f'\n {reactions[x]} {option}')

        embed = discord.Embed(title=question, description=''.join(
            description), color=discord.Color.blue())
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")

        image_url = await self.get_random_image()
        if image_url:
            embed.set_thumbnail(url=image_url)

        react_message = await ctx.send(embed=embed)

        for reaction in reactions[:len(options)]:
            await react_message.add_reaction(reaction)

        self.active_polls[react_message.id] = {
            'question': question,
            'options': options,
            'reactions': reactions[:len(options)],
            'creator': ctx.author.id,
            'channel': ctx.channel.id
        }

        await ctx.message.delete()

    @poll.command(name="end")
    async def end_poll(self, ctx, message_id: int):
        """End a poll and display the results"""
        if message_id not in self.active_polls:
            await ctx.send("No active poll found with that ID.")
            return

        poll_data = self.active_polls[message_id]
        channel = self.bot.get_channel(poll_data['channel'])
        message = await channel.fetch_message(message_id)

        results = await self.tally_results(message, poll_data['reactions'])

        embed = discord.Embed(title=f"Poll Results: {
                              poll_data['question']}", color=discord.Color.green())

        for option, (reaction, count) in zip(poll_data['options'], results):
            embed.add_field(name=f"{reaction} {option}", value=f"{
                            count} votes", inline=False)

        image_url = await self.get_random_image()
        if image_url:
            embed.set_thumbnail(url=image_url)

        await ctx.send(embed=embed)
        del self.active_polls[message_id]

    @commands.command()
    async def quickpoll(self, ctx, *, question: str):
        """Create a quick yes/no poll"""
        embed = discord.Embed(title="Quick Poll",
                              description=question, color=discord.Color.blue())
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")

        image_url = await self.get_random_image()
        if image_url:
            embed.set_thumbnail(url=image_url)

        msg = await ctx.send(embed=embed)
        await msg.add_reaction('👍')
        await msg.add_reaction('👎')
        await ctx.message.delete()

    @commands.command()
    async def strawpoll(self, ctx, title: str, *options: str):
        """Create a strawpoll"""
        if len(options) < 2:
            await ctx.send("You need at least 2 options to create a poll.")
            return

        try:
            poll = await self.create_strawpoll(title, list(options))
            embed = discord.Embed(title="Strawpoll Created",
                                  color=discord.Color.green())
            embed.add_field(name="Title", value=title, inline=False)
            embed.add_field(name="URL", value=poll['url'], inline=False)

            image_url = await self.get_random_image()
            if image_url:
                embed.set_thumbnail(url=image_url)

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"There was an error creating the Strawpoll: {str(e)}")

    async def create_strawpoll(self, title: str, options: List[str]) -> dict:
        """Create a strawpoll using their API"""
        payload = {
            "title": title,
            "options": options,
            "multi": False
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.strawpoll_api_key
        }

        async with self.session.post(self.strawpoll_api_url, data=json.dumps(payload), headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "url": f"https://strawpoll.com/{data['id']}",
                    "admin_url": f"https://strawpoll.com/{data['id']}/results"
                }
            else:
                raise Exception(f"Strawpoll API Error: {response.status}")

    async def tally_results(self, message: discord.Message, reactions: List[str]) -> List[tuple]:
        """Tally the results of a poll"""
        results = []
        for reaction in reactions:
            reaction_count = discord.utils.get(
                message.reactions, emoji=reaction)
            count = reaction_count.count - 1 if reaction_count else 0
            results.append((reaction, count))
        return results

    @commands.command()
    async def schedule_poll(self, ctx, time: str, question: str, *options: str):
        """Schedule a poll to be posted at a specific time"""
        # This is a placeholder for the scheduling functionality
        # You would need to implement a proper scheduling system
        await ctx.send(f"Poll scheduled for {time}: {question}")

    @commands.command()
    async def poll_stats(self, ctx):
        """Display statistics about polls"""
        total_polls = len(self.active_polls)
        total_votes = sum(reaction.count - 1 for poll in self.active_polls.values()
                          for reaction in poll['reactions'])

        embed = discord.Embed(title="Poll Statistics",
                              color=discord.Color.blue())
        embed.add_field(name="Total Active Polls",
                        value=str(total_polls), inline=True)
        embed.add_field(name="Total Votes", value=str(
            total_votes), inline=True)

        image_url = await self.get_random_image()
        if image_url:
            embed.set_thumbnail(url=image_url)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(PollsCog(bot))
