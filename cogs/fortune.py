import discord, datetime, os, random, json
from discord.ext import commands
from discord import app_commands

class Fortune(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        current_dir = os.path.dirname(os.path.realpath(__file__))
        json_file_path = os.path.join(current_dir, '../json/fortune.json')

        with open(json_file_path, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)

        self.fortune_items = data["fortune_items"]
        
    #Fortune
    @app_commands.command(name="fortune", description="抽運勢")
    async def fortune(self, interaction: discord.Interaction):
        selected_fortune = random.choice(self.fortune_items)
        # 提及使用者
        user_mention = interaction.user.mention
        
        embed = discord.Embed(
            title="今日運勢",
            description=f"{user_mention}{selected_fortune}",
            color=0x3498db,  # 可以自訂顏色
            timestamp = datetime.datetime.now()
        )
        
        logger = self.bot.get_cog('Logger')
        if logger:
            logger.log_fortune_command(
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id) if interaction.guild else "DM",
                fortune_result=str(selected_fortune)
            )
            
        await interaction.response.send_message(embed=embed)
        
async def setup(bot):
    await bot.add_cog(Fortune(bot))