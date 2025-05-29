import discord
from discord.ext import commands
from discord import app_commands

#
class SelectChannel(discord.ui.Select):
    def __init__(self, channels):
        # 將頻道名稱作為選項傳入下拉式選單
        options = [discord.SelectOption(label=channel.name, value=channel.id) for channel in channels if isinstance(channel, discord.TextChannel)]
        
        super().__init__(placeholder='選擇一個頻道...', min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        # 從下拉選單獲取頻道ID並傳送消息
        channel = self.view.bot.get_channel(int(self.values[0]))
        if channel:
            await channel.send(self.view.message_content)
            await interaction.response.send_message(f"訊息已經發送到頻道：{channel.name}", ephemeral=True)
        else:
            await interaction.response.send_message("找不到頻道", ephemeral=True)

class SendMessageView(discord.ui.View):
    def __init__(self, bot, channels, message_content):
        super().__init__()
        self.bot = bot
        self.message_content = message_content
        # 將選項加入下拉式選單
        self.add_item(SelectChannel(channels))

class Send(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="send", description="開始傳送訊息流程。")
    @app_commands.describe(message="要發送的消息內容")
    async def send_message(self, interaction: discord.Interaction, message: str):
        # 獲取伺服器中的所有文字頻道
        channels = [channel for channel in interaction.guild.channels if isinstance(channel, discord.TextChannel)]
        
        # 創建並發送一個包含下拉式選單的消息
        view = SendMessageView(self.bot, channels, message)
        await interaction.response.send_message("請從下拉式選單中選擇一個頻道來發送消息", view=view, ephemeral=True)


# Cog 載入 Bot 中
async def setup(bot: commands.Bot):
    await bot.add_cog(Send(bot))
    cog = Send(bot)
    for command in cog.get_commands():
            bot.add_listener(cog.log_command_usage, f'on_app_commands_{command.name}')
