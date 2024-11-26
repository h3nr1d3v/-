import discord
from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot, config_manager):
        self.bot = bot
        self.config_manager = config_manager

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, new_prefix: str):
        """Set a new command prefix for the bot."""
        if len(new_prefix) > 5:
            await ctx.send("Prefix must be 5 characters or less.")
            return
        self.bot.command_prefix = new_prefix
        self.config_manager.update_config('prefix', new_prefix)
        await ctx.send(f'Command prefix updated to: `{new_prefix}`')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def toggle_feature(self, ctx, feature: str):
        """Toggle a bot feature on or off."""
        valid_features = ['welcome_messages', 'logging', 'auto_moderation']
        if feature not in valid_features:
            await ctx.send(f"Invalid feature. Valid features are: {', '.join(valid_features)}")
            return
        current_state = self.config_manager.get_config(feature, False)
        new_state = not current_state
        self.config_manager.update_config(feature, new_state)
        await ctx.send(f'Feature "{feature}" is now {"enabled" if new_state else "disabled"}.')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def config(self, ctx):
        """Display current bot configuration."""
        config = self.config_manager.get_all_config()
        embed = discord.Embed(title="Bot Configuration",
                              color=discord.Color.blue())
        for key, value in config.items():
            embed.add_field(name=key, value=str(value), inline=False)
        await ctx.send(embed=embed)
