import discord
from discord.ext import commands
from discord import app_commands

class LineUserIdCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="get_line_user_id", description="取得您的Line使用者ID")
    async def get_line_user_id(self, interaction: discord.Interaction):
        user = interaction.user
        link = "https://liff.line.me/1645278921-kWRPP32q/?accountId=928vblqc"

        try:
            await user.send(f"點擊這個連結以獲得您的Line使用者ID: {link}")
            await interaction.response.send_message("好的,我已經查看了您私人傳送的訊息,謝謝您提供連結。我已經收到了訊息。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("了解,我已經檢查並確認我的直接訊息功能已啟用。如果您仍然無法發送連結,請再次嘗試。我會持續等待您提供連結。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(LineUserIdCog(bot))