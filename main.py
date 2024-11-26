import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
import asyncio
from typing import Dict, List, Set
from cogs.admin import Admin
from cogs.user import User
from cogs.moderation import Moderation
from utils.error_handler import ErrorHandler
from utils.config_manager import ConfigManager
from cogs.music import Music
from cogs.IA_S import IA_S
from cogs.levels import Levels
from cogs.polls import Polls
from cogs.reminders import Reminders
from cogs.games import Games
from cogs.tickets import Tickets
from cogs.logs import Logs
from cogs.translation import Translation
from cogs.help import Help
from cogs.welcome import Welcome
from cogs.anime import Anime
from cogs.custom_commands import CustomCommands
from cogs.analytics import Analytics

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
    '%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Create data directory
os.makedirs('data', exist_ok=True)

# Role-based access configuration
ROLE_PERMISSIONS = {
    "Master SS": {
        "cogs": [
            Admin, Analytics, CustomCommands, Anime, Games, IA_S,
            Levels, Logs, Moderation, Music, Polls, Reminders,
            Tickets, Translation,
        ],
        "level_required": 100
    },
    "Intermedios SS": {
        "cogs": [
            Anime, Games, IA_S, Music, Polls, Reminders,
            Tickets, Translation
        ],
        "level_required": 50
    },
    "Novatos SS": {
        "cogs": [
            Anime, Games, Music, Tickets, Reminders
        ],
        "level_required": 20
    }
}

# Default cogs available to everyone
DEFAULT_COGS = [Games, Music, Tickets, Reminders, Help]


class RoleBasedBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role_permissions = ROLE_PERMISSIONS
        self.cog_permissions: Dict[str, Set[str]] = {}
        self.config_manager = ConfigManager('config.json')
        self.start_time = None

    async def get_user_level(self, user_id: int) -> int:
        """Get user level from Levels."""
        if not self.get_cog("Levels"):
            return 0

        levels_cog = self.get_cog("Levels")
        user_data = levels_cog.levels.get(str(user_id), {})
        return user_data.get("level", 0)

    def get_highest_role(self, member: discord.Member) -> str:
        """Get the highest permission role for a member."""
        member_roles = set(role.name for role in member.roles)
        for role in ["Master SS", "Intermedios SS", "Novatos SS"]:
            if role in member_roles:
                return role
        return None

    async def has_cog_permission(self, ctx: commands.Context, cog_name: str) -> bool:
        """Check if a user has permission to use a cog."""
        # Always allow default cogs
        cog_class = type(self.get_cog(cog_name))
        if cog_class in DEFAULT_COGS:
            return True

        # Get user's highest role and level
        highest_role = self.get_highest_role(ctx.author)
        user_level = await self.get_user_level(ctx.author.id)

        if not highest_role:
            return False

        role_config = self.role_permissions.get(highest_role)
        if not role_config:
            return False

        # Check level requirement
        if user_level < role_config["level_required"]:
            return False

        # Check if the cog is allowed for this role
        return cog_class in role_config["cogs"]


class CustomHelpCommand(commands.DefaultHelpCommand):
    async def filter_commands(self, commands, *, sort=True, key=None):
        """Filter commands based on role permissions."""
        filtered = []
        for cmd in commands:
            try:
                if cmd.cog:
                    if await self.context.bot.has_cog_permission(self.context, cmd.cog.qualified_name):
                        filtered.append(cmd)
                else:
                    filtered.append(cmd)
            except Exception:
                continue

        if sort:
            filtered.sort(key=key or (lambda c: c.name))

        return filtered


# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = RoleBasedBot(command_prefix='!', intents=intents,
                   help_command=CustomHelpCommand())


@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    await bot.change_presence(activity=discord.Game(name="𝘕𝘦𝘬𝘰𝘚𝘩𝘦𝘭𝘭 🌸 ┊!ʜᴇʟᴘ"))
    bot.start_time = asyncio.get_event_loop().time()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
        return

    if isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You don't have access to this command due to role or level restrictions.")
        return

    # Log other errors
    logger.error(f"Command error: {error}")


@bot.check
async def check_cog_permissions(ctx):
    """Global check for cog permissions."""
    if not ctx.cog:
        return True

    return await bot.has_cog_permission(ctx, ctx.cog.qualified_name)


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)


async def load_cogs():
    """Load all cogs with role-based access control."""
    cogs_to_load = [
        (Admin, bot, bot.config_manager),
        (User, bot, bot.config_manager),
        (Moderation, bot, bot.config_manager),
        (Music, bot),
        (IA_S, bot),
        (Levels, bot),
        (Polls, bot),
        (Reminders, bot),
        (Games, bot),
        (Tickets, bot),
        (Logs, bot),
        (Translation, bot),
        (Help, bot),
        (Welcome, bot),
        (Anime, bot),
        (CustomCommands, bot),
        (Analytics, bot)
    ]

    for cog_info in cogs_to_load:
        try:
            if len(cog_info) > 2:
                await bot.add_cog(cog_info[0](cog_info[1], cog_info[2]))
            else:
                await bot.add_cog(cog_info[0](cog_info[1]))
            logger.info(f"Loaded cog: {cog_info[0].__name__}")
        except Exception as e:
            logger.error(f"Failed to load cog {cog_info[0].__name__}: {e}")

    # Set up error handling
    await bot.add_cog(ErrorHandler(bot))


async def main():
    # Load cogs
    await load_cogs()

    # Run the bot
    await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())

    # Import and start webserver after bot initialization
    from webserver import start_webserver
    start_webserver(bot)
