import discord
from discord.ext import tasks, commands
import requests
from bs4 import BeautifulSoup
from datetime import datetime


class StopWorkClassCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_config = bot.get_cog("ChannelConfigCog")  # 取得頻道配置Cog
        self.check_stop_work_class.start()

    def cog_unload(self):
        self.check_stop_work_class.cancel()

    @tasks.loop(hours=1)
    async def check_stop_work_class(self):
        current_time = datetime.now()
        current_hour = current_time.hour

        if current_hour in [20, 21, 22, 6]:
            response = requests.get(
                "https://www.dgpa.gov.tw/typh/daily/nds.html"
            )
            response.encoding = "utf8"

            if "無停班停課訊息" in response.text:
                return
            else:
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.find("div", class_="Header_YMD")
                update_time = soup.find("h4")
                table = soup.find("table", id="Table")
                tbody = table.find("tbody", class_="Table_Body")
                trs = tbody.find_all("tr")
                del trs[-1]

                embed = discord.Embed(
                    title="".join(title.text.split()),
                    color=0xFF5733
                )
                update_text = " ".join(update_time.text.split()[0:2])
                embed.add_field(
                    name="",
                    value=update_text,
                    inline=False
                )

                for tr in trs:
                    city_name = tr.find("td").text.strip()
                    stop_info = tr.find("td").find_next("td").text.strip()
                    embed.add_field(
                        name=city_name,
                        value=stop_info,
                        inline=False
                    )

                # 發送到所有已設定的伺服器頻道
                for guild in self.bot.guilds:
                    channel_id = self.channel_config.get_channel_id(
                        guild.id,
                        "stop_work"
                    )
                    if channel_id:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            await channel.send(embed=embed)

    @check_stop_work_class.before_loop
    async def before_check_stop_work_class(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(StopWorkClassCog(bot))
