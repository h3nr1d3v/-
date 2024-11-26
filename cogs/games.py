import discord
from discord.ext import commands
import random
import asyncio
import json
import os
import aiohttp
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Games(commands.Cog, name="Games"):
    """🎮 Fun games to play with the bot!"""

    def __init__(self, bot):
        self.bot = bot
        self.trivia_questions = self.load_trivia_questions()
        self.hangman_words = self.load_hangman_words()
        self.user_scores = self.load_user_scores()
        self.active_games: Dict[int, Dict[str, Any]] = {}
        self.cooldowns: Dict[int, Dict[str, datetime]] = {}
        # Image manager attributes
        self.session: Optional[aiohttp.ClientSession] = None
        self.image_cache = {}
        self.cache_expiry = {}

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

    async def close_session(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    def load_trivia_questions(self) -> List[Dict[str, str]]:
        """Load trivia questions from JSON file or return defaults."""
        try:
            with open('data/trivia_questions.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return [
                {
                    "question": "What is the capital of Spain?",
                    "answer": "Madrid",
                    "category": "Geography"
                },
                {
                    "question": "Who painted 'The Starry Night'?",
                    "answer": "Vincent van Gogh",
                    "category": "Art"
                },
                {
                    "question": "When did World War II begin?",
                    "answer": "1939",
                    "category": "History"
                }
            ]

    def load_hangman_words(self) -> List[str]:
        """Load hangman words from file or return defaults."""
        try:
            with open('data/hangman_words.txt', 'r', encoding='utf-8') as f:
                return [word.strip().lower() for word in f.readlines()]
        except FileNotFoundError:
            return ["python", "discord", "gaming", "programming", "computer", "internet", "technology"]

    def save_user_scores(self) -> None:
        """Save user scores to JSON file."""
        os.makedirs('data', exist_ok=True)
        with open('data/user_scores.json', 'w', encoding='utf-8') as f:
            json.dump(self.user_scores, f, indent=4)

    def load_user_scores(self) -> Dict[str, int]:
        """Load user scores from JSON file."""
        try:
            with open('data/user_scores.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def check_cooldown(self, user_id: int, game: str, cooldown_seconds: int = 30) -> bool:
        """Check if user is in cooldown for a specific game."""
        if user_id not in self.cooldowns:
            self.cooldowns[user_id] = {}

        if game in self.cooldowns[user_id]:
            last_played = self.cooldowns[user_id][game]
            if datetime.now() - last_played < timedelta(seconds=cooldown_seconds):
                return False

        self.cooldowns[user_id][game] = datetime.now()
        return True

    @commands.command(name="rps")
    async def rps(self, ctx, choice: str):
        """🎮 Play Rock, Paper, Scissors

        Usage: !rps <rock|paper|scissors>
        Example: !rps rock"""

        if not self.check_cooldown(ctx.author.id, "rps"):
            return await ctx.send("⏰ Please wait before playing again.")

        choices = {
            "rock": "🪨",
            "paper": "📄",
            "scissors": "✂️"
        }

        choice = choice.lower()
        if choice not in choices:
            return await ctx.send("❌ Invalid choice. Please choose: rock, paper, or scissors.")

        bot_choice = random.choice(list(choices.keys()))

        embed = discord.Embed(
            title="🎮 Rock, Paper, Scissors",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Your Choice",
            value=f"{choices[choice]} {choice.capitalize()}",
            inline=True
        )
        embed.add_field(
            name="Bot's Choice",
            value=f"{choices[bot_choice]} {bot_choice.capitalize()}",
            inline=True
        )

        if choice == bot_choice:
            result = "🤝 It's a tie!"
        elif (
            (choice == "rock" and bot_choice == "scissors") or
            (choice == "paper" and bot_choice == "rock") or
            (choice == "scissors" and bot_choice == "paper")
        ):
            result = "🎉 You win!"
            self.update_score(ctx.author.id, 2)
        else:
            result = "😢 You lose!"

        embed.add_field(name="Result", value=result, inline=False)

        # Add anime reaction image
        image_url = await self.get_random_image()
        embed.set_image(url=image_url)

        await ctx.send(embed=embed)

    @commands.command(name="guess")
    async def guess(self, ctx):
        """🔢 Guess the number between 1 and 100

        The bot will think of a number and you have 6 tries to guess it."""

        if not self.check_cooldown(ctx.author.id, "guess"):
            return await ctx.send("⏰ Please wait before playing again.")

        number = random.randint(1, 100)
        attempts = []

        embed = discord.Embed(
            title="🎲 Number Guessing Game",
            description="I'm thinking of a number between 1 and 100.\nYou have 6 tries to guess it.",
            color=discord.Color.green()
        )

        # Add anime reaction image
        image_url = await self.get_random_image()
        embed.set_image(url=image_url)

        await ctx.send(embed=embed)

        for i in range(6):
            def check(m):
                return (
                    m.author == ctx.author and
                    m.channel == ctx.channel and
                    m.content.isdigit() and
                    1 <= int(m.content) <= 100
                )

            try:
                guess = await self.bot.wait_for('message', check=check, timeout=30.0)
                guess_num = int(guess.content)
                attempts.append(guess_num)
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The number was {number}.")
                return
            except ValueError:
                await ctx.send("❌ Please enter a valid number between 1 and 100.")
                continue

            if guess_num == number:
                points = 6 - i
                self.update_score(ctx.author.id, points)

                embed = discord.Embed(
                    title="🎉 Congratulations!",
                    description=f"You guessed the number in {
                        i+1} tries.\nYou earned {points} points!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Attempts",
                                value=", ".join(map(str, attempts)))

                # Add anime reaction image
                image_url = await self.get_random_image()
                embed.set_image(url=image_url)

                await ctx.send(embed=embed)
                return

            hint = "📈 Higher!" if guess_num < number else "📉 Lower!"
            await ctx.send(f"{hint} You have {5-i} tries left.")

        await ctx.send(f"❌ Out of tries! The number was {number}.")

    @commands.command(name="trivia")
    async def trivia(self, ctx):
        """❓ Play a round of trivia

        Answer correctly to earn points."""

        if not self.check_cooldown(ctx.author.id, "trivia"):
            return await ctx.send("⏰ Please wait before playing again.")

        question = random.choice(self.trivia_questions)

        embed = discord.Embed(
            title="🎯 Trivia Time!",
            description=question['question'],
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Category",
            value=question.get('category', 'General'),
            inline=False
        )
        embed.set_footer(text="You have 30 seconds to answer")

        # Add anime reaction image
        image_url = await self.get_random_image()
        embed.set_image(url=image_url)

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            answer = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Time's up! The answer was: {question['answer']}")
            return

        if answer.content.lower() == question['answer'].lower():
            self.update_score(ctx.author.id, 3)

            embed = discord.Embed(
                title="✅ Correct!",
                description="You earned 3 points!",
                color=discord.Color.green()
            )

            # Add anime reaction image
            image_url = await self.get_random_image()
            embed.set_image(url=image_url)

            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Incorrect!",
                description=f"The correct answer was: {question['answer']}",
                color=discord.Color.red()
            )

            # Add anime reaction image
            image_url = await self.get_random_image()
            embed.set_image(url=image_url)

            await ctx.send(embed=embed)

    @commands.command(name="hangman")
    async def hangman(self, ctx):
        """🎯 Play Hangman

        Guess the word letter by letter before the drawing is complete."""

        if not self.check_cooldown(ctx.author.id, "hangman"):
            return await ctx.send("⏰ Please wait before playing again.")

        word = random.choice(self.hangman_words)
        guessed = set()
        tries = 6
        hangman_stages = [
            "```\n  +---+\n      |\n      |\n      |\n     ===```",
            "```\n  +---+\n  O   |\n      |\n      |\n     ===```",
            "```\n  +---+\n  O   |\n  |   |\n      |\n     ===```",
            "```\n  +---+\n  O   |\n /|   |\n      |\n     ===```",
            "```\n  +---+\n  O   |\n /|\\  |\n      |\n     ===```",
            "```\n  +---+\n  O   |\n /|\\  |\n /    |\n     ===```",
            "```\n  +---+\n  O   |\n /|\\  |\n / \\  |\n     ===```"
        ]

        def display_word():
            return ' '.join(letter if letter in guessed else '_' for letter in word)

        embed = discord.Embed(
            title="🎯 Hangman",
            description="Guess the word letter by letter!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Word", value=f"```{
                        display_word()}```", inline=False)
        embed.add_field(name="Tries Left", value=str(tries), inline=True)
        embed.add_field(name="Letters Used", value=", ".join(
            sorted(guessed)) or "None", inline=True)
        embed.add_field(
            name="Status", value=hangman_stages[6-tries], inline=False)

        # Add anime reaction image
        image_url = await self.get_random_image()
        embed.set_image(url=image_url)

        game_message = await ctx.send(embed=embed)

        while tries > 0:
            def check(m):
                return (
                    m.author == ctx.author and
                    m.channel == ctx.channel and
                    len(m.content) == 1 and
                    m.content.isalpha()
                )

            try:
                guess = await self.bot.wait_for('message', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Time's up! The word was: {word}")
                return

            letter = guess.content.lower()

            if letter in guessed:
                await ctx.send("❌ You already tried that letter!")
                continue

            guessed.add(letter)

            if letter in word:
                await ctx.send("✅ Correct letter!")
            else:
                tries -= 1
                await ctx.send("❌ Wrong letter!")

            embed.clear_fields()
            embed.add_field(name="Word", value=f"```{
                            display_word()}```", inline=False)
            embed.add_field(name="Tries Left", value=str(tries), inline=True)
            embed.add_field(name="Letters Used", value=", ".join(
                sorted(guessed)), inline=True)
            embed.add_field(
                name="Status", value=hangman_stages[6-tries], inline=False)

            # Update anime reaction image
            image_url = await self.get_random_image()
            embed.set_image(url=image_url)

            await game_message.edit(embed=embed)

            if all(letter in guessed for letter in word):
                points = tries + 1
                self.update_score(ctx.author.id, points)

                embed = discord.Embed(
                    title="🎉 Congratulations!",
                    description=f"You won {
                        points} points!\nThe word was: {word}",
                    color=discord.Color.gold()
                )

                # Add anime reaction image
                image_url = await self.get_random_image()
                embed.set_image(url=image_url)

                await ctx.send(embed=embed)
                return

        await ctx.send(f"❌ Game Over! The word was: {word}")

    @commands.command(name="leaderboard", aliases=["top", "ranking"])
    async def leaderboard(self, ctx):
        """📊 Show the games leaderboard

        View the top players and their scores."""

        if not self.user_scores:
            return await ctx.send("❌ No scores recorded yet.")

        sorted_scores = sorted(
            self.user_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        embed = discord.Embed(
            title="🏆 Leaderboard",
            color=discord.Color.gold()
        )

        medals = {
            0: "🥇",
            1: "🥈",
            2: "🥉"
        }

        for i, (user_id, score) in enumerate(sorted_scores[:10]):
            user = self.bot.get_user(int(user_id))
            if user:
                medal = medals.get(i, "")
                embed.add_field(
                    name=f"{medal} #{i+1} {user.name}",
                    value=f"📊 Points: {score}",
                    inline=False
                )

        # Add anime reaction image
        image_url = await self.get_random_image()
        embed.set_image(url=image_url)

        await ctx.send(embed=embed)

    def update_score(self, user_id: int, points: int) -> None:
        """Update user's score and save to file."""
        user_id_str = str(user_id)
        if user_id_str not in self.user_scores:
            self.user_scores[user_id_str] = 0
        self.user_scores[user_id_str] += points
        self.save_user_scores()

    def cog_unload(self):
        """Clean up resources when the cog is unloaded."""
        asyncio.create_task(self.close_session())


def setup(bot):
    bot.add_cog(GamesCog(bot))
