import discord
from discord.ext import commands
import json
import asyncio
import random
from datetime import datetime, timedelta
import aiohttp
import aiofiles
from typing import Optional, Dict, List, Union
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Achievements:
    ACHIEVEMENTS = {
        "first_message": {
            "name": "First Steps",
            "description": "Send your first message",
            "xp_reward": 100
        },
        "message_streak_7": {
            "name": "Weekly Warrior",
            "description": "Maintain a 7-day message streak",
            "xp_reward": 500
        },
        "reach_level_10": {
            "name": "Rising Star",
            "description": "Reach level 10",
            "xp_reward": 1000
        },
        "reach_level_50": {
            "name": "Veteran",
            "description": "Reach level 50",
            "xp_reward": 5000
        },
        "messages_100": {
            "name": "Chatterbox",
            "description": "Send 100 messages",
            "xp_reward": 300
        },
        "messages_1000": {
            "name": "Message Master",
            "description": "Send 1000 messages",
            "xp_reward": 3000
        },
    }


class LevelRewards:
    ROLES = {
        20: "Novatos SS",
        60: "Intermedios SS",
        120: "Master SS"
    }

    XP_MULTIPLIERS = {
        "Supporter": 1.2,
        "Premium": 1.5,
        "VIP": 2.0
    }


