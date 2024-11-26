import discord
from discord.ext import commands
import asyncio
import datetime
import pytz
import json
import aiofiles
from typing import List, Dict, Optional, Union
import logging
from dataclasses import dataclass, asdict
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    user_id: int
    channel_id: int
    guild_id: int
    time: datetime.datetime
    message: str
    repeat_interval: Optional[datetime.timedelta] = None
    notify_before: List[datetime.timedelta] = None
    participants: List[int] = None
    created_at: datetime.datetime = None
    reminder_id: str = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data['time'] = self.time.isoformat()
        data['repeat_interval'] = self.repeat_interval.total_seconds(
        ) if self.repeat_interval else None
        data['notify_before'] = [td.total_seconds()
                                 for td in self.notify_before] if self.notify_before else None
        data['created_at'] = self.created_at.isoformat(
        ) if self.created_at else None
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'Reminder':
        data['time'] = datetime.datetime.fromisoformat(data['time'])
        if data['repeat_interval']:
            data['repeat_interval'] = datetime.timedelta(
                seconds=data['repeat_interval'])
        if data['notify_before']:
            data['notify_before'] = [datetime.timedelta(
                seconds=s) for s in data['notify_before']]
        if data['created_at']:
            data['created_at'] = datetime.datetime.fromisoformat(
                data['created_at'])
        return cls(**data)


