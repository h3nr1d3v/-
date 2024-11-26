import discord
from discord.ext import commands
import aiohttp
import asyncio
from datetime import datetime

WELCOME_CHANNEL_ID =  # ID channels here
LEFT_CHANNEL_ID =  # ID channels here
BANNED_CHANNEL_ID =  # ID channels here
UNBANNED_CHANNEL_ID =  # ID channels here
WARNINGS_CHANNEL_ID =  # ID channels here


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.image_cache = {}
        self.cache_expiry = {}

    def cog_unload(self):
        asyncio.create_task(self.session.close())

    async def fetch_random_anime_image(self):
        current_time = datetime.now()
        if 'anime' in self.image_cache and (current_time - self.cache_expiry['anime']).total_seconds() < 3600:
            return self.image_cache['anime']

        url = "https://nekos.best/api/v2/neko"
        async with self.session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                image_url = data["results"][0]["url"]
                self.image_cache['anime'] = image_url
                self.cache_expiry['anime'] = current_time
                return image_url
        return None

    async def create_embed(self, title, description, color, member=None, image_url=None):
        embed = discord.Embed(
            title=title, description=description, color=color)
        if member and member.display_avatar:
            embed.set_author(name=member.display_name,
                             icon_url=member.display_avatar.url)
        if image_url:
            embed.set_image(url=image_url)
        embed.set_footer(
            text=f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return embed

    async def send_embed(self, channel_id, embed):
        channel = self.bot.get_channel(channel_id)
        if channel is not None:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(
                    f"Failed to send message - insufficient permissions in channel {channel.name}")
            except discord.HTTPException as e:
                print(f"Failed to send message - HTTPException: {e}")
        else:
            print(f"Channel with ID '{channel_id}' not found")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        image_url = await self.fetch_random_anime_image()
        embed = await self.create_embed(
            title=f"Welcome to the server, {member.display_name}!",
            description=f"We're glad to have you here, {
                member.mention}. To get started with our bot, try the following:",
            color=discord.Color.green(),
            member=member,
            image_url=image_url
        )
        embed.add_field(name="View All Commands",
                        value="Type `!help` to see a list of all available commands.", inline=False)
        embed.add_field(name="Get Help on a Specific Command",
                        value="Type `!help <command_name>` to get detailed information about a specific command.", inline=False)
        embed.add_field(
            name="Server Rules", value="Please read our server rules in the #rules channel.", inline=False)
        await self.send_embed(WELCOME_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        image_url = await self.fetch_random_anime_image()
        embed = await self.create_embed(
            title=f"{member.name} has left the server.",
            description="We hope to see you again!",
            color=discord.Color.red(),
            member=member,
            image_url=image_url
        )
        await self.send_embed(LEFT_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        image_url = await self.fetch_random_anime_image()
        embed = await self.create_embed(
            title=f"{user.name} has been banned from the server.",
            description="Please ensure to follow the server rules.",
            color=discord.Color.red(),
            image_url=image_url
        )
        await self.send_embed(BANNED_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        image_url = await self.fetch_random_anime_image()
        embed = await self.create_embed(
            title=f"{user.name} has been unbanned from the server.",
            description="Welcome back!",
            color=discord.Color.green(),
            image_url=image_url
        )
        await self.send_embed(UNBANNED_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            new_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)

            if new_roles:
                role_names = ", ".join([role.name for role in new_roles])
                embed = await self.create_embed(
                    title=f"Role Update for {after.name}",
                    description=f"New role(s) added: {role_names}",
                    color=discord.Color.blue(),
                    member=after
                )
                await self.send_embed(WARNINGS_CHANNEL_ID, embed)

            if removed_roles:
                role_names = ", ".join([role.name for role in removed_roles])
                embed = await self.create_embed(
                    title=f"Role Update for {after.name}",
                    description=f"Role(s) removed: {role_names}",
                    color=discord.Color.orange(),
                    member=after
                )
                await self.send_embed(WARNINGS_CHANNEL_ID, embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def welcome_test(self, ctx):
        """Test the welcome message"""
        await self.on_member_join(ctx.author)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def goodbye_test(self, ctx):
        """Test the goodbye message"""
        await self.on_member_remove(ctx.author)


def setup(bot):
    bot.add_cog(WelcomeCog(bot))
