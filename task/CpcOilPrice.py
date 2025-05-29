import discord
from discord.ext import commands, tasks
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import asyncio


class OilPriceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_config = bot.get_cog("ChannelConfigCog")  # 取得頻道配置Cog
        self.message_ids = {}  # 改為字典儲存各伺服器的訊息ID
        self.check_oil_prices.start()

    def cog_unload(self):
        self.check_oil_prices.cancel()

    @tasks.loop(hours=1)
    async def check_oil_prices(self):
        embed = await self.create_oil_price_embed()
        # 更新所有已設定的伺服器頻道
        for guild in self.bot.guilds:
            await self.update_oil_price_message(guild.id, embed)

    async def update_oil_price_message(self, guild_id, embed):
        channel_id = self.channel_config.get_channel_id(guild_id, "oil_price")
        if not channel_id:
            return

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return

        message_id = self.message_ids.get(guild_id)
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
            except discord.NotFound:
                message = await channel.send(embed=embed)
                self.message_ids[guild_id] = message.id
        else:
            message = await channel.send(embed=embed)
            self.message_ids[guild_id] = message.id

    async def create_oil_price_embed(self):
        url = (
            "https://www.cpc.com.tw/GetOilPriceJson.aspx"
            "?type=TodayOilPriceString"
        )
        response = await asyncio.to_thread(requests.get, url)
        data = response.json()

        t_UpOrDown = data.get('UpOrDown_Html')
        soup = BeautifulSoup(t_UpOrDown, "html.parser")
        down_element = soup.find(class_="sys")
        rate_element = soup.find(class_="rate").find("i")

        if down_element and rate_element:
            down_text = down_element.get_text()
            rate_text = rate_element.get_text()

        t_PriceUpdate = data.get('PriceUpdate')
        embed = discord.Embed(
            title="台灣中油最新油價",
            description=f"{t_PriceUpdate}零時起實施",
            color=0x00ff00
        )
        embed.add_field(
            name="本週油價變動",
            value=f"{down_text}{rate_text}",
            inline=False
        )
        embed.add_field(
            name="⛽ 92無鉛",
            value=f"{data.get('sPrice1')}元/公升",
            inline=True
        )
        embed.add_field(
            name="🚗 95無鉛",
            value=f"{data.get('sPrice2')}元/公升",
            inline=True
        )
        embed.add_field(
            name="🏎️ 98無鉛",
            value=f"{data.get('sPrice3')}元/公升",
            inline=True
        )
        embed.add_field(
            name="🍺 酒精汽油",
            value=f"{data.get('sPrice4')}元/公升",
            inline=True
        )
        embed.add_field(
            name="🚛 超級柴油",
            value=f"{data.get('sPrice5')}元/公升",
            inline=True
        )
        embed.add_field(
            name="🔥 液化石油氣",
            value=f"{data.get('sPrice6')}元/公升",
            inline=True
        )
        embed.set_footer(text="資料來源：台灣中油")

        return embed

    @app_commands.command(name="油價", description="從台灣中油獲取最新的油價並以Embed形式發送至頻道")
    async def oil_price(self, interaction: discord.Interaction):
        embed = await self.create_oil_price_embed()
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(OilPriceCog(bot))
