import discord
from discord.ext import commands
import asyncio


class Help(commands.Cog):
    """Provides help and information about bot commands."""

    def __init__(self, bot):
        self.bot = bot
        self._original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._original_help_command


class CustomHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__()
        self.color = discord.Color.blue()
        self.verify_checks = True

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="Bot Commands",
            description="Here's a list of available commands. Use `!help <command>` for more info on a command.",
            color=self.color
        )

        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            command_signatures = [
                self.get_command_signature(c) for c in filtered]
            if command_signatures:
                cog_name = getattr(cog, "qualified_name", "No Category")
                cog_desc = getattr(cog, "description",
                                   "No description available.")
                value = f"{cog_desc}\n```\n" + \
                    "\n".join(command_signatures) + "\n```"
                embed.add_field(name=cog_name, value=value, inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(
            title=self.get_command_signature(command),
            description=command.help or "No description available.",
            color=self.color
        )

        # Add usage field if command has parameters
        if command.help:
            # Parse parameters section if it exists
            help_text = command.help
            if "Parameters:" in help_text:
                params_section = help_text.split("Parameters:")[1].strip()
                main_desc = help_text.split("Parameters:")[0].strip()
                embed.description = main_desc
                embed.add_field(name="Parameters", value=f"```\n{
                                params_section}\n```", inline=False)

        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(
                command.aliases), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_group_help(self, group):
        embed = discord.Embed(
            title=self.get_command_signature(group),
            description=group.help or "No description available.",
            color=self.color
        )

        filtered = await self.filter_commands(group.commands, sort=True)
        if filtered:
            embed.add_field(
                name="Subcommands",
                value="\n".join(f"`{self.get_command_signature(c)}`\n{
                                c.help or 'No description'}" for c in filtered),
                inline=False
            )

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"{cog.qualified_name} Commands",
            description=cog.description or "No description available.",
            color=self.color
        )

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(
                name=self.get_command_signature(command),
                value=command.help or "No description available.",
                inline=False
            )

        channel = self.get_destination()
        await channel.send(embed=embed)

    def get_command_signature(self, command):
        return f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
