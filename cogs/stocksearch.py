import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup

class StockLookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="查詢股票", description="查詢指定股票的當前價格、變動狀態和股名")
    async def stock(self, interaction: discord.Interaction, 股票代碼: str):
        stock_code = 股票代碼
        """查詢股票指令，需要提供股票代碼"""
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
                
        # 建立Embed訊息
        embed = discord.Embed(title=f"股票查詢：{title}", color=0x00ff00)
        embed.add_field(name="股票代碼", value=stock_code, inline=False)
        embed.add_field(name="當前價格", value=price, inline=True)
        embed.add_field(name="漲跌狀態", value=f'{s}{b2}', inline=True)

        # 發送Embed訊息
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StockLookup(bot))
    cog = StockLookup(bot)
    for command in cog.get_commands():
            bot.add_listener(cog.log_command_usage, f'on_app_commands_{command.name}')