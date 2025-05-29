import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from typing import Optional
import aiohttp
import io
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class AIChatroom(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "./db/ai_chat.db"
        self.setup_db()
        self.sessions = {}  # 儲存當前會話的上下文
        
        # 新增：Bot 啟動時恢復現有會話
        self.bot.loop.create_task(self.restore_sessions())

    async def restore_sessions(self):
        """從資料庫恢復所有活躍的會話"""
        await self.bot.wait_until_ready()  # 等待 Bot 完全啟動
    
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT thread_id, model, history FROM chat_sessions")
        sessions = cursor.fetchall()
        conn.close()
    
        for thread_id, model, history in sessions:
            try:
                # 檢查討論區是否仍然存在
                thread = await self.bot.fetch_channel(thread_id)
                if thread:
                    self.sessions[thread_id] = {
                        "model": model,
                        "history": eval(history) if history else []
                    }
                    print(f"已恢復會話: 討論區 {thread_id} (模型: {model})")
                else:
                    # 討論區不存在則清理記錄
                    self.cleanup_session(thread_id)
            except discord.NotFound:
                self.cleanup_session(thread_id)
            except Exception as e:
                print(f"恢復會話時出錯 (討論區 {thread_id}): {str(e)}")
    
    def cleanup_session(self, thread_id: int):
        """清理不存在的會話記錄"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE thread_id = ?", (thread_id,))
        conn.commit()
        conn.close()
        print(f"已清理不存在討論區的會話: {thread_id}")
    
    def setup_db(self):
        os.makedirs("./db", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            thread_id INTEGER UNIQUE,
            model TEXT,
            history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()

    async def call_ai_api(self, model: str, messages: list, image_url: Optional[str] = None):
        """增強 DeepSeek API 呼叫穩定性（解決 JSON 解析超時）"""
        api_url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
            "Content-Type": "application/json"
        }

        # 限制請求資料量
        payload = {
            "model": model,
            "messages": self._format_messages(messages)[-6:],  # 只保留最近6條訊息
            "temperature": 0.7,
            "max_tokens": 800,  # 減少生成長度
            "stream": False  # 關閉串流避免複雜處理
        }

        # 如果是圖片請求，進一步限制
        if image_url:
            payload["max_tokens"] = 500
            payload["messages"][-1]["content"] = [
                {"type": "text", "text": "分析此圖片"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]

        retry_delay = [1, 3, 5]  # 重試間隔（秒）
        last_error = None

        for attempt in range(3):
            try:
                # 使用分塊讀取回應
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        api_url,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:

                        # 檢查狀態碼
                        if response.status != 200:
                            error_msg = await response.text()
                            raise ValueError(f"API 錯誤: HTTP {response.status} - {error_msg[:200]}")

                        # 使用分塊處理大回應
                        full_data = bytearray()
                        async for chunk in response.content.iter_chunked(1024):  # 1KB 為單位讀取
                            full_data.extend(chunk)
                            if len(full_data) > 1_000_000:  # 超過 1MB 放棄
                                raise ValueError("回應資料過大")

                        # 解析 JSON
                        try:
                            data = json.loads(full_data.decode())
                            return data["choices"][0]["message"]["content"]
                        except json.JSONDecodeError:
                            raise ValueError("無效的 JSON 格式")

            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
                last_error = str(e)
                print(f"嘗試 {attempt + 1} 失敗: {last_error}")
                if attempt < 2:  # 前兩次重試
                    await asyncio.sleep(retry_delay[attempt])
                continue

        return f"⚠️ 無法取得回應（最終錯誤: {last_error}）"

    def _format_messages(self, messages: list) -> list:
        """格式化訊息歷史以符合 API 要求"""
        formatted = []
        
        for msg in messages:
            # 跳過空的系統訊息
            if msg.get("role") == "system" and not msg.get("content"):
                continue
                
            # 處理多模態訊息 (文字 + 圖片)
            if isinstance(msg.get("content"), list):
                content = []
                for item in msg["content"]:
                    if item["type"] == "text" and item["text"].strip():
                        content.append(item)
                    elif item["type"] == "image_url":
                        content.append(item)
                
                if content:  # 只有當有實際內容時才添加
                    formatted.append({
                        "role": msg["role"],
                        "content": content
                    })
            elif msg.get("content", "").strip():  # 普通文字訊息
                formatted.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return formatted

    async def monitor_connection(self):
        """背景監控 API 連接狀態"""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                # 每30分鐘檢查一次
                await asyncio.sleep(1800)

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.deepseek.com/v1/models",
                        headers={"Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}"},
                        timeout=15
                    ) as resp:
                        status = resp.status
                        if status != 200:
                            print(f"API 監控異常: HTTP {status}")
                            # 可在此添加通知管理員的邏輯
            except Exception as e:
                print(f"監控任務錯誤: {type(e).__name__}: {str(e)}")
    
    async def _split_long_message(self, message: str) -> list:
        """將長訊息分割成多個部分"""
        if len(message) <= 1900:
            return [message]
        
        # 嘗試按段落分割
        parts = []
        current_part = ""
        
        for paragraph in message.split("\n\n"):
            if len(current_part) + len(paragraph) + 2 > 1900:
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                
                # 如果單個段落就超過限制
                if len(paragraph) > 1900:
                    chunks = [paragraph[i:i+1900] for i in range(0, len(paragraph), 1900)]
                    parts.extend(chunks)
                else:
                    current_part = paragraph
            else:
                if current_part:
                    current_part += "\n\n"
                current_part += paragraph
        
        if current_part:
            parts.append(current_part)
        
        return parts
    
    @app_commands.command(name="check_api", description="檢查API連接狀態")
    async def check_api(self, interaction: discord.Interaction):
        """更穩定的API檢查指令"""
        try:
            # 必須先響應交互
            await interaction.response.defer(thinking=True)

            test_msg = [{"role": "user", "content": "測試連接，請回覆 OK"}]

            # 直接使用 call_ai_api 方法測試
            response = await self.call_ai_api("deepseek-chat", test_msg)

            # 編輯原始回應
            await interaction.edit_original_response(
                content=f"✅ API 狀態正常\n回應: {response[:100]}..."
            )
        except Exception as e:
            try:
                await interaction.edit_original_response(
                    content=f"❌ 檢查失敗: {type(e).__name__}"
                )
            except:
                # 最終回退方案
                channel = interaction.channel
                await channel.send(
                    f"{interaction.user.mention} API 檢查失敗: {type(e).__name__}"
                )
    
    @app_commands.command(name="create_chat", description="創建一個AI聊天討論區")
    @app_commands.describe(topic="討論區主題", model="選擇AI模型")
    @app_commands.choices(model=[
        app_commands.Choice(name="DeepSeek Chat", value="deepseek-chat"),
        app_commands.Choice(name="DeepSeek Coder", value="deepseek-coder"),
        app_commands.Choice(name="GPT-3.5", value="gpt-3.5"),
    ])
    async def create_chat(
        self, 
        interaction: discord.Interaction, 
        topic: str,
        model: app_commands.Choice[str]
    ):
        """創建一個私人討論區作為AI聊天室"""
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("此指令只能在文字頻道中使用", ephemeral=True)
            return
    
        # 檢查是否已存在未關閉的聊天室
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT thread_id FROM chat_sessions WHERE channel_id = ?",
            (interaction.channel.id,)
        )
        existing_thread = cursor.fetchone()
    
        if existing_thread:
            try:
                # 嘗試取得現有討論區
                thread = await interaction.guild.fetch_channel(existing_thread[0])
                await interaction.response.send_message(
                    f"此頻道已有開啟的聊天室: {thread.mention}\n"
                    f"請先使用 `/end_chat` 關閉現有聊天室",
                    ephemeral=True
                )
                return
            except discord.NotFound:
                # 如果討論區不存在，清除舊記錄
                cursor.execute(
                    "DELETE FROM chat_sessions WHERE thread_id = ?",
                    (existing_thread[0],)
                )
                conn.commit()
    
        # 創建討論區
        thread = await interaction.channel.create_thread(
            name=topic,
            type=discord.ChannelType.private_thread
        )
    
        # 儲存到資料庫
        try:
            cursor.execute(
                "INSERT INTO chat_sessions (channel_id, thread_id, model) VALUES (?, ?, ?)",
                (interaction.channel.id, thread.id, model.value)
            )
            conn.commit()
        except sqlite3.Error as e:
            await interaction.response.send_message(
                "創建聊天室時發生錯誤，請稍後再試",
                ephemeral=True
            )
            print(f"資料庫錯誤: {str(e)}")
            return
        finally:
            conn.close()
    
        # 儲存會話上下文
        self.sessions[thread.id] = {
            "model": model.value,
            "history": []
        }
    
        await interaction.response.send_message(
            f"已創建討論區 {thread.mention}，使用模型: {model.name}\n"
            f"直接在討論區中發送訊息即可與AI對話\n"
            f"使用 `/end_chat` 結束對話",
            ephemeral=True
        )
    
        # 發送歡迎訊息
        await thread.send(f"# {topic}\n歡迎使用AI聊天室！當前模型: {model.name}\n直接發送訊息開始對話吧！")

    @app_commands.command(name="change_model", description="變更當前討論區的AI模型")
    @app_commands.describe(model="新的AI模型")
    @app_commands.choices(model=[
        app_commands.Choice(name="DeepSeek Chat", value="deepseek-chat"),
        app_commands.Choice(name="DeepSeek Coder", value="deepseek-coder"),
        app_commands.Choice(name="GPT-3.5", value="gpt-3.5"),
    ])
    async def change_model(
        self, 
        interaction: discord.Interaction, 
        model: app_commands.Choice[str]
    ):
        """變更當前討論區的AI模型"""
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("此指令只能在討論區中使用", ephemeral=True)
            return
        
        # 更新資料庫
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE chat_sessions SET model = ? WHERE thread_id = ?",
            (model.value, interaction.channel.id)
        )
        conn.commit()
        conn.close()
        
        # 更新會話上下文
        if interaction.channel.id in self.sessions:
            self.sessions[interaction.channel.id]["model"] = model.value
        
        await interaction.response.send_message(
            f"已將AI模型變更為: {model.name}",
            ephemeral=True
        )

    @app_commands.command(name="list_chats", description="列出當前頻道的所有AI聊天室")
    async def list_chats(self, interaction: discord.Interaction):
        """列出當前頻道的所有AI聊天室"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT thread_id FROM chat_sessions WHERE channel_id = ?",
            (interaction.channel.id,)
        )
        threads = cursor.fetchall()
        conn.close()

        if not threads:
            await interaction.response.send_message("此頻道沒有開啟的AI聊天室", ephemeral=True)
            return
    
        message = "**當前頻道的AI聊天室:**\n"
        for thread_id in threads:
            try:
                thread = await interaction.guild.fetch_channel(thread_id[0])
                message += f"- {thread.mention} (ID: {thread.id})\n"
            except discord.NotFound:
                message += f"- [已刪除的聊天室] (ID: {thread_id[0]})\n"
    
        await interaction.response.send_message(message, ephemeral=True)
    
    @app_commands.command(name="end_chat", description="結束當前AI聊天室並刪除歷史")
    async def end_chat(self, interaction: discord.Interaction):
        """結束AI聊天室並刪除歷史"""
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message("此指令只能在討論區中使用", ephemeral=True)
            return
        
        # 從資料庫刪除
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM chat_sessions WHERE thread_id = ?",
            (interaction.channel.id,)
        )
        conn.commit()
        conn.close()
        
        # 移除會話上下文
        if interaction.channel.id in self.sessions:
            del self.sessions[interaction.channel.id]
        
        await interaction.response.send_message("聊天室已關閉，歷史記錄已刪除")
        await interaction.channel.delete()

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """全局指令錯誤處理"""
        if isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.NotFound) and "Unknown interaction" in str(original):
                try:
                    await interaction.channel.send(
                        f"{interaction.user.mention} 指令處理超時，請稍後重試"
                    )
                    return
                except:
                    pass
    
        await interaction.response.send_message(
            f"⚠️ 指令執行錯誤: {str(error)}",
            ephemeral=True
        )
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 忽略機器人自己的訊息
        if message.author == self.bot.user:
            return

        # 確保在討論區中且有有效會話
        if not isinstance(message.channel, discord.Thread) or message.channel.id not in self.sessions:
            return

        # 檢查圖片附件
        image_url = None
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_url = attachment.proxy_url  # 使用代理 URL 避免 Discord 連結過期
                break

        # 更新對話歷史（限制長度）
        session = self.sessions[message.channel.id]
        session["history"].append({"role": "user", "content": message.content, "image_url": image_url})
        session["history"] = session["history"][-8:]  # 保留最近 8 條

        # 顯示「正在輸入」狀態
        async with message.channel.typing():
            try:
                response = await self.call_ai_api(
                    model=session["model"],
                    messages=session["history"],
                    image_url=image_url
                )

                # 處理回應
                session["history"].append({"role": "assistant", "content": response})

                # 分段發送長訊息
                chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
                for chunk in chunks:
                    await message.channel.send(chunk)

            except Exception as e:
                await message.channel.send(f"❌ 處理錯誤: {str(e)[:500]}")

async def setup(bot: commands.Bot):
    cog = AIChatroom(bot)
    await bot.add_cog(cog)
    bot.tree.on_error = cog.on_app_command_error  # 註冊錯誤處理