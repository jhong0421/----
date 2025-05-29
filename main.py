import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    application_id=os.getenv('APPLICATION_ID'),
    heartbeat_timeout=150
)

# 自動加載模組


async def load_extensions():
    """動態載入所有 cogs 資料夾內的模組"""
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ 已加載模組: {filename[:-3]}")
            except Exception as e:
                print(f"❌ 無法加載模組 {filename}: {str(e)}")

    """動態載入所有 event 資料夾內的模組"""
    for filename in os.listdir("./event"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"event.{filename[:-3]}")
                print(f"✅ 已加載模組: {filename[:-3]}")
            except Exception as e:
                print(f"❌ 無法加載模組 {filename}: {str(e)}")

    """動態載入所有 task 資料夾內的模組"""
    for filename in os.listdir("./task"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"task.{filename[:-3]}")
                print(f"✅ 已加載模組: {filename[:-3]}")
            except Exception as e:
                print(f"❌ 無法加載模組 {filename}: {str(e)}")


@bot.event
async def on_ready():
    print(f"目前登入身份 --> {bot.user}")
    await load_extensions()
    await bot.tree.sync()
    slash = await bot.tree.sync()
    print(f"載入 {len(slash)} 個斜線指令")

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
