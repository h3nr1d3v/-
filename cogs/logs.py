import discord
from discord.ext import commands
import datetime
import asyncio


class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id =  # Replace with your log channel ID
        self.ignored_channels = set()  # Add channel IDs here to ignore
        self.message_cache = {}
        # Usar asyncio.create_task en lugar de self.bot.loop.create_task
        self.clear_cache_task = asyncio.create_task(self.clear_message_cache())

    async def get_log_channel(self):
        channel = self.bot.get_channel(self.log_channel_id)
        if not channel:
            print(
                f"Warning: Log channel with ID {self.log_channel_id} not found.")
        return channel

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.channel.id in self.ignored_channels:
            return

        channel = await self.get_log_channel()
        if not channel:
            return

        embed = discord.Embed(
            title="Message Deleted",
            description=f"In {message.channel.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="Content", value=message.content or "No content")
        embed.set_author(name=message.author.name,
                         icon_url=message.author.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()

        if message.attachments:
            embed.add_field(name="Attachments", value="\n".join(
                [a.url for a in message.attachments]))

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.channel.id in self.ignored_channels or before.content == after.content:
            return

        channel = await self.get_log_channel()
        if not channel:
            return

        embed = discord.Embed(
            title="Message Edited",
            description=f"In {before.channel.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Before", value=before.content or "No content", inline=False)
        embed.add_field(
            name="After", value=after.content or "No content", inline=False)
        embed.set_author(name=before.author.name,
                         icon_url=before.author.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = await self.get_log_channel()
        if not channel:
            return

        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} joined the server",
            color=discord.Color.green()
        )
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        embed.add_field(name="Account Created",
                        value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"))

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = await self.get_log_channel()
        if not channel:
            return

        embed = discord.Embed(
            title="Member Left",
            description=f"{member.mention} left the server",
            color=discord.Color.orange()
        )
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()
        embed.add_field(name="Joined At", value=member.joined_at.strftime(
            "%Y-%m-%d %H:%M:%S") if member.joined_at else "Unknown")

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self.log_role_changes(before, after)

    async def log_role_changes(self, before, after):
        channel = await self.get_log_channel()
        if not channel:
            return

        removed_roles = set(before.roles) - set(after.roles)
        added_roles = set(after.roles) - set(before.roles)

        if not (removed_roles or added_roles):
            return

        embed = discord.Embed(
            title="Member Roles Updated",
            description=f"Roles changed for {after.mention}",
            color=discord.Color.purple()
        )
        embed.set_author(name=after.name, icon_url=after.display_avatar.url)
        embed.timestamp = datetime.datetime.utcnow()

        if removed_roles:
            embed.add_field(name="Roles Removed", value=", ".join(
                [role.name for role in removed_roles]), inline=False)
        if added_roles:
            embed.add_field(name="Roles Added", value=", ".join(
                [role.name for role in added_roles]), inline=False)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        channel = await self.get_log_channel()
        if not channel:
            return

        if before.channel != after.channel:
            if after.channel:
                action = f"joined {after.channel.name}"
                color = discord.Color.green()
            elif before.channel:
                action = f"left {before.channel.name}"
                color = discord.Color.red()
            else:
                return

            embed = discord.Embed(
                title="Voice Channel Update",
                description=f"{member.mention} {action}",
                color=color
            )
            embed.set_author(name=member.name,
                             icon_url=member.display_avatar.url)
            embed.timestamp = datetime.datetime.utcnow()

            await channel.send(embed=embed)

    async def clear_message_cache(self):
        while True:
            await asyncio.sleep(3600)  # Clear cache every hour
            self.message_cache.clear()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ignore_channel(self, ctx, channel: discord.TextChannel):
        """Ignore a channel for logging"""
        self.ignored_channels.add(channel.id)
        await ctx.send(f"Now ignoring logs from {channel.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unignore_channel(self, ctx, channel: discord.TextChannel):
        """Unignore a channel for logging"""
        self.ignored_channels.discard(channel.id)
        await ctx.send(f"Now logging events from {channel.mention}")


async def setup(bot):
    await bot.add_cog(LogsCog(bot))
