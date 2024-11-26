import discord
from discord.ext import commands
import json
import os


class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.commands_file = 'custom_commands.json'
        self.custom_commands = self.load_commands()

    def load_commands(self):
        if os.path.exists(self.commands_file):
            with open(self.commands_file, 'r') as f:
                return json.load(f)
        return {}

    def save_commands(self):
        with open(self.commands_file, 'w') as f:
            json.dump(self.custom_commands, f, indent=2)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_command(self, ctx, command_name: str, *, response: str):
        """Add a custom command"""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.custom_commands:
            self.custom_commands[guild_id] = {}

        self.custom_commands[guild_id][command_name] = response
        self.save_commands()
        await ctx.send(f"Custom command '{command_name}' added successfully!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def remove_command(self, ctx, command_name: str):
        """Remove a custom command"""
        guild_id = str(ctx.guild.id)
        if guild_id in self.custom_commands and command_name in self.custom_commands[guild_id]:
            del self.custom_commands[guild_id][command_name]
            self.save_commands()
            await ctx.send(f"Custom command '{command_name}' removed successfully!")
        else:
            await ctx.send(f"Custom command '{command_name}' not found!")

    @commands.command()
    async def list_commands(self, ctx):
        """List all custom commands for this server"""
        guild_id = str(ctx.guild.id)
        if guild_id in self.custom_commands and self.custom_commands[guild_id]:
            commands_list = "\n".join(self.custom_commands[guild_id].keys())
            embed = discord.Embed(
                title="Custom Commands", description=commands_list, color=discord.Color.blue())
            await ctx.send(embed=embed)
        else:
            await ctx.send("No custom commands found for this server.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = str(message.guild.id)
        if guild_id in self.custom_commands:
            command = message.content.lower()
            if command in self.custom_commands[guild_id]:
                await message.channel.send(self.custom_commands[guild_id][command])


async def setup(bot):
    await bot.add_cog(CustomCommandsCog(bot))
