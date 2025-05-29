import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from pathlib import Path

class ChannelConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {}  # 儲存頻道配置 {guild_id: {"oil_price": channel_id, "stop_work": channel_id}}
        
        # 確保 db 目錄存在
        db_path = Path("db")
        db_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化資料庫
        self.db_path = db_path / "cconfig.db"
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self):
        """初始化資料庫表格"""
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_config (
            guild_id INTEGER PRIMARY KEY,
            oil_price_channel INTEGER,
            stop_work_channel INTEGER
        )
        """)
        self.conn.commit()

    async def save_config(self):
        """將當前配置保存到資料庫"""
        cursor = self.conn.cursor()
        
        # 清空現有資料
        cursor.execute("DELETE FROM channel_config")
        
        # 插入新資料
        for guild_id, channels in self.config.items():
            cursor.execute(
                "INSERT INTO channel_config (guild_id, oil_price_channel, stop_work_channel) VALUES (?, ?, ?)",
                (
                    guild_id,
                    channels.get("oil_price"),
                    channels.get("stop_work")
                )
            )
        
        self.conn.commit()

    async def load_config(self):
        """從資料庫載入配置"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT guild_id, oil_price_channel, stop_work_channel FROM channel_config")
        
        self.config.clear()  # 清空當前配置
        
        for row in cursor.fetchall():
            guild_id, oil_price_channel, stop_work_channel = row
            self.config[guild_id] = {}
            
            if oil_price_channel:
                self.config[guild_id]["oil_price"] = oil_price_channel
            if stop_work_channel:
                self.config[guild_id]["stop_work"] = stop_work_channel

    def cog_unload(self):
        """Cog卸載時關閉資料庫連接"""
        self.conn.close()

    @app_commands.command(name="setup", description="設定自動通知的頻道")
    @app_commands.describe(
        notification_type="選擇要設定的通知類型",
        channel="選擇要發送通知的頻道"
    )
    @app_commands.choices(
        notification_type=[
            app_commands.Choice(name="油價通知", value="oil_price"),
            app_commands.Choice(name="停班停課通知", value="stop_work"),
        ]
    )
    async def setup_notification_channel(
        self,
        interaction: discord.Interaction,
        notification_type: app_commands.Choice[str],
        channel: discord.TextChannel
    ):
        guild_id = interaction.guild_id
        if guild_id not in self.config:
            self.config[guild_id] = {}

        self.config[guild_id][notification_type.value] = channel.id
        await self.save_config()

        await interaction.response.send_message(
            f"已設定 {channel.mention} 為 {notification_type.name} 的發送頻道",
            ephemeral=True
        )

    def get_channel_id(self, guild_id, notification_type):
        """取得指定伺服器和通知類型的頻道ID"""
        if guild_id in self.config and notification_type in self.config[guild_id]:
            return self.config[guild_id][notification_type]
        return None

async def setup(bot):
    cog = ChannelConfigCog(bot)
    await bot.add_cog(cog)
    # 載入已保存的配置
    await cog.load_config()