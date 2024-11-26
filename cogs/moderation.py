import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import aiohttp
import random
import logging
from typing import Optional, Union, List, Dict
import re
from collections import defaultdict

WELCOME_CHANNEL_ID =  # ID channels here
LEFT_CHANNEL_ID =  # ID channels here
BANNED_CHANNEL_ID =  # ID channels here
UNBANNED_CHANNEL_ID =  # ID channels here
WARNINGS_CHANNEL_ID =  # ID channels here

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoModConfig:
    def __init__(self):
        self.spam_threshold = 5
        self.spam_interval = 5
        self.raid_threshold = 10
        self.raid_interval = 30
        self.max_mentions = 5
        self.max_links = 3
        self.mute_duration = 5  # minutes
        self.warn_expire_days = 30
        self.max_warnings = 3
        self.auto_ban_threshold = 5


class Moderation(commands.Cog):
    """Advanced server moderation and auto-moderation system.

    Features:
    - Warning system with auto-punishment
    - Spam detection and prevention
    - Content filtering
    - User notes and tracking
    - Automated moderation actions
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = AutoModConfig()
        self.warnings = defaultdict(list)
        self.spam_control = defaultdict(list)
        self.raid_detection = set()
        self.session = None
        self.muted_roles = {}
        self.temp_bans = {}
        self.auto_mod_enabled = True
        self.filtered_words = set()
        self.user_notes = defaultdict(list)

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        # Initialize data files if they don't exist
        self.initialize_data_files()
        self.load_data()

    async def cog_load(self):
        """Initialize the cog and create necessary directories."""
        self.session = aiohttp.ClientSession()
        os.makedirs('data', exist_ok=True)
        await self.setup_muted_roles()
        logger.info("ModerationCog loaded successfully")

    async def cog_unload(self):
        """Cleanup when cog is unloaded."""
        if self.session:
            await self.session.close()
        self.save_data()
        logger.info("ModerationCog unloaded successfully")

    def load_data(self):
        """Load all moderation data from files."""
        try:
            if os.path.exists('data/warnings.json'):
                with open('data/warnings.json', 'r') as f:
                    self.warnings = defaultdict(list, json.load(f))

            if os.path.exists('data/filtered_words.json'):
                with open('data/filtered_words.json', 'r') as f:
                    self.filtered_words = set(json.load(f))

            if os.path.exists('data/user_notes.json'):
                with open('data/user_notes.json', 'r') as f:
                    self.user_notes = defaultdict(list, json.load(f))
        except Exception as e:
            logger.error(f"Error loading moderation data: {e}")

    def save_data(self):
        """Save all moderation data to files."""
        try:
            with open('data/warnings.json', 'w') as f:
                json.dump(dict(self.warnings), f, indent=4)

            with open('data/filtered_words.json', 'w') as f:
                json.dump(list(self.filtered_words), f, indent=4)

            with open('data/user_notes.json', 'w') as f:
                json.dump(dict(self.user_notes), f, indent=4)
        except Exception as e:
            logger.error(f"Error saving moderation data: {e}")

    async def setup_muted_roles(self):
        """Create or get muted roles for all guilds."""
        for guild in self.bot.guilds:
            role = discord.utils.get(guild.roles, name="Muted")
            if not role:
                try:
                    role = await guild.create_role(
                        name="Muted",
                        reason="Auto-moderation muted role"
                    )
                    for channel in guild.channels:
                        await channel.set_permissions(role, send_messages=False)
                except discord.Forbidden:
                    logger.error(f"Cannot create muted role in {guild.name}")
            self.muted_roles[guild.id] = role

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx, setting: str = None, value: str = None):
        """Configure auto-moderation settings.

        View or modify auto-moderation parameters like spam thresholds,
        maximum warnings, and punishment durations.

        Parameters:
        -----------
        setting: str
            The setting to modify (optional)
        value: str
            The new value for the setting (optional)

        Examples:
        --------
        !automod
        !automod spam_threshold 5
        !automod mute_duration 10
        """
        if not setting:
            # Display current settings
            embed = discord.Embed(
                title="Auto-Moderation Settings",
                color=discord.Color.blue()
            )
            for attr, value in vars(self.config).items():
                embed.add_field(name=attr, value=str(value))
            return await ctx.send(embed=embed)

        try:
            if hasattr(self.config, setting):
                setattr(self.config, setting, int(value))
                await ctx.send(f"Updated {setting} to {value}")
            else:
                await ctx.send("Invalid setting")
        except ValueError:
            await ctx.send("Invalid value")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str):
        """Warn a member for rule violations.

        Issues a formal warning to a member and logs it. Multiple warnings
        may result in automatic punishments.

        Parameters:
        -----------
        member: discord.Member
            The member to warn
        reason: str
            The reason for the warning

        Examples:
        --------
        !warn @user Spamming in chat
        !warn @user Inappropriate language
        """
        if member.top_role >= ctx.author.top_role:
            return await ctx.send("You cannot warn members with higher or equal roles.")

        warning = {
            "reason": reason,
            "moderator": ctx.author.id,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.warnings[str(member.id)].append(warning)
        warning_count = len(self.warnings[str(member.id)])

        embed = discord.Embed(
            title="Member Warned",
            color=discord.Color.orange()
        )
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Warning Count", value=str(warning_count))

        await ctx.send(embed=embed)

        # Auto-punishment system
        if warning_count >= self.config.max_warnings:
            await self.handle_max_warnings(ctx, member)

    async def handle_max_warnings(self, ctx, member: discord.Member):
        """Handle actions when a member reaches maximum warnings."""
        warning_count = len(self.warnings[str(member.id)])

        if warning_count >= self.config.auto_ban_threshold:
            await member.ban(reason=f"Exceeded maximum warnings ({warning_count})")
            action = "banned"
        elif warning_count >= self.config.max_warnings:
            duration = timedelta(days=1)
            await member.timeout(duration, reason=f"Exceeded warning threshold ({warning_count})")
            action = "timed out for 24 hours"

        embed = discord.Embed(
            title="Automatic Punishment",
            description=f"{member.mention} has been {
                action} for exceeding warning threshold.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx, member: discord.Member):
        """View all warnings for a specific member.

        Shows a detailed list of all warnings a member has received,
        including reasons and dates.

        Parameters:
        -----------
        member: discord.Member
            The member whose warnings you want to view

        Examples:
        --------
        !warnings @user
        """
        user_warnings = self.warnings.get(str(member.id), [])

        if not user_warnings:
            return await ctx.send(f"{member.mention} has no warnings.")

        embed = discord.Embed(
            title=f"Warnings for {member.name}",
            color=discord.Color.orange()
        )

        for i, warning in enumerate(user_warnings, 1):
            moderator = ctx.guild.get_member(warning['moderator'])
            mod_name = moderator.name if moderator else "Unknown Moderator"
            timestamp = datetime.fromisoformat(warning['timestamp'])

            embed.add_field(
                name=f"Warning {i}",
                value=f"Reason: {warning['reason']}\n"
                f"By: {mod_name}\n"
                f"Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Clear all warnings for a specific member.

        Removes all recorded warnings for a member, giving them a clean slate.

        Parameters:
        -----------
        member: discord.Member
            The member whose warnings you want to clear

        Examples:
        --------
        !clearwarnings @user
        """
        if str(member.id) in self.warnings:
            del self.warnings[str(member.id)]
            await ctx.send(f"Cleared all warnings for {member.mention}")
        else:
            await ctx.send(f"{member.mention} has no warnings to clear.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Enhanced message monitoring for auto-moderation."""
        if message.author.bot or not self.auto_mod_enabled:
            return

        if not message.guild:
            return

        # Check permissions
        if message.author.guild_permissions.administrator:
            return

        # Spam detection
        await self.check_spam(message)

        # Content filtering
        await self.filter_content(message)

        # Mention spam
        if len(message.mentions) > self.config.max_mentions:
            await self.handle_violation(message, "mention spam")

        # Link spam
        links = re.findall(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+', message.content)
        if len(links) > self.config.max_links:
            await self.handle_violation(message, "link spam")

    async def check_spam(self, message):
        """Check for message spam."""
        user_id = str(message.author.id)
        now = datetime.utcnow()

        self.spam_control[user_id] = [
            msg_time for msg_time in self.spam_control[user_id]
            if (now - msg_time).seconds < self.config.spam_interval
        ]

        self.spam_control[user_id].append(now)

        if len(self.spam_control[user_id]) > self.config.spam_threshold:
            await self.handle_violation(message, "spam")

    async def filter_content(self, message):
        """Filter message content for prohibited words."""
        if any(word in message.content.lower() for word in self.filtered_words):
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} your message was removed for containing prohibited content.",
                delete_after=5
            )

    async def handle_violation(self, message, violation_type):
        """Handle auto-moderation violations."""
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        # Add warning
        warning = {
            "reason": f"Automatic warning: {violation_type}",
            "moderator": self.bot.user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.warnings[str(message.author.id)].append(warning)

        # Apply timeout
        try:
            duration = timedelta(minutes=self.config.mute_duration)
            await message.author.timeout(duration, reason=f"Auto-mod: {violation_type}")

            embed = discord.Embed(
                title="Auto-Moderation Action",
                description=f"{message.author.mention} has been timed out for {
                    violation_type}.",
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"Cannot timeout user {message.author.id}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addfilter(self, ctx, word: str):
        """Add a word to the content filter.

        Adds a word to the auto-moderation filter. Messages containing
        filtered words will be automatically removed.

        Parameters:
        -----------
        word: str
            The word to add to the filter

        Examples:
        --------
        !addfilter badword
        """
        self.filtered_words.add(word.lower())
        self.save_data()
        await ctx.send(f"Added '{word}' to filter", delete_after=5)
        await ctx.message.delete()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removefilter(self, ctx, word: str):
        """Remove a word from the content filter.

        Removes a word from the auto-moderation filter, allowing it
        to be used in messages again.

        Parameters:
        -----------
        word: str
            The word to remove from the filter

        Examples:
        --------
        !removefilter word
        """
        if word.lower() in self.filtered_words:
            self.filtered_words.remove(word.lower())
            self.save_data()
            await ctx.send(f"Removed '{word}' from filter", delete_after=5)
        await ctx.message.delete()

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def note(self, ctx, member: discord.Member, *, content: str):
        """Add a note about a user.

        Adds a private moderator note about a user for future reference.
        Notes are only visible to other moderators.

        Parameters:
        -----------
        member: discord.Member
            The member to add a note about
        content: str
            The content of the note

        Examples:
        --------
        !note @user Warned about behavior in voice chat
        """
        note = {
            "content": content,
            "moderator": ctx.author.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.user_notes[str(member.id)].append(note)
        self.save_data()
        await ctx.send(f"Added note for {member.mention}")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def notes(self, ctx, member: discord.Member):
        """View all notes about a user.

        Shows all moderator notes that have been recorded about a user.

        Parameters:
        -----------
        member: discord.Member
            The member whose notes you want to view

        Examples:
        --------
        !notes @user
        """
        user_notes = self.user_notes.get(str(member.id), [])

        if not user_notes:
            return await ctx.send(f"No notes found for {member.mention}")

        embed = discord.Embed(
            title=f"Notes for {member.name}",
            color=discord.Color.blue()
        )

        for i, note in enumerate(user_notes, 1):
            moderator = ctx.guild.get_member(note['moderator'])
            mod_name = moderator.name if moderator else "Unknown Moderator"
            timestamp = datetime.fromisoformat(note['timestamp'])

            embed.add_field(
                name=f"Note {i}",
                value=f"Content: {note['content']}\n"
                f"By: {mod_name}\n"
                f"Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ModerationCog(bot))
    logger.info("ModerationCog setup complete")
