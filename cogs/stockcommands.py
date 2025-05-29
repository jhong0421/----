import discord, sqlite3, requests, os, aiohttp
from discord.ext import commands, tasks
from discord import app_commands
from bs4 import BeautifulSoup
from datetime import datetime
from linebot import LineBotApi
from linebot.exceptions import LineBotApiError
from linebot.models import TextSendMessage
from googlesearch import search
from datetime import datetime, time, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# 設定你的Line Bot Access Token
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))

class Favorites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = None
        self.c = None
        self.guild_ids = [1170046549825441822, 1016715052633559143, 386856020988919808]
        self.check_stock_prices.start()  # 啟動定期檢查任務

    # 先建立資料夾再初始化連線
        if not os.path.exists('db'):
            os.makedirs('db', exist_ok=True)  # 新增 exist_ok 防止多線程問題
        
        # 確保 db 資料夾存在
        if not os.path.exists('db'):
            os.makedirs('db')
    
    def ensure_connection(self):
        if not self.conn or not self.c:
            self.conn = sqlite3.connect('db/favorites.db')
            self.c = self.conn.cursor()
    
    def create_stock_daily_table(self, stock_code):
        """創建新股票的每日價格紀錄表，並在表名前加上前綴"""
        table_name = f'stock_{stock_code}_daily_prices'  # 加上 'stock_' 前綴
        self.c.execute(f'''
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            date DATE PRIMARY KEY,
            closing_price REAL
        )
        ''')
        self.conn.commit()
    
    def cog_unload(self):
        self.check_stock_prices.cancel()  # 確保任務在 cog 卸載時停止
        if self.conn:
            self.conn.close()
            self.conn = None
            self.c = None

    @tasks.loop(minutes=3)  # 每3分鐘檢查一次
    async def check_stock_prices(self):
        current_time = datetime.now(timezone(timedelta(hours=8)))  # 台北時間
        start_time = time(9, 0)  # 09:00
        end_time = time(13, 30)  # 13:30

        # 檢查當前時間是否在指定範圍內
        if start_time <= current_time.time() <= end_time:
            self.ensure_connection()
            try:
                self.c.execute('''
                SELECT stock.company_name, stock.current_price, stock.last_update, 
                       favorites.user_id, favorites.stock_code, favorites.last_price, 
                       user_line_mapping.line_user_id
                FROM favorites 
                LEFT JOIN stock ON favorites.stock_code = stock.stock_code
                LEFT JOIN user_line_mapping ON favorites.user_id = user_line_mapping.user_id
                ''')

                rows = self.c.fetchall()
                for company_name, current_stock_price, last_update, user_id, stock_code, last_price, line_user_id in rows:
                    current_price = await self.get_stock_price(stock_code)

                    # 自動創建每日價格表，如果還沒創建
                    self.create_stock_daily_table(stock_code)

                    # 表名加前綴
                    table_name = f'stock_{stock_code}_daily_prices'

                    # 插入或更新每日價格
                    today = datetime.now().strftime('%Y-%m-%d')
                    self.c.execute(f'''
                    INSERT OR REPLACE INTO "{table_name}" (date, closing_price)
                    VALUES (?, ?)
                    ''', (today, current_price))
                    self.conn.commit()

                    if last_price is not None and current_price is not None:
                        price_change = (current_price - last_price) / last_price * 100
                        # 只在價格變動超過5%時發送通知
                        if abs(price_change) >= 5:
                            user = self.bot.get_user(user_id)

                            # 獲取股票名稱
                            stock_name = await self.get_stock_name(stock_code)  # 確保這裡是異步調用

                            # 檢查 stock_name 是否為 None
                            if stock_name is None or stock_name == "":
                                stock_name = "未知股票名稱"  # 或者你可以選擇其他替代值

                            # 搜尋價格異動5%的股票訊息
                            query = f"{stock_name}新聞"

                            for j in search(query, sleep_interval=5, num_results=5):
                                print(j)

                            message = f"您關注的股票 {stock_code} {stock_name} 價格變動超過5%！\n上次價格: {last_price}\n當前價格: {current_price}\n變動幅度: {price_change:.2f}%"
                            message_stock_information = f"{j}"

                            if user:
                                try:
                                    await user.send(message)
                                    await user.send(message_stock_information)
                                except discord.errors.Forbidden:
                                    print(f"無法向用戶 {user_id} 發送Discord私人訊息")

                            if line_user_id:
                                try:
                                    line_bot_api.push_message(line_user_id, TextSendMessage(text=message))
                                    line_bot_api.push_message(line_user_id, TextSendMessage(text=message_stock_information))
                                except LineBotApiError as e:
                                    print(f"無法向Line用戶 {line_user_id} 發送私人訊息: {e}")

                        # 更新數據庫中的最新價格
                        self.c.execute('UPDATE favorites SET last_price = ?, last_update = ? WHERE user_id = ? AND stock_code = ?',
                                       (current_price, datetime.now(), user_id, stock_code))
                        self.conn.commit()
            except Exception as e:
                print(f"檢查股票價格時發生錯誤: {e}")
    
    async def get_stock_name(self, stock_code):
        url = f'https://tw.stock.yahoo.com/quote/{stock_code}'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    web_text = await response.text()
                    soup = BeautifulSoup(web_text, "html.parser")

                    # 嘗試更精確的選擇器來抓取股票名稱
                    stock_name_element = soup.select_one('.Fz\\(24px\\)')
                    if stock_name_element:
                        return stock_name_element.get_text().strip()

                    # 嘗試其他選擇器來獲取名稱
                    stock_name_element = soup.select_one('h1')
                    if stock_name_element:
                        return stock_name_element.get_text().strip()

                    # 嘗試獲取頁面標題
                    title = soup.title.string if soup.title else ""
                    if title:
                        return title.split(" - ")[0]  # 從標題中獲取名稱，通常格式為 "名稱 - 其他信息"
    
        except Exception as e:
            print(f"獲取股票 {stock_code} 名稱時出錯: {e}")
        return "未知股票名稱"  # 如果無法獲取名稱，返回預設值

    @check_stock_prices.before_loop
    async def before_check_stock_prices(self):
        await self.bot.wait_until_ready()

    async def get_stock_price(self, stock_code):
        url = f'https://tw.stock.yahoo.com/quote/{stock_code}'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    web_text = await response.text()
                    soup = BeautifulSoup(web_text, "html.parser")
            
                    # 嘗試獲取實時價格
                    price_element = soup.select_one('.Fz\\(32px\\)')
                    if price_element:
                        price_text = price_element.get_text().strip()
                        # 移除所有非數字字符（除了小數點）
                        price_text = ''.join(char for char in price_text if char.isdigit() or char == '.')
                        if price_text:
                            return float(price_text)
        
                    # 如果無法獲取實時價格，嘗試獲取收盤價
                    price_element = soup.select_one('td[data-test="PREV_CLOSE-value"]')
                    if price_element:
                        price_text = price_element.get_text().strip()
                        price_text = ''.join(char for char in price_text if char.isdigit() or char == '.')
                        if price_text:
                            print(f"股票 {stock_code} 使用收盤價: {price_text}")
                            return float(price_text)
        
                    # 如果仍然無法獲取價格，輸出更詳細的錯誤信息
                    print(f"無法獲取股票 {stock_code} 的價格。網頁標題: {soup.title.string if soup.title else 'No title'}")
                    return None
        except Exception as e:
            print(f"獲取股票 {stock_code} 價格時出錯: {e}")
        return None
        
    @app_commands.command(name="加股票最愛", description="將股票代碼加入最愛清單")
    async def add_favorite(self, interaction: discord.Interaction, 股票代碼: str):
        self.ensure_connection()  # 確保 SQLite 連線已經建立
        
        # 判斷交互所屬的伺服器是否是特定的幾個
        allowed_guilds = [1170046549825441822, 1016715052633559143, 386856020988919808]  # 這裡填上你想要允許的伺服器ID
        if interaction.guild.id not in allowed_guilds:
            await interaction.response.send_message('很抱歉，您所在的伺服器無法使用此功能。', ephemeral=True)
            return
        stock_code = 股票代碼
        user_id = interaction.user.id
        self.c.execute('INSERT OR IGNORE INTO favorites (user_id, stock_code) VALUES (?, ?)', (user_id, stock_code))
        self.conn.commit()
        await interaction.response.send_message(f'股票代碼 {stock_code} 已加入您的最愛清單！', ephemeral=True)
        current_price = await self.get_stock_price(stock_code)
        self.c.execute('INSERT OR REPLACE INTO favorites (user_id, stock_code, last_price, last_update) VALUES (?, ?, ?, ?)',
                       (user_id, stock_code, current_price, datetime.now()))
        self.conn.commit()

    @app_commands.command(name="移除股票最愛項目", description="從最愛清單中移除一個股票代碼")
    async def remove_favorite_item(self, interaction: discord.Interaction):
        allowed_guilds = [1170046549825441822, 1016715052633559143, 386856020988919808]
        if interaction.guild.id not in allowed_guilds:
            await interaction.response.send_message('很抱歉，您所在的伺服器無法使用此功能。', ephemeral=True)
            return
        
        self.ensure_connection()
        user_id = interaction.user.id
        self.c.execute('SELECT stock_code FROM favorites WHERE user_id = ?', (user_id,))
        rows = self.c.fetchall()
        if rows:
            options = [discord.SelectOption(label=row[0], value=row[0]) for row in rows]
            view = RemoveFavoriteDropdownView(options, self)
            await interaction.response.send_message('選擇您要移除的股票代碼：', view=view, ephemeral=True)
        else:
            await interaction.response.send_message('您的股票最愛清單是空的。', ephemeral=True)

    @app_commands.command(name="股票最愛清單", description="顯示您的股票最愛清單")
    async def list_favorites(self, interaction: discord.Interaction):
        # 判斷交互所屬的伺服器是否是特定的幾個
        allowed_guilds = [1170046549825441822, 1016715052633559143, 386856020988919808]  # 這裡填上你想要允許的伺服器ID
        if interaction.guild.id not in allowed_guilds:
            await interaction.response.send_message('很抱歉，您所在的伺服器無法使用此功能。', ephemeral=True)
            return
    
        # 確保數據庫連接已建立
        self.ensure_connection()
    
        user_id = interaction.user.id
        self.c.execute('SELECT stock_code FROM favorites WHERE user_id = ?', (user_id,))
        rows = self.c.fetchall()
        if rows:
            favorite_list = '\n'.join([row[0] for row in rows])
            await interaction.response.send_message(f'您的股票最愛清單：\n{favorite_list}', ephemeral=True)
        else:
            await interaction.response.send_message('您的股票最愛清單是空的。', ephemeral=True)
        
    @app_commands.command(name="股票最愛查詢", description="從最愛清單中選擇股票代碼進行查詢")
    async def query_favorite(self, interaction: discord.Interaction):
        # 判斷交互所屬的伺服器是否是特定的幾個
        allowed_guilds = [1170046549825441822, 1016715052633559143, 386856020988919808]  # 這裡填上你想要允許的伺服器ID
        if interaction.guild.id not in allowed_guilds:
            await interaction.response.send_message('很抱歉，您所在的伺服器無法使用此功能。', ephemeral=True)
        user_id = interaction.user.id
        self.c.execute('SELECT stock_code FROM favorites WHERE user_id = ?', (user_id,))
        rows = self.c.fetchall()
        if rows:
            options = [discord.SelectOption(label=row[0], value=row[0]) for row in rows]
            view = FavoriteStockDropdownView(options, interaction)
            await interaction.response.send_message('選擇您要查詢的股票代碼：', view=view, ephemeral=True)
        else:
            await interaction.response.send_message('您的股票最愛清單是空的。', ephemeral=True)
    
    @app_commands.command(name="股票最愛一覽", description="顯示您所有股票最愛清單的股票資訊")
    async def list_all_favorites(self, interaction: discord.Interaction):
        allowed_guilds = [1170046549825441822, 1016715052633559143, 386856020988919808]
        if interaction.guild.id not in allowed_guilds:
            await interaction.response.send_message('很抱歉，您所在的伺服器無法使用此功能。', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        self.ensure_connection()
        user_id = interaction.user.id
        self.c.execute('SELECT stock_code FROM favorites WHERE user_id = ?', (user_id,))
        rows = self.c.fetchall()
        if rows:
            embed = discord.Embed(title="您的股票最愛一覽", color=0x00ff00)
            for row in rows:
                stock_code = row[0]
                try:
                    url = f'https://tw.stock.yahoo.com/quote/{stock_code}'
                    web = requests.get(url)
                    soup = BeautifulSoup(web.text, "html.parser")

                    title_elements = soup.select('.Fz\\(24px\\)')
                    title = title_elements[0].get_text().strip() if title_elements else "未知股名"

                    try:
                        price = soup.select('.Fz\\(32px\\)')[0].get_text().strip()
                    except IndexError:
                        price = "未知價格"

                    b1 = soup.select('.Fz\\(20px\\)')[0]
                    b2 = b1.get_text()
                    s = ''
                    try:
                        if soup.select('#main-0-QuoteHeader-Proxy')[0].select('.C($c-trend-down)')[0]:
                            s = '-'
                    except:
                        try:
                            if soup.select('#main-0-QuoteHeader-Proxy')[0].select('.C($c-trend-up)')[0]:
                                s = '+'
                        except:
                            s = '-'

                    embed.add_field(name=f"{title} ({stock_code})", value=f'價格: {price} 漲跌: {s}{b2}', inline=False)
                except Exception as e:
                    embed.add_field(name=f"錯誤 ({stock_code})", value=f"獲取股票資訊時出錯: {str(e)}", inline=False)

            # 使用 followup 發送消息，而不是 response
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send('您的股票最愛清單是空的。', ephemeral=True)

class FavoriteStockDropdownView(discord.ui.View):
    def __init__(self, options, interaction):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.add_item(FavoriteStockDropdown(options))

class FavoriteStockDropdown(discord.ui.Select):
    def __init__(self, options):
        super().__init__(placeholder='選擇一個股票代碼...', options=options)

    async def callback(self, interaction: discord.Interaction):
        stock_code = self.values[0]
        await interaction.response.defer()
        await self.lookup_stock(interaction, stock_code)

    async def lookup_stock(self, interaction, stock_code):
        url = f'https://tw.stock.yahoo.com/quote/{stock_code}'
        web = requests.get(url)
        soup = BeautifulSoup(web.text, "html.parser")

        title_elements = soup.select('.Fz\\(24px\\)')
        title = title_elements[0].get_text().strip() if title_elements else "未知股名"

        try:
            price = soup.select('.Fz\\(32px\\)')[0].get_text().strip()
        except IndexError:
            price = "未知價格"

        b1 = soup.select('.Fz\\(20px\\)')[0] # 取漲幅值
        b2 = b1.get_text()
        s = '' # 初始化漲幅
        try:
            # 如果 main-0-QuoteHeader-Proxy id 的 div 裡有 C($c-trend-down) 的 class
            # 表示狀態為下跌
            if soup.select('#main-0-QuoteHeader-Proxy')[0].select('.C($c-trend-down)')[0]:
                s = '-'
        except:
            try:
                # 如果 main-0-QuoteHeader-Proxy id 的 div 裡有 C($c-trend-up) 的 class
                # 表示狀態為上漲
                if soup.select('#main-0-QuoteHeader-Proxy')[0].select('.C($c-trend-up)')[0]:
                    s = '+'
            except:
                # 如果都沒有包含，表示平盤
                s = '-'

        embed = discord.Embed(title=f"股票查詢：{title}", color=0x00ff00)
        embed.add_field(name="股票代碼", value=stock_code, inline=False)
        embed.add_field(name="當前價格", value=price, inline=True)
        embed.add_field(name="漲跌狀態", value=f'{s}{b2}', inline=True)

        await interaction.followup.send(embed=embed)

class RemoveFavoriteDropdownView(discord.ui.View):
    def __init__(self, options, interaction, conn):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.conn = conn
        self.add_item(RemoveFavoriteDropdown(options, conn))

class RemoveFavoriteDropdown(discord.ui.Select):
    def __init__(self, options, favorites_cog):
        super().__init__(placeholder='選擇一個股票代碼...', options=options)
        self.favorites_cog = favorites_cog

    async def callback(self, interaction: discord.Interaction):
        stock_code = self.values[0]
        user_id = interaction.user.id
        
        # 確保數據庫連接是打開的
        self.favorites_cog.ensure_connection()
        
        try:
            # 使用 Favorites cog 中的數據庫連接
            self.favorites_cog.c.execute('DELETE FROM favorites WHERE user_id = ? AND stock_code = ?', (user_id, stock_code))
            self.favorites_cog.conn.commit()
            
            # 先回應互動
            await interaction.response.send_message(f'股票代碼 {stock_code} 已從您的最愛清單移除！', ephemeral=True)
            
            # 更新下拉選單選項
            self.favorites_cog.c.execute('SELECT stock_code FROM favorites WHERE user_id = ?', (user_id,))
            remaining_stocks = self.favorites_cog.c.fetchall()
            
            if remaining_stocks:
                new_options = [discord.SelectOption(label=row[0], value=row[0]) for row in remaining_stocks]
                self.options = new_options
                
                # 嘗試編輯原始訊息，如果失敗則忽略
                try:
                    await interaction.message.edit(view=self.view)
                except discord.errors.NotFound:
                    pass  # 訊息可能已被刪除，忽略錯誤
            else:
                # 如果沒有剩餘的股票，禁用下拉選單
                self.disabled = True
                try:
                    await interaction.followup.send('您的股票最愛清單現在是空的。', ephemeral=True)
                    await interaction.message.edit(view=self.view)
                except discord.errors.NotFound:
                    pass  # 訊息可能已被刪除，忽略錯誤
            
        except Exception as e:
            # 只在互動尚未回應時發送錯誤訊息
            if not interaction.response.is_done():
                await interaction.response.send_message(f'移除股票時發生錯誤：{str(e)}', ephemeral=True)
            else:
                try:
                    await interaction.followup.send(f'移除股票時發生錯誤：{str(e)}', ephemeral=True)
                except:
                    pass  # 如果連 followup 也失敗，則忽略

class RemoveFavoriteDropdownView(discord.ui.View):
    def __init__(self, options, favorites_cog):
        super().__init__(timeout=None)
        self.favorites_cog = favorites_cog
        self.add_item(RemoveFavoriteDropdown(options, favorites_cog))

async def setup(bot: commands.Bot):
    cog = Favorites(bot)
    await bot.add_cog(Favorites(bot))
    for command in cog.get_commands():
        bot.add_listener(cog.log_command_usage, f'on_app_commands_{command.name}')