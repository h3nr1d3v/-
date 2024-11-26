import discord
from discord.ext import commands
from typing import Optional
from datetime import datetime
import humanize
import platform
import psutil
import os


class User(commands.Cog):
    """User information and utility commands.

    This cog provides commands for getting information about users,
    the server, and system statistics.
    """

    def __init__(self, bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager
        self.start_time = datetime.utcnow()

    @commands.command()
    async def info(self, ctx):
        """Get detailed information about the server.

        Shows various statistics and information about the current server,
        including member count, channel counts, and server features.
        """
        features = ", ".join(ctx.guild.features) or "None"

        embed = discord.Embed(
            title=f"Information about {ctx.guild.name}",
            color=discord.Color.green(),
            description=f"Server ID: {ctx.guild.id}"
        )

        # Server Info
        embed.add_field(
            name="Owner", value=ctx.guild.owner.mention, inline=True)
        embed.add_field(name="Region", value=str(ctx.guild.region).title(
        ) if hasattr(ctx.guild, 'region') else 'Unknown', inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(
            ctx.guild.created_at, style='R'), inline=True)

        # Statistics
        embed.add_field(name="Members", value=f"""
            Total: {ctx.guild.member_count}
            Humans: {len([m for m in ctx.guild.members if not m.bot])}
            Bots: {len([m for m in ctx.guild.members if m.bot])}
        """, inline=True)

        # Channels
        embed.add_field(name="Channels", value=f"""
            Text: {len(ctx.guild.text_channels)}
            Voice: {len(ctx.guild.voice_channels)}
            Categories: {len(ctx.guild.categories)}
            Total: {len(ctx.guild.channels)}
        """, inline=True)

        # Other Info
        embed.add_field(name="Other", value=f"""
            Roles: {len(ctx.guild.roles)}
            Emojis: {len(ctx.guild.emojis)}/{ctx.guild.emoji_limit}
            Boost Level: {ctx.guild.premium_tier}
            Boosts: {ctx.guild.premium_subscription_count}
        """, inline=True)

        # Server Features
        if ctx.guild.features:
            embed.add_field(name="Server Features",
                            value=features, inline=False)

        # Server Icon
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        # Server Banner
        if ctx.guild.banner:
            embed.set_image(url=ctx.guild.banner.url)

        await ctx.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx, member: Optional[discord.Member] = None):
        """Get detailed information about a user.

        Parameters:
        -----------
        member: discord.Member
            The member to get information about. If not specified, shows your own info.

        Examples:
        --------
        !userinfo
        !userinfo @user
        """
        member = member or ctx.author
        roles = [role.mention for role in member.roles if role !=
                 ctx.guild.default_role]

        embed = discord.Embed(
            title=f"User Info - {member}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)

        # Basic Info
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(
            name="Nickname", value=member.nick if member.nick else "None", inline=True)
        embed.add_field(
            name="Bot", value="Yes" if member.bot else "No", inline=True)

        # Dates
        embed.add_field(name="Account Created", value=f"{discord.utils.format_dt(member.created_at, style='F')}\n({
                        discord.utils.format_dt(member.created_at, style='R')})", inline=False)
        embed.add_field(name="Joined Server", value=f"{discord.utils.format_dt(member.joined_at, style='F')}\n({
                        discord.utils.format_dt(member.joined_at, style='R')})", inline=False)

        # Status and Activity
        status_emoji = {
            "online": "🟢",
            "idle": "🟡",
            "dnd": "🔴",
            "offline": "⚫"
        }

        status = f"{status_emoji.get(str(member.status), '⚫')} {
            str(member.status).title()}"
        embed.add_field(name="Status", value=status, inline=True)

        if member.activity:
            if isinstance(member.activity, discord.Spotify):
                activity = f"Listening to {member.activity.title} by {
                    member.activity.artist}"
            else:
                activity = f"{member.activity.type.name.title()} {
                    member.activity.name}"
            embed.add_field(name="Activity", value=activity, inline=True)

        # Roles
        if roles:
            embed.add_field(
                name=f"Roles [{len(roles)}]", value=" ".join(roles), inline=False)

        # Permissions
        key_permissions = []
        if member.guild_permissions.administrator:
            key_permissions.append("Administrator")
        if member.guild_permissions.manage_guild:
            key_permissions.append("Manage Server")
        if member.guild_permissions.manage_roles:
            key_permissions.append("Manage Roles")
        if member.guild_permissions.manage_channels:
            key_permissions.append("Manage Channels")
        if member.guild_permissions.manage_messages:
            key_permissions.append("Manage Messages")
        if member.guild_permissions.kick_members:
            key_permissions.append("Kick Members")
        if member.guild_permissions.ban_members:
            key_permissions.append("Ban Members")

        if key_permissions:
            embed.add_field(name="Key Permissions", value=", ".join(
                key_permissions), inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx, member: Optional[discord.Member] = None):
        """Get the avatar of a user in full size.

        Parameters:
        -----------
        member: discord.Member
            The member whose avatar you want to see. If not specified, shows your own avatar.

        Examples:
        --------
        !avatar
        !avatar @user
        """
        member = member or ctx.author
        embed = discord.Embed(title=f"Avatar - {member}", color=member.color)
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def servericon(self, ctx):
        """Get the server's icon in full size."""
        if not ctx.guild.icon:
            await ctx.send("This server doesn't have an icon!")
            return

        embed = discord.Embed(
            title=f"Server Icon - {ctx.guild.name}", color=discord.Color.blue())
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def botinfo(self, ctx):
        """Get information about the bot.

        Shows various statistics about the bot including uptime,
        system usage, and version information.
        """
        embed = discord.Embed(
            title="Bot Information",
            color=discord.Color.blue(),
            description="Statistics and information about the bot."
        )

        # Version Info
        embed.add_field(
            name="Version Info",
            value=f"""
                Python: {platform.python_version()}
                Discord.py: {discord.__version__}
            """,
            inline=False
        )

        # Bot Stats
        total_members = sum(guild.member_count for guild in self.bot.guilds)
        embed.add_field(
            name="Bot Stats",
            value=f"""
                Servers: {len(self.bot.guilds)}
                Users: {total_members}
                Commands: {len(self.bot.commands)}
            """,
            inline=True
        )

        # System Info
        process = psutil.Process()
        with process.oneshot():
            mem_usage = process.memory_info().rss / 1024**2
            cpu_usage = process.cpu_percent()

        embed.add_field(
            name="System",
            value=f"""
                CPU Usage: {cpu_usage:.1f}%
                Memory: {mem_usage:.1f} MB
                OS: {platform.system()} {platform.release()}
            """,
            inline=True
        )

        # Uptime
        uptime = datetime.utcnow() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        embed.add_field(
            name="Uptime",
            value=f"{days}d {hours}h {minutes}m {seconds}s",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def roles(self, ctx):
        """List all roles in the server and their members."""
        roles = sorted(ctx.guild.roles, key=lambda x: x.position, reverse=True)

        embed = discord.Embed(
            title=f"Roles in {ctx.guild.name}",
            color=discord.Color.blue(),
            description=f"Total Roles: {len(roles)}"
        )

        for role in roles:
            if role != ctx.guild.default_role:
                members = len(role.members)
                embed.add_field(
                    name=f"{role.name} ({members} members)",
                    value=f"ID: {role.id}\nColor: {role.color}\nHoisted: {
                        role.hoist}\nMentionable: {role.mentionable}",
                    inline=False
                )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(UserCog(bot, None))
