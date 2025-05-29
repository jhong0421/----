import discord, os
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

ALLOWED_USERS = os.getenv("OWNER_ID")

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="設置狀態",
        description="變更機器人狀態"
    )
    @app_commands.describe(
        狀態類型="狀態類型",
        狀態文字="要顯示的狀態文字"
    )
    @app_commands.choices(  # 新增下拉選單選項
        狀態類型=[
            app_commands.Choice(name="正在玩", value="playing"),
            app_commands.Choice(name="正在聽", value="listening"),
            app_commands.Choice(name="正在看", value="watching")
        ]
    )
    async def set_status(
        self,
        interaction: discord.Interaction,
        狀態類型: app_commands.Choice[str],  # 修改參數類型
        狀態文字: str
    ):
        # 權限檢查
        if interaction.user.id not in ALLOWED_USERS:
            return await interaction.response.send_message(
                "⚠️ 你沒有權限使用此指令！",
                ephemeral=True
            )

        # 從選項獲取值
        status_type = 狀態類型.value
        
        # 狀態類型映射
        activity = None
        match status_type:
            case "playing":
                activity = discord.Game(name=狀態文字)
            case "listening":
                activity = discord.Activity(
                    type=discord.ActivityType.listening,
                    name=狀態文字
                )
            case "watching":
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=狀態文字
                )

        # 更新狀態並回應
        await self.bot.change_presence(activity=activity)
        await interaction.response.send_message(
            f"✅ 機器人狀態已更新為 **{狀態類型.name} {狀態文字}**"
        )

        # 記錄日誌
        logger = self.bot.get_cog("Logger")
        if logger:
            logger.log_setstatus_command(
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id) if interaction.guild else "DM",
                status_type=str(狀態類型.name),
                status_text=str(狀態文字)
            )

async def setup(bot):
    await bot.add_cog(Status(bot))