class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders: List[Reminder] = []
        self.check_reminders_task: Optional[asyncio.Task] = None
        self.save_task: Optional[asyncio.Task] = None
        self.timezone_cache: Dict[int, str] = {}

    async def cog_load(self):
        try:
            await self.load_reminders()
            self.check_reminders_task = asyncio.create_task(
                self.check_reminders())
            self.save_task = asyncio.create_task(self.auto_save())
            logger.info("RemindersCog loaded successfully")
        except Exception as e:
            logger.error(f"Error loading RemindersCog: {e}")
            raise

    async def cog_unload(self):
        if self.check_reminders_task:
            self.check_reminders_task.cancel()
        if self.save_task:
            self.save_task.cancel()
        await self.save_reminders()
        logger.info("RemindersCog unloaded successfully")

    async def load_reminders(self):
        try:
            async with aiofiles.open('data/reminders.json', 'r') as f:
                data = json.loads(await f.read())
                self.reminders = [Reminder.from_dict(r) for r in data]
                self.reminders.sort(key=lambda x: x.time)
        except FileNotFoundError:
            self.reminders = []
        except Exception as e:
            logger.error(f"Error loading reminders: {e}")
            self.reminders = []

    async def save_reminders(self):
        try:
            async with aiofiles.open('data/reminders.json', 'w') as f:
                data = [r.to_dict() for r in self.reminders]
                await f.write(json.dumps(data, indent=4))
        except Exception as e:
            logger.error(f"Error saving reminders: {e}")

    async def auto_save(self):
        while True:
            await asyncio.sleep(300)  # Save every 5 minutes
            await self.save_reminders()
            logger.info("Auto-save completed")

    async def check_reminders(self):
        while True:
            try:
                now = datetime.datetime.now(pytz.UTC)
                reminders_to_process = []

                for reminder in self.reminders:
                    if reminder.time <= now:
                        reminders_to_process.append(reminder)

                for reminder in reminders_to_process:
                    await self.process_reminder(reminder)
                    self.reminders.remove(reminder)

                    if reminder.repeat_interval:
                        new_time = reminder.time + reminder.repeat_interval
                        new_reminder = Reminder(
                            user_id=reminder.user_id,
                            channel_id=reminder.channel_id,
                            guild_id=reminder.guild_id,
                            time=new_time,
                            message=reminder.message,
                            repeat_interval=reminder.repeat_interval,
                            notify_before=reminder.notify_before,
                            participants=reminder.participants,
                            created_at=datetime.datetime.now(pytz.UTC),
                            reminder_id=f"{
                                reminder.user_id}-{datetime.datetime.now().timestamp()}"
                        )
                        self.reminders.append(new_reminder)
                        self.reminders.sort(key=lambda x: x.time)

                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in check_reminders: {e}")
                await asyncio.sleep(60)

    async def process_reminder(self, reminder: Reminder):
        try:
            channel = self.bot.get_channel(reminder.channel_id)
            if not channel:
                return

            user = self.bot.get_user(reminder.user_id)
            if not user:
                return

            embed = discord.Embed(
                title="⏰ Recordatorio",
                description=reminder.message,
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now(pytz.UTC)
            )

            embed.add_field(name="Creado por", value=user.mention, inline=True)

            if reminder.participants:
                participants = [f"<@{pid}>" for pid in reminder.participants]
                embed.add_field(
                    name="Participantes",
                    value=", ".join(participants),
                    inline=False
                )

            if reminder.repeat_interval:
                next_time = reminder.time + reminder.repeat_interval
                embed.add_field(
                    name="Próxima repetición",
                    value=next_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    inline=False
                )

            await channel.send(
                content=" ".join([f"<@{pid}>" for pid in reminder.participants]
                                 ) if reminder.participants else user.mention,
                embed=embed
            )

        except Exception as e:
            logger.error(f"Error processing reminder: {e}")

    @commands.group(invoke_without_command=True)
    async def remind(self, ctx, time: str, *, reminder: str):
        """Establece un recordatorio

        Ejemplos:
        !remind 1h Revisar el correo
        !remind 30m @user1 @user2 Reunión de equipo
        !remind 2d/1w Tarea semanal recurrente
        """
        try:
            # Parse mentions and remove them from the reminder message
            mentions = ctx.message.mentions
            mention_ids = [m.id for m in mentions]
            for mention in mentions:
                reminder = reminder.replace(
                    f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
            reminder = reminder.strip()

            # Parse time and repeat interval
            repeat_interval = None
            if '/' in time:
                time, repeat = time.split('/')
                repeat_interval = self.parse_time(repeat)

            when = self.parse_time(time)
            reminder_time = datetime.datetime.now(pytz.UTC) + when

            # Create notification times for important reminders
            notify_before = None
            if when.total_seconds() > 86400:  # If reminder is more than a day away
                notify_before = [
                    datetime.timedelta(days=1),
                    datetime.timedelta(hours=1)
                ]

            new_reminder = Reminder(
                user_id=ctx.author.id,
                channel_id=ctx.channel.id,
                guild_id=ctx.guild.id,
                time=reminder_time,
                message=reminder,
                repeat_interval=repeat_interval,
                notify_before=notify_before,
                participants=mention_ids if mention_ids else None,
                created_at=datetime.datetime.now(pytz.UTC),
                reminder_id=f"{
                    ctx.author.id}-{datetime.datetime.now().timestamp()}"
            )

            self.reminders.append(new_reminder)
            self.reminders.sort(key=lambda x: x.time)

            # Create response embed
            embed = discord.Embed(
                title="✅ Recordatorio establecido",
                color=discord.Color.green()
            )
            embed.add_field(name="Mensaje", value=reminder, inline=False)
            embed.add_field(
                name="Tiempo",
                value=reminder_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                inline=True
            )

            if repeat_interval:
                embed.add_field(
                    name="Repetición",
                    value=f"Cada {self.format_timedelta(repeat_interval)}",
                    inline=True
                )

            if mention_ids:
                participants = [f"<@{pid}>" for pid in mention_ids]
                embed.add_field(
                    name="Participantes",
                    value=", ".join(participants),
                    inline=False
                )

            await ctx.send(embed=embed)

        except ValueError as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @remind.command(name="list")
    async def remind_list(self, ctx, page: int = 1):
        """Lista todos tus recordatorios activos"""
        user_reminders = [
            r for r in self.reminders if r.user_id == ctx.author.id]

        if not user_reminders:
            return await ctx.send("No tienes recordatorios activos.")

        # Paginate reminders
        items_per_page = 5
        pages = (len(user_reminders) + items_per_page - 1) // items_per_page
        page = min(max(1, page), pages)

        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        embed = discord.Embed(
            title="📝 Tus recordatorios activos",
            color=discord.Color.blue()
        )

        for i, reminder in enumerate(user_reminders[start_idx:end_idx], start_idx + 1):
            value = f"**Mensaje:** {reminder.message}\n"
            value += f"**Tiempo:** {
                reminder.time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

            if reminder.repeat_interval:
                value += f"**Repetición:** Cada {
                    self.format_timedelta(reminder.repeat_interval)}\n"

            if reminder.participants:
                participants = [f"<@{pid}>" for pid in reminder.participants]
                value += f"**Participantes:** {', '.join(participants)}\n"

            embed.add_field(
                name=f"Recordatorio {i}",
                value=value,
                inline=False
            )

        embed.set_footer(text=f"Página {page}/{pages}")
        await ctx.send(embed=embed)

    @remind.command(name="delete")
    async def remind_delete(self, ctx, index: int):
        """Elimina un recordatorio específico"""
        user_reminders = [
            r for r in self.reminders if r.user_id == ctx.author.id]

        if not user_reminders:
            return await ctx.send("No tienes recordatorios activos.")

        if 1 <= index <= len(user_reminders):
            reminder = user_reminders[index - 1]
            self.reminders.remove(reminder)

            embed = discord.Embed(
                title="🗑️ Recordatorio eliminado",
                description=f"Mensaje: {reminder.message}\n"
                f"Tiempo: {reminder.time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                color=discord.Color.red()
            )

            await ctx.send(embed=embed)
            await self.save_reminders()
        else:
            await ctx.send("❌ Índice de recordatorio inválido.")

    @remind.command(name="clear")
    async def remind_clear(self, ctx):
        """Elimina todos tus recordatorios"""
        user_reminders = [
            r for r in self.reminders if r.user_id == ctx.author.id]

        if not user_reminders:
            return await ctx.send("No tienes recordatorios activos.")

        count = len(user_reminders)
        self.reminders = [
            r for r in self.reminders if r.user_id != ctx.author.id]

        embed = discord.Embed(
            title="🗑️ Recordatorios eliminados",
            description=f"Se han eliminado {count} recordatorios.",
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)
        await self.save_reminders()

    @staticmethod
    def parse_time(time: str) -> datetime.timedelta:
        """Parse time string into timedelta"""
        time = time.lower()
        units = {
            's': 'seconds',
            'm': 'minutes',
            'h': 'hours',
            'd': 'days',
            'w': 'weeks'
        }

        pattern = r'(\d+)([smhdw])'
        matches = re.findall(pattern, time)

        if not matches:
            raise ValueError(
                "Formato de tiempo inválido. Usa números seguidos de s(segundos), "
                "m(minutos), h(horas), d(días), o w(semanas). Ejemplo: 1h30m"
            )

        delta = datetime.timedelta()
        for value, unit in matches:
            if unit in units:
                kwargs = {units[unit]: int(value)}
                delta += datetime.timedelta(**kwargs)
            else:
                raise ValueError(f"Unidad de tiempo inválida: {unit}")

        return delta

    @staticmethod
    def format_timedelta(td: datetime.timedelta) -> str:
        """Format timedelta into human readable string"""
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days:
            parts.append(f"{days} día{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hora{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minuto{'s' if minutes != 1 else ''}")
        if seconds:
            parts.append(f"{seconds} segundo{'s' if seconds != 1 else ''}")

        return ", ".join(parts)


async def setup(bot):
    await bot.add_cog(RemindersCog(bot))
