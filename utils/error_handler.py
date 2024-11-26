import discord
from discord.ext import commands
import traceback
import sys


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command."""

        # This prevents any commands with local handlers being handled here
        if hasattr(ctx.command, 'on_error'):
            return

        # Get the original exception
        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Comando no encontrado. Usa `!help` para ver los comandos disponibles.")
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f'{ctx.command} ha sido deshabilitado.')
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Falta un argumento requerido: `{error.param}`")
            return

        if isinstance(error, commands.MissingPermissions):
            missing = [perm.replace('_', ' ').replace(
                'guild', 'server').title() for perm in error.missing_permissions]
            if len(missing) > 2:
                fmt = '{}, y {}'.format(", ".join(missing[:-1]), missing[-1])
            else:
                fmt = ' y '.join(missing)
            await ctx.send(f'No tienes los permisos necesarios para usar este comando. '
                           f'Necesitas: {fmt}')
            return

        if isinstance(error, commands.UserInputError):
            await ctx.send(f"Entrada inválida: {error}")
            return

        if isinstance(error, commands.NoPrivateMessage):
            try:
                await ctx.author.send(f'{ctx.command} no puede ser usado en mensajes privados.')
            except discord.HTTPException:
                pass
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.send("No tienes permiso para usar este comando.")
            return

        # For any other errors, print to console and notify user
        print('Ignoring exception in command {}:'.format(
            ctx.command), file=sys.stderr)
        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

        error_embed = discord.Embed(
            title="Ha ocurrido un error",
            description=f"Un error inesperado ocurrió mientras se ejecutaba el comando `{
                ctx.command}`.",
            color=discord.Color.red()
        )
        error_embed.add_field(
            name="Error", value=f"```{error}```", inline=False)
        error_embed.set_footer(
            text="Si este error persiste, por favor contacta a un administrador.")

        await ctx.send(embed=error_embed)

    @commands.command(name='repeat', aliases=['mimic', 'copy'])
    async def do_repeat(self, ctx, *, inp: str):
        """A simple command which repeats your input!"""
        await ctx.send(inp)

    @do_repeat.error
    async def do_repeat_handler(self, ctx, error):
        """A local Error Handler for our command do_repeat."""
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'inp':
                await ctx.send("You forgot to give me input to repeat!")


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