class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.levels: Dict[str, Dict] = {}
        self.achievements: Dict[str, List] = {}
        self.tasks: Dict[str, Dict] = {}
        self.karma: Dict[str, int] = {}
        self.streaks: Dict[str, Dict] = {}
        self.xp_cooldown = commands.CooldownMapping.from_cooldown(
            1, 60, commands.BucketType.user)
        self.session: Optional[aiohttp.ClientSession] = None
        self.image_cache: Dict[str, str] = {}
        self.cache_expiry: Dict[str, datetime] = {}
        self.save_task: Optional[asyncio.Task] = None
        self.boost_events: Dict[str, datetime] = {}

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        # Initialize data files if they don't exist
        self.initialize_data_files()

    def initialize_data_files(self):
        """Initialize empty data files if they don't exist."""
        files = ['levels.json', 'achievements.json',
                 'tasks.json', 'karma.json', 'streaks.json']
        for file in files:
            file_path = f'data/{file}'
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump({}, f)

    async def cog_load(self):
        """Initialize the cog."""
        try:
            self.session = aiohttp.ClientSession()
            await self.load_all_data()
            self.save_task = asyncio.create_task(self.auto_save())
            logger.info("LevelsCog loaded successfully")
        except Exception as e:
            logger.error(f"Error loading LevelsCog: {e}")
            raise

    async def load_all_data(self):
        """Load all data files."""
        self.levels = await self.load_data('data/levels.json')
        self.achievements = await self.load_data('data/achievements.json')
        self.tasks = await self.load_data('data/tasks.json')
        self.karma = await self.load_data('data/karma.json')
        self.streaks = await self.load_data('data/streaks.json')

    async def load_data(self, filename: str) -> Dict:
        """Load data from a JSON file."""
        try:
            async with aiofiles.open(filename, 'r') as f:
                content = await f.read()
                return json.loads(content) if content else {}
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"Error decoding {filename}")
            return {}
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}

    async def get_random_image(self) -> str:
        """Get a random anime reaction image."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            current_time = datetime.utcnow()
            if 'anime' in self.image_cache and (current_time - self.cache_expiry['anime']).total_seconds() < 3600:
                return self.image_cache['anime']

            safe_categories = ['smile', 'wave',
                               'thumbsup', 'dance', 'happy', 'pat']
            category = random.choice(safe_categories)

            async with self.session.get(f"https://nekos.best/api/v2/{category}") as response:
                if response.status == 200:
                    data = await response.json()
                    if 'results' in data and len(data['results']) > 0:
                        image_url = data['results'][0].get('url')
                        self.image_cache['anime'] = image_url
                        self.cache_expiry['anime'] = current_time
                        return image_url
        except Exception as e:
            logger.error(f"Error getting random image: {e}")

        return 'https://example.com/default_image.png'

    async def save_data(self, data: Dict, filename: str):
        try:
            async with aiofiles.open(filename, 'w') as f:
                await f.write(json.dumps(data, indent=4))
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")

    async def save_all_data(self):
        try:
            await asyncio.gather(
                self.save_data(self.levels, 'data/levels.json'),
                self.save_data(self.achievements, 'data/achievements.json'),
                self.save_data(self.tasks, 'data/tasks.json'),
                self.save_data(self.karma, 'data/karma.json'),
                self.save_data(self.streaks, 'data/streaks.json')
            )
            logger.info("All data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    async def auto_save(self):
        while True:
            try:
                await asyncio.sleep(60)  # Save every 1 minutes
                await self.save_all_data()
            except Exception as e:
                logger.error(f"Error in auto_save: {e}")

    def get_level_xp(self, level: int) -> int:
        return 5 * (level ** 2) + 50 * level + 100

    def get_level_from_xp(self, xp: int) -> int:
        level = 0
        while xp >= self.get_level_xp(level):
            xp -= self.get_level_xp(level)
            level += 1
        return level

    def get_xp_multiplier(self, member: discord.Member) -> float:
        multiplier = 1.0
        for role in member.roles:
            if role.name in LevelRewards.XP_MULTIPLIERS:
                multiplier = max(
                    multiplier, LevelRewards.XP_MULTIPLIERS[role.name])
        return multiplier

    async def check_achievements(self, member: discord.Member):
        """Check and award achievements for a user"""
        user_id = str(member.id)
        if user_id not in self.achievements:
            self.achievements[user_id] = []

        user_data = self.levels.get(user_id, {})
        current_achievements = self.achievements[user_id]

        for achievement_id, achievement in Achievements.ACHIEVEMENTS.items():
            if achievement_id in current_achievements:
                continue

            achieved = False

            if achievement_id == "first_message" and user_data.get("total_messages", 0) >= 1:
                achieved = True
            elif achievement_id == "message_streak_7" and self.streaks.get(user_id, {}).get("current_streak", 0) >= 7:
                achieved = True
            elif achievement_id == "reach_level_10" and user_data.get("level", 0) >= 10:
                achieved = True
            elif achievement_id == "reach_level_50" and user_data.get("level", 0) >= 50:
                achieved = True
            elif achievement_id == "messages_100" and user_data.get("total_messages", 0) >= 100:
                achieved = True
            elif achievement_id == "messages_1000" and user_data.get("total_messages", 0) >= 1000:
                achieved = True

            if achieved:
                await self.award_achievement(member, achievement_id)

    async def award_achievement(self, member: discord.Member, achievement_id: str):
        """Award an achievement to a user"""
        user_id = str(member.id)
        achievement = Achievements.ACHIEVEMENTS[achievement_id]

        if user_id not in self.achievements:
            self.achievements[user_id] = []

        if achievement_id not in self.achievements[user_id]:
            self.achievements[user_id].append(achievement_id)

            if user_id in self.levels:
                self.levels[user_id]["xp"] += achievement["xp_reward"]

            embed = discord.Embed(
                title="🏆 Achievement Unlocked! 🏆",
                description=f"Congratulations {member.mention}!",
                color=discord.Color.gold()
            )
            embed.add_field(
                name=achievement["name"], value=achievement["description"])
            embed.add_field(name="Reward", value=f"{
                            achievement['xp_reward']} XP")

            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                if member.guild:
                    for channel in member.guild.text_channels:
                        if channel.permissions_for(member.guild.me).send_messages:
                            await channel.send(embed=embed)
                            break

    async def level_up(self, member: discord.Member, channel: discord.TextChannel, new_level: int):
        """Handle level up event"""
        embed = discord.Embed(
            title="🎉 Level Up! 🎉",
            description=f"{member.mention} has reached level {new_level}!",
            color=discord.Color.green()
        )

        # Add next level information
        next_level_xp = self.get_level_xp(new_level)
        embed.add_field(
            name="Next Level",
            value=f"You need {next_level_xp:,} XP to reach level {
                new_level + 1}",
            inline=False
        )

        try:
            image_url = await self.get_random_image()
            if image_url:
                embed.set_image(url=image_url)
        except Exception as e:
            logger.error(f"Error getting random image: {e}")

        await channel.send(embed=embed)

    async def check_tasks(self, member: discord.Member):
        """Check and update user tasks"""
        user_id = str(member.id)
        if user_id not in self.tasks:
            self.tasks[user_id] = self.generate_daily_tasks()

        current_time = datetime.utcnow()
        task_data = self.tasks[user_id]

        if current_time.date() > datetime.fromisoformat(task_data["date"]).date():
            self.tasks[user_id] = self.generate_daily_tasks()
            return

        for task in task_data["tasks"]:
            if not task["completed"]:
                if self.check_task_completion(member, task):
                    task["completed"] = True
                    await self.reward_task_completion(member, task)

    def generate_daily_tasks(self) -> Dict:
        """Generate new daily tasks"""
        tasks = [
            {
                "type": "messages",
                "goal": random.randint(10, 50),
                "reward": random.randint(100, 500),
                "completed": False
            },
            {
                "type": "xp",
                "goal": random.randint(500, 2000),
                "reward": random.randint(200, 1000),
                "completed": False
            }
        ]
        return {
            "date": datetime.utcnow().isoformat(),
            "tasks": tasks
        }

    def check_task_completion(self, member: discord.Member, task: Dict) -> bool:
        """Check if a task has been completed"""
        user_id = str(member.id)
        user_data = self.levels.get(user_id, {})

        if task["type"] == "messages":
            return user_data.get("total_messages", 0) >= task["goal"]
        elif task["type"] == "xp":
            return user_data.get("xp", 0) >= task["goal"]
        return False

    async def reward_task_completion(self, member: discord.Member, task: Dict):
        """Reward user for completing a task"""
        user_id = str(member.id)
        self.levels[user_id]["xp"] += task["reward"]

        embed = discord.Embed(
            title="✅ Task Completed!",
            description=f"You've completed a daily task and earned {
                task['reward']} XP!",
            color=discord.Color.green()
        )

        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        await self.process_message_xp(message)
        await self.check_achievements(message.author)
        await self.check_tasks(message.author)
        await self.update_streak(message.author)

    async def process_message_xp(self, message: discord.Message):
        user_id = str(message.author.id)

        if user_id not in self.levels:
            self.levels[user_id] = {
                "xp": 0,
                "level": 0,
                "last_message": datetime.utcnow().isoformat(),
                "total_messages": 0,
                "longest_streak": 0
            }

        bucket = self.xp_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return

        base_xp = random.randint(15, 25)
        multiplier = self.get_xp_multiplier(message.author)

        if user_id in self.boost_events and datetime.utcnow() < self.boost_events[user_id]:
            multiplier *= 2

        xp_gain = int(base_xp * multiplier)

        if len(message.content) > 100:
            xp_gain += 5

        self.levels[user_id]["xp"] += xp_gain
        self.levels[user_id]["last_message"] = datetime.utcnow().isoformat()
        self.levels[user_id]["total_messages"] = self.levels[user_id].get(
            "total_messages", 0) + 1

        current_level = self.get_level_from_xp(self.levels[user_id]["xp"])
        if current_level > self.levels[user_id]["level"]:
            self.levels[user_id]["level"] = current_level
            await self.level_up(message.author, message.channel, current_level)
            await self.check_and_assign_role_rewards(message.author, current_level)

    async def check_and_assign_role_rewards(self, member: discord.Member, level: int):
        """Check and assign role rewards for level ups"""
        for req_level, role_name in LevelRewards.ROLES.items():
            if level >= req_level:
                role = discord.utils.get(member.guild.roles, name=role_name)
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role)
                        await self.send_role_reward_notification(member, role)
                    except discord.Forbidden:
                        logger.error(f"Cannot assign role {
                                     role_name} to {member}")

    async def send_role_reward_notification(self, member: discord.Member, role: discord.Role):
        """Send notification for new role rewards"""
        embed = discord.Embed(
            title="🎭 New Role Unlocked! 🎭",
            description=f"Congratulations {
                member.mention}! You've earned the {role.name} role!",
            color=role.color
        )
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            pass

    async def update_streak(self, user: discord.Member):
        """Update user's message streak"""
        user_id = str(user.id)
        now = datetime.utcnow()

        if user_id not in self.streaks:
            self.streaks[user_id] = {
                "current_streak": 1,
                "last_active": now.isoformat(),
                "longest_streak": 1
            }
            return

        last_active = datetime.fromisoformat(
            self.streaks[user_id]["last_active"])
        days_difference = (now - last_active).days

        if days_difference == 1:
            self.streaks[user_id]["current_streak"] += 1
            self.streaks[user_id]["longest_streak"] = max(
                self.streaks[user_id]["current_streak"],
                self.streaks[user_id]["longest_streak"]
            )
        elif days_difference > 1:
            self.streaks[user_id]["current_streak"] = 1

        self.streaks[user_id]["last_active"] = now.isoformat()

        streak = self.streaks[user_id]["current_streak"]
        if streak in [7, 30, 100, 365]:
            await self.reward_streak_milestone(user, streak)

    async def reward_streak_milestone(self, user: discord.Member, streak: int):
        """Reward users for reaching streak milestones"""
        rewards = {
            7: {"xp": 1000, "karma": 100},
            30: {"xp": 5000, "karma": 500},
            100: {"xp": 20000, "karma": 2000},
            365: {"xp": 100000, "karma": 10000}
        }

        if streak in rewards:
            user_id = str(user.id)
            reward = rewards[streak]

            self.levels[user_id]["xp"] += reward["xp"]
            self.karma[user_id] = self.karma.get(user_id, 0) + reward["karma"]

            embed = discord.Embed(
                title="🎯 Streak Milestone Reached! 🎯",
                description=f"Amazing {user.mention}! You've maintained a {
                    streak}-day streak!",
                color=discord.Color.gold()
            )
            embed.add_field(name="Rewards", value=f"XP: {
                            reward['xp']}\nKarma: {reward['karma']}")

            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.command()
    async def rank(self, ctx, member: discord.Member = None):
        """Display rank information for a user"""
        member = member or ctx.author
        user_id = str(member.id)

        if user_id not in self.levels:
            await ctx.send(f"{member.mention} hasn't earned any XP yet!")
            return

        level_data = self.levels[user_id]
        current_level = level_data["level"]
        current_xp = level_data["xp"]
        next_level_xp = self.get_level_xp(current_level)

        embed = discord.Embed(
            title=f"📊 {member.name}'s Rank",
            color=member.color
        )
        embed.add_field(name="Level", value=str(current_level), inline=True)
        embed.add_field(name="XP", value=f"{
                        current_xp:,}/{next_level_xp:,}", inline=True)
        embed.add_field(
            name="Total Messages",
            value=str(level_data.get("total_messages", 0)),
            inline=True
        )

        if user_id in self.streaks:
            streak_data = self.streaks[user_id]
            embed.add_field(
                name="Current Streak",
                value=f"{streak_data['current_streak']} days",
                inline=True
            )

        embed.set_thumbnail(
            url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx, category: str = "xp", page: int = 1):
        """Display server leaderboard"""
        valid_categories = ["xp", "streak", "karma", "messages"]
        if category not in valid_categories:
            await ctx.send(f"Invalid category! Choose from: {', '.join(valid_categories)}")
            return

        if page < 1:
            page = 1

        items_per_page = 10
        start_idx = (page - 1) * items_per_page

        if category == "xp":
            data = [(uid, data["xp"]) for uid, data in self.levels.items()]
            title = "XP Leaderboard"
        elif category == "streak":
            data = [(uid, data["current_streak"])
                    for uid, data in self.streaks.items()]
            title = "Streak Leaderboard"
        elif category == "karma":
            data = list(self.karma.items())
            title = "Karma Leaderboard"
        else:  # messages
            data = [(uid, data["total_messages"])
                    for uid, data in self.levels.items()]
            title = "Messages Leaderboard"

        sorted_data = sorted(data, key=lambda x: x[1], reverse=True)
        total_pages = (len(sorted_data) + items_per_page - 1) // items_per_page

        if page > total_pages:
            await ctx.send(f"Invalid page number! Total pages: {total_pages}")
            return

        embed = discord.Embed(
            title=f"🏆 {title} (Page {page}/{total_pages})",
            color=discord.Color.gold()
        )

        for i, (user_id, value) in enumerate(sorted_data[start_idx:start_idx + items_per_page], start=start_idx + 1):
            member = ctx.guild.get_member(int(user_id))
            if member:
                embed.add_field(
                    name=f"{i}. {member.name}",
                    value=f"{value:,}",
                    inline=False
                )

        embed.set_footer(text=f"Use {ctx.prefix}leaderboard {
                         category} <page> to view more")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_xp(self, ctx, member: discord.Member, amount: int):
        """Add XP to a user (Admin only)"""
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return

        user_id = str(member.id)
        if user_id not in self.levels:
            self.levels[user_id] = {
                "xp": 0,
                "level": 0,
                "last_message": datetime.utcnow().isoformat(),
                "total_messages": 0
            }

        self.levels[user_id]["xp"] += amount
        current_level = self.get_level_from_xp(self.levels[user_id]["xp"])

        if current_level > self.levels[user_id]["level"]:
            self.levels[user_id]["level"] = current_level
            await self.level_up(member, ctx.channel, current_level)
            await self.check_and_assign_role_rewards(member, current_level)

        await ctx.send(f"Added {amount} XP to {member.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def remove_xp(self, ctx, member: discord.Member, amount: int):
        """Remove XP from a user (Admin only)"""
        if amount <= 0:
            await ctx.send("Amount must be positive!")
            return

        user_id = str(member.id)
        if user_id not in self.levels:
            await ctx.send(f"{member.mention} has no XP to remove!")
            return

        self.levels[user_id]["xp"] = max(
            0, self.levels[user_id]["xp"] - amount)
        new_level = self.get_level_from_xp(self.levels[user_id]["xp"])
        self.levels[user_id]["level"] = new_level

        await ctx.send(f"Removed {amount} XP from {member.mention}")

    @commands.command()
    async def daily(self, ctx):
        """View daily tasks"""
        user_id = str(ctx.author.id)
        if user_id not in self.tasks:
            self.tasks[user_id] = self.generate_daily_tasks()

        task_data = self.tasks[user_id]
        embed = discord.Embed(
            title="📋 Daily Tasks",
            description="Complete these tasks to earn rewards!",
            color=discord.Color.blue()
        )

        for i, task in enumerate(task_data["tasks"], 1):
            status = "✅" if task["completed"] else "❌"
            description = f"Goal: {task['goal']} {
                task['type']}\nReward: {task['reward']} XP"
            embed.add_field(
                name=f"Task {i} {status}",
                value=description,
                inline=False
            )

        embed.set_footer(text="Tasks reset daily at midnight UTC")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reset_user(self, ctx, member: discord.Member):
        """Reset all data for a user (Admin only)"""
        user_id = str(member.id)

        self.levels.pop(user_id, None)
        self.achievements.pop(user_id, None)
        self.tasks.pop(user_id, None)
        self.karma.pop(user_id, None)
        self.streaks.pop(user_id, None)
        self.boost_events.pop(user_id, None)

        await self.save_all_data()
        await ctx.send(f"Reset all data for {member.mention}")

    @commands.command()
    async def stats(self, ctx):
        """Display bot statistics"""
        total_users = len(self.levels)
        total_messages = sum(data.get("total_messages", 0)
                             for data in self.levels.values())
        total_xp = sum(data["xp"] for data in self.levels.values())

        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(name="Total Users", value=str(
            total_users), inline=True)
        embed.add_field(name="Total Messages", value=f"{
                        total_messages:,}", inline=True)
        embed.add_field(name="Total XP", value=f"{total_xp:,}", inline=True)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LevelsCog(bot))
