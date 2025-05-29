import discord
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from typing import Optional, Union, List
from discord import Reaction, Member, User

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 先建立資料夾再初始化連線
        if not os.path.exists('db'):
            os.makedirs('db', exist_ok=True)  # 新增 exist_ok 防止多線程問題
        
        self.conn = sqlite3.connect('db/main.db')
        
        # 確保連線成功後再執行初始化
        self._initialize_database()
        
        self.create_command_tables()  # 新增專用指令記錄表
        
        # 確保 db 資料夾存在
        if not os.path.exists('db'):
            os.makedirs('db')
            
        self.conn = sqlite3.connect('db/main.db')
        self.create_tables()
    
    def _initialize_database(self):
        """統一處理資料表建立"""
        try:
            with self.conn:
                self.create_tables()
                self.create_command_tables()
        except sqlite3.Error as e:
            print(f"資料庫初始化失敗: {str(e)}")
            raise

    def create_command_tables(self):
        c = self.conn.cursor()
        
        # 股票相關表格
        c.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            last_price REAL,
            last_update TIMESTAMP,
            PRIMARY KEY (user_id, stock_code)
        )''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS user_line_mapping (
            user_id INTEGER PRIMARY KEY,
            line_user_id TEXT
        )''')

        c.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            stock_code TEXT PRIMARY KEY,
            company_name TEXT,
            current_price REAL,
            last_update TIMESTAMP
        )''')
        
        # 21點指令記錄表
        c.execute('''CREATE TABLE IF NOT EXISTS commands_blackjack
                     (id INTEGER PRIMARY KEY,
                      時間 DATETIME,
                      用戶ID TEXT,
                      伺服器ID TEXT,
                      結果 TEXT,
                      玩家分數 INTEGER,
                      莊家分數 INTEGER)''')

        # 設定狀態記錄表
        c.execute('''CREATE TABLE IF NOT EXISTS commands_setstatus
                     (id INTEGER PRIMARY KEY,
                      時間 DATETIME,
                      用戶ID TEXT,
                      伺服器ID TEXT,
                      狀態類型 TEXT,
                      狀態文字 TEXT)''')
        
        # 基礎指令記錄表
        c.execute('''CREATE TABLE IF NOT EXISTS commands_basic
                     (id INTEGER PRIMARY KEY,
                      時間 DATETIME,
                      用戶ID TEXT,
                      伺服器ID TEXT,
                      指令類型 TEXT,
                      延遲數值 TEXT)''')

        # AI指令記錄表
        c.execute('''CREATE TABLE IF NOT EXISTS commands_ai
                     (id INTEGER PRIMARY KEY,
                      時間 DATETIME,
                      用戶ID TEXT,
                      伺服器ID TEXT,
                      問題內容 TEXT,
                      回答摘要 TEXT)''')

        # 天氣指令記錄表
        c.execute('''CREATE TABLE IF NOT EXISTS commands_weather
                     (id INTEGER PRIMARY KEY,
                      時間 DATETIME,
                      用戶ID TEXT,
                      伺服器ID TEXT,
                      查詢城市 TEXT,
                      溫度 REAL,
                      天氣狀況 TEXT)''')
        
        self.conn.commit()
        
        # 運勢指令記錄表
        c.execute('''CREATE TABLE IF NOT EXISTS commands_fortune
                     (id INTEGER PRIMARY KEY,
                      時間 DATETIME,
                      用戶ID TEXT,
                      伺服器ID TEXT,
                      運勢結果 TEXT)''')
        
        self.conn.commit()


    # === 新增專用記錄方法 ===
    def log_blackjack(self, user_id: str, guild_id: str, result: str, player_score: int, dealer_score: int):
        c = self.conn.cursor()
        c.execute('''INSERT INTO commands_blackjack 
                     (時間, 用戶ID, 伺服器ID, 結果, 玩家分數, 莊家分數)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                   user_id,
                   guild_id,
                   result,
                   player_score,
                   dealer_score))
        self.conn.commit()

    def log_setstatus_command(self, user_id: str, guild_id: str, status_type: str, status_text: str):
        c = self.conn.cursor()
        c.execute('''INSERT INTO commands_setstatus
                     (時間, 用戶ID, 伺服器ID, 狀態類型, 狀態文字)
                     VALUES (?, ?, ?, ?, ?)''',
                  (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                   user_id,
                   guild_id,
                   status_type,
                   status_text))
        self.conn.commit()
    
    def log_basic_command(self, user_id: str, guild_id: str, command_type: str, latency: int):
        c = self.conn.cursor()
        c.execute('''INSERT INTO commands_basic 
                     (時間, 用戶ID, 伺服器ID, 指令類型, 延遲數值)
                     VALUES (?, ?, ?, ?, ?)''',
                  (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                   user_id,
                   guild_id,
                   command_type,
                   latency))
        self.conn.commit()

    def log_ai_query(self, user_id: str, guild_id: str, question: str, answer: str):
        c = self.conn.cursor()
        c.execute('''INSERT INTO commands_ai 
                     (時間, 用戶ID, 伺服器ID, 問題內容, 回答摘要)
                     VALUES (?, ?, ?, ?, ?)''',
                  (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                   user_id,
                   guild_id,
                   question,
                   answer[:200]))  # 摘要截斷
        self.conn.commit()

    def log_weather_query(self, user_id: str, guild_id: str, city: str, temp: float, description: str):
        c = self.conn.cursor()
        c.execute('''INSERT INTO commands_weather 
                     (時間, 用戶ID, 伺服器ID, 查詢城市, 溫度, 天氣狀況)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                   user_id,
                   guild_id,
                   city,
                   temp,
                   description))
        self.conn.commit()
    
    def log_fortune_command(self, user_id: str, guild_id: str, fortune_result: str):
        c = self.conn.cursor()
        c.execute('''INSERT INTO commands_fortune
                     (時間, 用戶ID, 伺服器ID, 運勢結果)
                     VALUES (?, ?, ?, ?)''',
                  (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                   user_id,
                   guild_id,
                   fortune_result))  # 摘要截斷
        self.conn.commit()

    def create_tables(self):
        c = self.conn.cursor()
        # 主事件表
        c.execute('''CREATE TABLE IF NOT EXISTS 事件紀錄
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      時間 DATETIME,
                      事件類型 TEXT,
                      伺服器名稱 TEXT,
                      頻道名稱 TEXT,
                      用戶名稱 TEXT,
                      詳細內容 TEXT)''')
        self.conn.commit()

    def 記錄事件(self, 事件類型: str, 伺服器: Optional[discord.Guild], 
           頻道: Optional[discord.abc.GuildChannel], 用戶: Optional[Union[discord.User, discord.Member]], 
           詳細內容: str):
        c = self.conn.cursor()
    
        # 處理頻道名稱
        if 頻道 is None:
            頻道名稱 = '無頻道'
        elif isinstance(頻道, discord.DMChannel):
            頻道名稱 = '私人訊息'
        elif isinstance(頻道, discord.GroupChannel):
            頻道名稱 = '群組聊天'
        else:
            頻道名稱 = 頻道.name

        c.execute('''INSERT INTO 事件紀錄 
                     (時間, 事件類型, 伺服器名稱, 頻道名稱, 用戶名稱, 詳細內容)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                   事件類型,
                   伺服器.name if 伺服器 else '私人訊息',
                   頻道名稱,
                   f"{用戶.name}" if 用戶 else '系統',
                   詳細內容))
        self.conn.commit()

    # === 伺服器事件 ===
    @commands.Cog.listener()
    async def on_guild_join(self, 伺服器: discord.Guild):
        訊息 = f"Bot 加入「{伺服器.name}」伺服器"
        self.記錄事件("伺服器加入", 伺服器, None, None, 訊息)
        print(訊息)

    @commands.Cog.listener()
    async def on_guild_remove(self, 伺服器: discord.Guild):
        訊息 = f"Bot 離開「{伺服器.name}」伺服器"
        self.記錄事件("伺服器離開", 伺服器, None, None, 訊息)
        print(訊息)
        
    @commands.Cog.listener()
    async def on_guild_update(self, 更新前: discord.Guild, 更新後: discord.Guild):
        變化 = []
        if 更新前.name != 更新後.name:
            變化.append(f"名稱: {更新前.name} → {更新後.name}")
        if 更新前.icon != 更新後.icon:
            變化.append("伺服器圖標更新")
            
        if 變化:
            self.記錄事件("伺服器更新", 更新後, None, None, " | ".join(變化))

    # === 成員事件 ===
    @commands.Cog.listener()
    async def on_member_join(self, 成員: discord.Member):
        try:
            頻道 = 成員.guild.system_channel
            if 頻道:
                await 頻道.send(f"歡迎 {成員.mention} 加入伺服器！")
        except Exception as e:
            print(f"無法發送歡迎訊息: {str(e)}")
        
        訊息 = f"成員加入 | 創建時間: {成員.created_at}"
        self.記錄事件("成員加入", 成員.guild, None, 成員, 訊息)

    @commands.Cog.listener()
    async def on_member_remove(self, 成員: discord.Member):
        try:
            頻道 = 成員.guild.system_channel
            if 頻道:
                await 頻道.send(f"{成員.mention} 已離開伺服器！")
        except Exception as e:
            print(f"無法發送歡迎訊息: {str(e)}")
            
        在線時長 = datetime.now(timezone.utc) - 成員.joined_at
        訊息 = f"成員離開 | 在線時長: {str(在線時長).split('.')[0]}"
        self.記錄事件("成員離開", 成員.guild, None, 成員, 訊息)

    # === 訊息事件 ===
    @commands.Cog.listener()
    async def on_message(self, 訊息: discord.Message):
        if 訊息.author.bot:
            return

        附件 = [附件.url for 附件 in 訊息.attachments]
        內容 = f"{訊息.content} | 附件: {', '.join(附件)}" if 附件 else 訊息.content
        
        self.記錄事件("訊息發送", 訊息.guild, 訊息.channel, 訊息.author, 內容)

    @commands.Cog.listener()
    async def on_message_edit(self, 原始訊息: discord.Message, 修改後訊息: discord.Message):
        附件變化 = (
            f"原始附件: {[a.url for a in 原始訊息.attachments]}, "
            f"新附件: {[a.url for a in 修改後訊息.attachments]}"
        )
        內容 = f"『{原始訊息.content}』→『{修改後訊息.content}』{附件變化}"
        self.記錄事件("訊息編輯", 原始訊息.guild, 原始訊息.channel, 原始訊息.author, 內容)
    
    @commands.Cog.listener()
    async def on_message_delete(self, 訊息: discord.Message):
        if 訊息.author.bot:
            return
        
        附件 = [附件.url for 附件 in 訊息.attachments]
        內容 = f"{訊息.content} | 已刪除附件: {', '.join(附件)}" if 附件 else 訊息.content
        self.記錄事件("訊息刪除", 訊息.guild, 訊息.channel, 訊息.author, 內容)

    # === 管理事件 ===
    @commands.Cog.listener()
    async def on_member_ban(self, 伺服器: discord.Guild, 用戶: discord.User):
        訊息 = f"用戶被封禁 | ID: {用戶.id}"
        self.記錄事件("封禁成員", 伺服器, None, 用戶, 訊息)
        await 伺服器.system_channel.send(f"❌ {用戶.mention} 已被封禁")

    @commands.Cog.listener()
    async def on_member_unban(self, 伺服器: discord.Guild, 用戶: discord.User):
        訊息 = f"用戶解除封禁 | ID: {用戶.id}"
        self.記錄事件("解除封禁", 伺服器, None, 用戶, 訊息)
        await 伺服器.system_channel.send(f"✅ {用戶.mention} 已解除封禁")

    # === 語音頻道事件 ===
    @commands.Cog.listener()
    async def on_voice_state_update(self, 成員: discord.Member, 之前狀態: discord.VoiceState, 之後狀態: discord.VoiceState):
        狀態變化 = []
        if 之前狀態.channel != 之後狀態.channel:
            狀態變化.append(f"頻道: {getattr(之前狀態.channel, 'name', '無')} → {getattr(之後狀態.channel, 'name', '無')}")
        if 之前狀態.self_stream != 之後狀態.self_stream:
            狀態變化.append(f"串流: {之前狀態.self_stream} → {之後狀態.self_stream}")
        
        if 狀態變化:
            訊息 = " | ".join(狀態變化)
            self.記錄事件("語音狀態", 成員.guild, 之後狀態.channel or 之前狀態.channel, 成員, 訊息)
            
    # === 反應事件 ===
    @commands.Cog.listener()
    async def on_reaction_add(self, 反應: Reaction, 用戶: Union[Member, User]):
        if 用戶.bot:
            return
            
        表情 = str(反應.emoji) if isinstance(反應.emoji, str) else f"自訂表情:{反應.emoji.name}"
        內容 = f"在訊息「{反應.message.content[:50]}」添加反應 {表情}"
        self.記錄事件("反應添加", 反應.message.guild, 反應.message.channel, 用戶, 內容)

    @commands.Cog.listener()
    async def on_reaction_remove(self, 反應: Reaction, 用戶: Union[Member, User]):
        表情 = str(反應.emoji) if isinstance(反應.emoji, str) else f"自訂表情:{反應.emoji.name}"
        內容 = f"從訊息「{反應.message.content[:50]}」移除反應 {表情}"
        self.記錄事件("反應移除", 反應.message.guild, 反應.message.channel, 用戶, 內容)

    @commands.Cog.listener()
    async def on_reaction_clear(self, 訊息: discord.Message, 反應列表: List[Reaction]):
        表情列表 = [str(r.emoji) if isinstance(r.emoji, str) else f"自訂表情:{r.emoji.name}" for r in 反應列表]
        內容 = f"清除 {len(表情列表)} 個反應: {', '.join(表情列表)}"
        self.記錄事件("反應清除", 訊息.guild, 訊息.channel, None, 內容)
        
    # === 互動事件 ===
    @commands.Cog.listener()
    async def on_interaction(self, 互動: discord.Interaction):
        if 互動.command:
            內容 = f"使用指令: /{互動.command.name}"
            self.記錄事件("指令使用", 互動.guild, 互動.channel, 互動.user, 內容)
            
    # === 用戶狀態事件 ===
    @commands.Cog.listener()
    async def on_presence_update(self, 更新前: Member, 更新後: Member):
        狀態變化 = []
        
        # 檢查活動狀態
        if 更新前.activity != 更新後.activity:
            新活動 = 更新後.activity.name if 更新後.activity else "無"
            狀態變化.append(f"活動: {新活動}")
            
        # 檢查狀態變更
        if 更新前.status != 更新後.status:
            狀態變化.append(f"狀態: {str(更新前.status)} → {str(更新後.status)}")
            
        if 狀態變化:
            self.記錄事件("狀態更新", 更新後.guild, None, 更新後, " | ".join(狀態變化))
    

async def setup(bot):
    await bot.add_cog(Logger(bot))