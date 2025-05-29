import discord, os
from discord.ext import commands
from typing import List, Union
from discord.ext import commands
from datetime import datetime
from discord import Reaction, Member, User, Message  # 添加 Message 到導入列表

class Event(commands.Cog):
    now = datetime.now()
    formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_directory = r'./logs'  # 指定日誌文件的存儲目錄
        
    def log_event(self, message):
        """將事件訊息寫入日誌文件，每天一個檔案"""
        # 獲取當前日期並格式化為YYYY-MM-DD形式
        today_date = datetime.now().strftime('%Y-%m-%d')
        # 創建一個包含日期的日誌文件名
        log_file_name = f"log_{today_date}.txt"
        # 組合日誌文件的完整路徑
        log_file_path = os.path.join(self.log_directory, log_file_name)
        
        # 確保日誌目錄存在
        os.makedirs(self.log_directory, exist_ok=True)
        
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{formatted_time}]Bot 加入「{guild.name}」伺服器"
        print(log_message)
        self.log_event(log_message)
        
        
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{formatted_time}]Bot 離開「{guild.name}」伺服器"
        print(log_message)
        self.log_event(log_message)
    
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        if before.name != after.name:
            log_message = f"[{formatted_time}]伺服器更新名稱「{before.name} -> {after.name}」"
            print(log_message)
            self.log_event(log_message)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        # 使用伺服器的系統訊息頻道
        channel = member.guild.system_channel
        log_message = f"[{formatted_time}]「{member.mention}」加入「{member.guild.name}」伺服器"
        print(log_message)
        self.log_event(log_message)
        await channel.send(f"「{member.mention}」加入「{member.guild.name}」伺服器")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        # 使用伺服器的系統訊息頻道
        channel = member.guild.system_channel
        print(f"[{formatted_time}]「{member.mention}」離開「{member.guild.name}」伺服器")
        await channel.send(f"「{member.mention}」離開「{member.guild.name}」伺服器")

    
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        # 使用伺服器的系統訊息頻道
        channel = guild.system_channel
        log_message = f"[{formatted_time}]「{guild.name}」伺服器 Ban「{user.display_name}」"
        print(log_message)
        self.log_event(log_message)
        await channel.send(f"「{guild.name}」伺服器 Ban「{user.mention}」")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        channel = guild.system_channel  # 使用 guild 來取得 system_channel
        log_message = f"[{formatted_time}]「{guild.name}」伺服器 UnBan「{user.display_name}」"
        print(log_message)
        self.log_event(log_message)
        await channel.send(f"「{guild.name}」伺服器 UnBan「{user.mention}」")


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        if message.author == self.bot.user:
            return
        guild_name = message.guild.name if message.guild else '私人訊息'
        channel_name = message.channel.name if message.guild else '無頻道'
        
        # 檢查訊息中是否包含圖片或其他附件，並記錄訊息內容
        attachments_str = ", ".join([attachment.url for attachment in message.attachments]) if message.attachments else ""
        content = message.content + (f" (附件: {attachments_str})" if attachments_str else "")
        
        log_message = f"[{formatted_time}] 「{message.author.display_name}」在「{guild_name}」群組的「{channel_name}」頻道中發送訊息「{content}」"
        print(log_message)
        self.log_event(log_message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        guild_name = before.guild.name if before.guild else '私人訊息'
        channel_name = before.channel.name if before.guild else '無頻道'  # 修正此處，使用before
        
        # 獲取修改前後的附件 URLs
        before_attachments = ", ".join([attachment.url for attachment in before.attachments])
        after_attachments = ", ".join([attachment.url for attachment in after.attachments])
    
        # 如果有附件，加入到訊息内容中
        before_content = f"{before.content} (附件: {before_attachments})" if before_attachments else before.content
        after_content = f"{after.content} (附件: {after_attachments})" if after_attachments else after.content

        log_message = f"[{formatted_time}] 「{before.author.display_name}」在「{guild_name}」群組的「{channel_name}」頻道中更改訊息「{before_content}」 -> 「{after_content}」"
        print(log_message)
        self.log_event(log_message)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        guild_name = message.guild.name if message.guild else '私人訊息'
        channel_name = message.channel.name if message.guild else '無頻道'
        
        # 檢查訊息中是否包含圖片或其他附件，並記錄訊息內容
        attachments_str = ", ".join([attachment.url for attachment in message.attachments]) if message.attachments else ""
        content = message.content + (f" (附件: {attachments_str})" if attachments_str else "")
        
        log_message = f"[{formatted_time}] 「{message.author.display_name}」在「{guild_name}」群組的「{channel_name}」頻道中刪除訊息「{content}」"
        print(log_message)
        self.log_event(log_message)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: Union[Member, User]):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        guild_name = reaction.message.guild.name if reaction.message.guild else '私人訊息'
        channel_name = reaction.message.channel.name if reaction.message.guild else '無頻道'
        log_message = f"[{formatted_time}] 「{user.display_name}」在「{guild_name}」群組的「{channel_name}」頻道中添加反應「{reaction.emoji}」到訊息「{reaction.message.content}」"
        print(log_message)
        self.log_event(log_message)

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction: Reaction, user: Union[Member, User]):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        guild_name = reaction.message.guild.name if reaction.message.guild else '私人訊息'
        channel_name = reaction.message.channel.name if reaction.message.guild else '無頻道'
        log_message = f"[{formatted_time}] 「{user.display_name}」在「{guild_name}」群組的「{channel_name}」頻道中移除反應「{reaction.emoji}」到訊息「{reaction.message.content}」"
        print(log_message)
        self.log_event(log_message)

    @commands.Cog.listener()
    async def on_reaction_clear(self, message: discord.Message, reactions: List[discord.Reaction]):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        reaction_emojis = [str(i.emoji) for i in reactions]
        guild_name = message.guild.name if message.guild else '私人訊息'
        channel_name = message.channel.name if message.guild else '無頻道'
        log_message = f"[{formatted_time}] 在「{guild_name}」群組的「{channel_name}」頻道中訊息「{message.content}」移除所有反應「{', '.join(reaction_emojis)}」"
        print(log_message)
        self.log_event(log_message)

        
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        guild_name = interaction.guild.name if interaction.guild else '私人訊息'
        if interaction.command is not None:
            log_message = f"[{formatted_time}] 「{interaction.user.display_name}」在「{guild_name}」群組中使用指令「/{interaction.command.name}」"
            print(log_message)
            self.log_event(log_message)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        now = datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        guild_name = member.guild.name
        if before.channel is None and after.channel:
            log_message = f"[{formatted_time}] 在「{guild_name}」群組中「{member.display_name}」加入「{after.channel.name}」語音頻道"
            print(log_message)
            self.log_event(log_message)
        elif before.channel and after.channel is None:
            log_message = f"[{formatted_time}] 在「{guild_name}」群組中「{member.display_name}」離開「{before.channel.name}」語音頻道"
            print(log_message)
            self.log_event(log_message)
        elif before.channel != after.channel:
            log_message = f"[{formatted_time}] 在「{guild_name}」群組中「{member.display_name}」移動「{before.channel.name} -> {after.channel.name}」語音頻道"
            print(log_message)
            self.log_event(log_message)

async def setup(bot: commands.Bot):
    cog = Event(bot)
    await bot.add_cog(Event(bot))
    for command in cog.get_commands():
            bot.add_listener(cog.log_command_usage, f'on_app_commands_{command.name}')