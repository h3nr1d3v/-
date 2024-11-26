import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import io
from collections import Counter
from datetime import datetime, timedelta


class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def member_growth(self, ctx, days: int = 30):
        """Show member growth over the specified number of days"""
        guild = ctx.guild
        today = datetime.utcnow()
        dates = [(today - timedelta(days=i)).date() for i in range(days)]
        member_counts = []

        for date in dates:
            count = sum(
                1 for member in guild.members if member.joined_at.date() <= date)
            member_counts.append(count)

        plt.figure(figsize=(10, 6))
        plt.plot(dates, member_counts)
        plt.title(f"Member Growth over {days} days")
        plt.xlabel("Date")
        plt.ylabel("Number of Members")
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, 'member_growth.png'))

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def activity_heatmap(self, ctx, channel: discord.TextChannel = None):
        """Show activity heatmap for the specified channel"""
        channel = channel or ctx.channel
        messages = await channel.history(limit=1000).flatten()

        hour_counts = Counter([msg.created_at.hour for msg in messages])
        hours = list(range(24))
        counts = [hour_counts[hour] for hour in hours]

        plt.figure(figsize=(12, 6))
        plt.bar(hours, counts)
        plt.title(f"Activity Heatmap for #{channel.name}")
        plt.xlabel("Hour of Day (UTC)")
        plt.ylabel("Number of Messages")
        plt.xticks(hours)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        await ctx.send(file=discord.File(buf, 'activity_heatmap.png'))

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def top_users(self, ctx, limit: int = 10):
        """Show top users by message count"""
        guild = ctx.guild
        user_messages = Counter()

        for channel in guild.text_channels:
            try:
                async for message in channel.history(limit=None):
                    if not message.author.bot:
                        user_messages[message.author] += 1
            except discord.errors.Forbidden:
                continue

        top_users = user_messages.most_common(limit)

        embed = discord.Embed(
            title=f"Top {limit} Users by Message Count", color=discord.Color.gold())
        for i, (user, count) in enumerate(top_users, 1):
            embed.add_field(name=f"{i}. {user.name}", value=f"{
                            count} messages", inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AnalyticsCog(bot))
