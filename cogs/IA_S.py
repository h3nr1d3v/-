import discord
from discord.ext import commands
import openai
import os
import requests
from io import BytesIO
from PIL import Image


class IA_S(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")
        self.conversation_history = {}

    @commands.command()
    async def ask(self, ctx, *, question):
        """
        Ask a question to ChatGPT
        Usage: !ask <your question>
        """
        try:
            user_id = ctx.author.id
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            self.conversation_history[user_id].append(
                {"role": "user", "content": question})

            response = openai.ChatCompletion.create(
                api_key=self.openai_api_key,
                model="gpt-3.5-turbo",
                messages=self.conversation_history[user_id],
                max_tokens=150
            )
            answer = response.choices[0].message['content'].strip()
            self.conversation_history[user_id].append(
                {"role": "assistant", "content": answer})

            # Limit conversation history to last 10 messages
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]

            embed = discord.Embed(title="ChatGPT Response",
                                  description=answer, color=discord.Color.green())
            embed.set_footer(text=f"Asked by {ctx.author.name}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred with ChatGPT: {str(e)}")

    @commands.command()
    async def clear_chat(self, ctx):
        """
        Clear your conversation history with ChatGPT
        Usage: !clear_chat
        """
        user_id = ctx.author.id
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            await ctx.send("Your conversation history has been cleared.")
        else:
            await ctx.send("You don't have any conversation history to clear.")

    @commands.command()
    async def generate_image(self, ctx, *, prompt):
        """
        Generate an image using StabilityAI
        Usage: !generate_image <your prompt>
        """
        try:
            url = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

            headers = {
                "Accept": "image/*",
                "Authorization": f"Bearer {self.stability_api_key}"
            }

            files = {
                "prompt": (None, prompt),
                "output_format": (None, "png"),
            }

            async with ctx.typing():
                response = requests.post(url, headers=headers, files=files)

                if response.status_code == 200:
                    image = Image.open(BytesIO(response.content))
                    with BytesIO() as image_binary:
                        image.save(image_binary, 'PNG')
                        image_binary.seek(0)
                        await ctx.send(file=discord.File(fp=image_binary, filename='generated_image.png'))
                else:
                    await ctx.send(f"Error generating image: {response.text}")
        except Exception as e:
            await ctx.send(f"An error occurred with StabilityAI: {str(e)}")

    @commands.command()
    async def analyze_image(self, ctx, image_url: str):
        """
        Analyze an image using OpenAI's GPT-4 Vision
        Usage: !analyze_image <image_url>
        """
        try:
            response = openai.ChatCompletion.create(
                api_key=self.openai_api_key,
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What's in this image?"},
                            {"type": "image_url", "image_url": image_url},
                        ],
                    }
                ],
                max_tokens=300,
            )

            analysis = response.choices[0].message['content'].strip()
            embed = discord.Embed(title="Image Analysis",
                                  description=analysis, color=discord.Color.blue())
            embed.set_image(url=image_url)
            embed.set_footer(text=f"Analyzed for {ctx.author.name}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred with GPT-4 Vision: {str(e)}")


def setup(bot):
    bot.add_cog(IA_S(bot))
