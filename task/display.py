import discord
import time
from discord.ext import commands, tasks


class TaskBase(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 開始執行函式
        self.count.start()
        self.start_time = time.time()

    def cog_unload(self):
        # 取消執行函式
        self.count.cancel()

    # 定義要執行的循環函式
    @tasks.loop(seconds=6)
    async def count(self):
        # 偵測所在伺服器數
        guilds = len(self.bot.guilds)
        # 偵測使用者人數
        count = sum(len(guild.members) for guild in self.bot.guilds)
        try:
            # 等待bot ready
            await self.bot.wait_until_ready()
            # 變更bot狀態
            await self.bot.change_presence(
                activity=discord.Game(
                    name=f"{guilds}個伺服器 | {count}個人"
                )
            )

        except Exception as erro:
            # 錯誤輸出
            print(erro)


async def setup(bot):
    await bot.add_cog(TaskBase(bot))
