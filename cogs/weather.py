import discord
import aiohttp
import os
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="天氣", description="查詢城市天氣")
    async def weather(self, interaction: discord.Interaction, 城市: str):
        API_KEY = os.getenv('WEATHER_API_KEY')
        url = f"http://api.openweathermap.org/data/2.5/weather?q={城市}&appid={API_KEY}&units=metric&lang=zh_tw"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

        if data["cod"] != 200:
            return await interaction.response.send_message("查詢失敗")
        
        logger = self.bot.get_cog('Logger')
        if logger:
            logger.log_weather_query(
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id) if interaction.guild else "DM",
                city=城市,
                temp=data['main']['temp'],
                description=data["weather"][0]["description"]
            )
            
        embed = discord.Embed(
            title=f"{data['name']} 天氣",
            color=discord.Color.blue()
        )
        embed.add_field(name="溫度", value=f"{data['main']['temp']}°C")
        embed.add_field(name="天氣狀況", value=data["weather"][0]["description"])
        embed.add_field(name="濕度", value=f"{data['main']['humidity']}%")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Weather(bot))