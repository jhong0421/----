import discord, os
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

ALLOWED_USERS = os.getenv("OWNER_ID")

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="測試機器人延遲")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"延遲：{latency}ms",
            color=discord.Color.green()
        )
        
        logger = self.bot.get_cog('Logger')
        if logger:
            logger.log_basic_command(
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild.id) if interaction.guild else "DM",
                command_type="ping",
                latency=round(self.bot.latency * 1000)
            )
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="顯示所有可用指令")
    async def help(self, interaction: discord.Interaction):
        # 第一個 Embed (基本指令)
        embed1 = discord.Embed(
            title="📚 指令幫助 (1/2)",
            description="以下是所有可用的指令:",
            color=discord.Color.blue()
        )
        
        commands_list1 = [
            ("/help", "查看所有指令！"),
            ("/weather <地點>", "查詢各大縣市的天氣情況"),
            ("/deepseek <問題>", "使用DeepSeek V3進行AI問答"),
            ("/fortune", "抽出你的運勢"),
            ("/21點", "遊玩21點小遊戲"),
            ("/ping", "查看機器人延遲"),
            ("/setup <通知類別> <指定頻道>", "指定油價和停班停課自動通知的頻道"),
            ("/join", "讓機器人加入語音頻道"),
            ("/leave", "讓機器人離開語音頻道"),
            ("/play <url>", "播放YouTube音樂 (音樂播放器目前還在修正中)"),
            ("/loop", "切換循環播放模式 (off/one/all)"),
            ("/volume <數字>", "調整音樂播放音量"),
            ("/queue", "顯示目前的音樂清單"),
            ("/nowplaying", "顯示目前播放的歌曲"),
            ("/lyrics <歌手+歌曲>", "獲取歌詞"),
            ("/pause", "暫停音樂"),
            ("/resume", "繼續播放音樂"),
            ("/skip", "跳過目前播放的音樂"),
            ("/stop", "停止播放音樂"),
            ("/clearqueue", "清除播放清單"),
            ("/股票查詢 <股票代碼>", "查詢股票"),
            ("/股票最愛清單", "查詢自己的股票最愛清單"),
            ("/加股票最愛", "將股票代碼加入最愛清單"),
            ("/移除股票最愛項目", "將股票代碼從最愛清單中移除"),
            ("/股票最愛一覽", "顯示所有股票最愛清單的股票資訊")
        ]
        
        for cmd, desc in commands_list1:
            embed1.add_field(name=cmd, value=desc, inline=False)
        
        # 第二個 Embed (Line相關指令)
        embed2 = discord.Embed(
            title="📚 指令幫助 (2/2)",
            color=discord.Color.blue()
        )
        
        commands_list2 = [
            ("/get_line_user_id", "獲取Line ID"),
            ("/bind_line <Line ID>", "綁定DC與Line的ID")
        ]
        
        for cmd, desc in commands_list2:
            embed2.add_field(name=cmd, value=desc, inline=False)
            
        embed1.set_footer(text="輸入指令前請加上斜線 '/'")
        embed2.set_footer(text="輸入指令前請加上斜線 '/'")
        
        # 先回覆第一個Embed
        await interaction.response.send_message(embed=embed1)
        # 再發送第二個Embed
        await interaction.followup.send(embed=embed2)

async def setup(bot):
    await bot.add_cog(Basic(bot))