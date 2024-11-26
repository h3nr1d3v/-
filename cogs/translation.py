import discord
from discord.ext import commands
from googletrans import Translator, LANGUAGES
import asyncio


class Translation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        self.language_cache = {}

    @commands.command()
    async def translate(self, ctx, lang, *, text):
        """Translate text to a specified language"""
        try:
            lang = lang.lower()
            if lang not in LANGUAGES:
                closest_match = self.find_closest_language(lang)
                if closest_match:
                    confirm_msg = await ctx.send(f"Did you mean '{closest_match}' ({LANGUAGES[closest_match]})? React with ✅ to confirm or ❌ to cancel.")
                    await confirm_msg.add_reaction('✅')
                    await confirm_msg.add_reaction('❌')

                    def check(reaction, user):
                        return user == ctx.author and str(reaction.emoji) in ['✅', '❌']

                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                    except asyncio.TimeoutError:
                        await confirm_msg.delete()
                        await ctx.send("Translation cancelled due to timeout.")
                        return
                    else:
                        if str(reaction.emoji) == '✅':
                            lang = closest_match
                        else:
                            await ctx.send("Translation cancelled.")
                            return
                else:
                    await ctx.send("Invalid language code. Use `!languages` to see available languages.")
                    return

            translated = self.translator.translate(text, dest=lang)
            embed = discord.Embed(title="Translation",
                                  color=discord.Color.blue())
            embed.add_field(name="Original", value=text, inline=False)
            embed.add_field(
                name=f"Translated to {LANGUAGES[lang]}", value=translated.text, inline=False)
            embed.set_footer(
                text=f"Translated from {LANGUAGES[translated.src]} to {LANGUAGES[lang]}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    async def languages(self, ctx):
        """List available language codes"""
        lang_list = [f"{code}: {name}" for code, name in LANGUAGES.items()]
        lang_chunks = [lang_list[i:i + 20]
                       for i in range(0, len(lang_list), 20)]

        for i, chunk in enumerate(lang_chunks):
            embed = discord.Embed(title=f"Available Languages (Page {i+1}/{len(lang_chunks)})",
                                  description="\n".join(chunk),
                                  color=discord.Color.blue())
            await ctx.send(embed=embed)

    @commands.command()
    async def detect(self, ctx, *, text):
        """Detect the language of the given text"""
        try:
            detection = self.translator.detect(text)
            await ctx.send(f"Detected language: {LANGUAGES[detection.lang]} (Confidence: {detection.confidence:.2f})")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    def find_closest_language(self, input_lang):
        if not self.language_cache:
            self.language_cache = {
                lang.lower(): code for code, lang in LANGUAGES.items()}

        input_lang = input_lang.lower()
        if input_lang in self.language_cache:
            return self.language_cache[input_lang]

        for lang, code in self.language_cache.items():
            if input_lang in lang or lang in input_lang:
                return code

        return None


async def setup(bot):
    await bot.add_cog(TranslationCog(bot))
