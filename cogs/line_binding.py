import discord
from discord.ext import commands
from discord import app_commands
from event.logger import Logger
from database.databaseshare import DB

class LineBindingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = Logger(bot)
        self.db = DB()

    @app_commands.command(name="bind_line", description="綁定您的Line使用者ID至您的Discord帳戶")
    async def bind_line(self, interaction: discord.Interaction, line_user_id: str):
        try:
            discord_user_id = interaction.user.id
            with self.db.get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO user_line_mapping (user_id, line_user_id)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET line_user_id=excluded.line_user_id
                """, (discord_user_id, line_user_id))
                
            # 記錄日誌
            await self.logger.log_basic_command(
                str(discord_user_id),
                str(interaction.guild.id) if interaction.guild else 'DM',
                "bind_line",
                f"綁定Line ID: {line_user_id}"
            )
            
            await interaction.response.send_message(
                f"✅ 已成功綁定Line ID: {line_user_id}",
                ephemeral=True
            )
            
        except Exception as e:
            await self.logger.log_error(
                str(interaction.user.id),
                str(interaction.guild.id) if interaction.guild else 'DM',
                "LINE_BIND_ERROR",
                str(e)
            )
            await interaction.response.send_message(
                f"❌ 綁定失敗：{str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(LineBindingCog(bot))