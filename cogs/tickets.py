import discord
from discord.ext import commands
import asyncio
import json
from datetime import datetime


class Tickets(commands.Cog):
    """Support ticket system for server management.

    This cog provides a complete ticket management system including:
    - Automated ticket creation
    - Ticket transcripts
    - User management within tickets
    - Logging system
    """

    def __init__(self, bot):
        self.bot = bot
        self.tickets_data = self.load_tickets_data()

    def load_tickets_data(self):
        try:
            with open('tickets_data.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"setup_message_id": None, "category_id": None, "ticket_counter": 0}

    def save_tickets_data(self):
        with open('tickets_data.json', 'w') as f:
            json.dump(self.tickets_data, f)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx, *, category_name="Tickets"):
        """Set up the ticket system for your server.

        Creates a reaction-based ticket system where users can create support
        tickets by clicking on a reaction. Also creates a dedicated category
        for ticket channels.

        Parameters:
        -----------
        category_name: str
            The name for the tickets category (default: "Tickets")

        Examples:
        --------
        !setup_tickets
        !setup_tickets Support Tickets
        """
        category = discord.utils.get(ctx.guild.categories, name=category_name)
        if not category:
            category = await ctx.guild.create_category(category_name)

        embed = discord.Embed(
            title="Support Tickets",
            description="React with 🎫 to open a new support ticket!",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)
        await message.add_reaction('🎫')

        self.tickets_data["setup_message_id"] = message.id
        self.tickets_data["category_id"] = category.id
        self.save_tickets_data()

        await ctx.send("Ticket system has been set up successfully!")

    @commands.command()
    async def close(self, ctx):
        """Close the current support ticket.

        Closes the ticket channel and sends a transcript to the ticket creator.
        Requires confirmation before closing.

        Must be used in a ticket channel.

        Examples:
        --------
        !close
        """
        if not ctx.channel.name.startswith('ticket-'):
            await ctx.send("This command can only be used in a ticket channel.")
            return

        confirm_message = await ctx.send("Are you sure you want to close this ticket? React with ✅ to confirm.")
        await confirm_message.add_reaction('✅')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅' and reaction.message.id == confirm_message.id

        try:
            await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Ticket closure cancelled.")
            return

        try:
            transcript = await self.generate_transcript(ctx.channel)
            await ctx.author.send("Your support ticket has been closed. Here's a transcript:", file=discord.File(transcript, "transcript.txt"))
        except discord.Forbidden:
            await ctx.send("I couldn't send you a DM with the transcript. Make sure your DMs are open.")

        log_channel = discord.utils.get(
            ctx.guild.text_channels, name="ticket-logs")
        if log_channel:
            await log_channel.send(f"Ticket {ctx.channel.name} closed by {ctx.author.mention}")

        await ctx.send("Closing this ticket in 5 seconds...")
        await asyncio.sleep(5)
        await ctx.channel.delete()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_to_ticket(self, ctx, user: discord.Member):
        """Add a user to the current ticket channel.

        Grants a user permission to view and send messages in the ticket.
        Must be used in a ticket channel.

        Parameters:
        -----------
        user: discord.Member
            The user to add to the ticket

        Examples:
        --------
        !add_to_ticket @user
        """
        if not ctx.channel.name.startswith('ticket-'):
            await ctx.send("This command can only be used in a ticket channel.")
            return

        await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
        await ctx.send(f"{user.mention} has been added to the ticket.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def remove_from_ticket(self, ctx, user: discord.Member):
        """Remove a user from the current ticket channel.

        Revokes a user's permission to view and send messages in the ticket.
        Must be used in a ticket channel.

        Parameters:
        -----------
        user: discord.Member
            The user to remove from the ticket

        Examples:
        --------
        !remove_from_ticket @user
        """
        if not ctx.channel.name.startswith('ticket-'):
            await ctx.send("This command can only be used in a ticket channel.")
            return

        await ctx.channel.set_permissions(user, overwrite=None)
        await ctx.send(f"{user.mention} has been removed from the ticket.")

    @commands.command()
    async def ticket_info(self, ctx):
        """Display information about the current ticket.

        Shows details about the ticket including:
        - Creation date
        - Ticket creator
        - Current members

        Must be used in a ticket channel.

        Examples:
        --------
        !ticket_info
        """
        if not ctx.channel.name.startswith('ticket-'):
            await ctx.send("This command can only be used in a ticket channel.")
            return

        embed = discord.Embed(title=f"Ticket Information: {
                              ctx.channel.name}", color=discord.Color.blue())
        embed.add_field(name="Created At", value=ctx.channel.created_at.strftime(
            "%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Creator", value=ctx.channel.members[1].mention if len(
            ctx.channel.members) > 1 else "Unknown", inline=False)
        embed.add_field(name="Current Members", value=", ".join(
            [member.mention for member in ctx.channel.members if not member.bot]), inline=False)

        await ctx.send(embed=embed)

    async def generate_transcript(self, channel):
        transcript = f"Transcript for {channel.name}\n\n"
        async for message in channel.history(limit=None, oldest_first=True):
            transcript += f"{message.created_at} - {
                message.author.name}: {message.content}\n"

        with open(f"{channel.name}-transcript.txt", "w", encoding="utf-8") as f:
            f.write(transcript)

        return f"{channel.name}-transcript.txt"

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return

        if reaction.message.id == self.tickets_data["setup_message_id"] and str(reaction.emoji) == '🎫':
            await self.create_ticket(user, reaction.message.guild)

    async def create_ticket(self, user, guild):
        category = discord.utils.get(
            guild.categories, id=self.tickets_data["category_id"])
        if not category:
            return

        self.tickets_data["ticket_counter"] += 1
        ticket_number = self.tickets_data["ticket_counter"]
        self.save_tickets_data()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            f'ticket-{ticket_number}',
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"Ticket #{ticket_number}",
            description=f"Welcome {
                user.mention} to your support ticket! Please describe your issue and a staff member will be with you shortly.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Type !close to close this ticket")
        await channel.send(embed=embed)

        log_channel = discord.utils.get(
            guild.text_channels, name="ticket-logs")
        if log_channel:
            await log_channel.send(f"Ticket #{ticket_number} created by {user.mention}")


async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
