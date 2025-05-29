import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import re
import aiohttp
from yt_dlp import YoutubeDL

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'default_search': 'ytsearch',  # 這是關鍵！讓 yt_dlp 支援直接搜尋
    'extract_flat': False,
    'nocheckcertificate': True,
    'ignoreerrors': True,
}

ytdl = YoutubeDL(YTDL_OPTIONS)

def is_url(text):
    return re.match(r'https?://', text) is not None

class Song:
    def __init__(self, info):
        self.title = info.get('title')
        self.url = info.get('webpage_url') or info.get('url')
        self.duration = info.get('duration')  # 單位為秒

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}       # guild_id -> [Song,...]
        self.volumes = {}      # guild_id -> float (0.0~1.0)
        self.loop_modes = {}   # guild_id -> str ('off', 'one', 'all')

    def get_queue(self, guild_id):
        return self.queues.setdefault(guild_id, [])

    def get_volume(self, guild_id):
        return self.volumes.get(guild_id, 0.5)

    def set_volume(self, guild_id, volume):
        self.volumes[guild_id] = volume

    def get_loop_mode(self, guild_id):
        return self.loop_modes.get(guild_id, 'off')

    def set_loop_mode(self, guild_id, mode):
        self.loop_modes[guild_id] = mode
    
    async def add_to_queue(self, guild_id, info):
        song = Song(info)
        self.get_queue(guild_id).append(song)

    async def play_next(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        voice = interaction.guild.voice_client
        queue = self.get_queue(guild_id)

        if not queue:
            await interaction.followup.send("播放清單已空。")
            return

        song = queue[0]

        info = ytdl.extract_info(song.url, download=False)
        # ytsearch 可能回多個，取第一個
        if 'entries' in info:
            info = info['entries'][0]

        url = info.get('url') or song.url

        def after_play(error):
            if error:
                print(f"播放錯誤: {error}")

            mode = self.get_loop_mode(guild_id)
            if mode != 'one':
                if mode == 'all':
                    queue.append(queue.pop(0))
                else:
                    queue.pop(0)

            fut = self.play_next(interaction)
            asyncio.run_coroutine_threadsafe(fut, self.bot.loop)

        volume = self.get_volume(guild_id)
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), volume=volume)
        voice.play(source, after=after_play)

        embed = discord.Embed(title="▶️ 現在播放", description=f"[{song.title}]({song.url})", color=discord.Color.green())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="join", description="加入你的語音頻道")
    async def join(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("你不在語音頻道中！", ephemeral=True)
            return
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if vc:
            await vc.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f"已加入 {channel.name}")

    @app_commands.command(name="leave", description="離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("已離開語音頻道")
        else:
            await interaction.response.send_message("我不在語音頻道中", ephemeral=True)

    @app_commands.command(name="play", description="播放音樂(可輸入網址或關鍵字)")
    @app_commands.describe(query="YouTube 連結或歌曲名稱")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)

        if not is_url(query):
            query = f"ytsearch:{query}"

        info = await asyncio.to_thread(ytdl.extract_info, query, download=False)

        songs_added = 0

        if 'entries' in info:  # 播放清單或搜尋結果
            for entry in info['entries']:
                if entry:
                    await self.add_to_queue(guild_id, {
                        'webpage_url': entry['webpage_url'],
                        'title': entry['title'],
                        'duration': entry['duration']
                    })
                    songs_added += 1
            await interaction.followup.send(f"📃 播放清單已加入 {songs_added} 首歌曲。")
        else:  # 單一影片
            await self.add_to_queue(guild_id, {
                'webpage_url': info['webpage_url'],
                'title': info['title'],
                'duration': info['duration']
            })
            await interaction.followup.send(f"🎶 正在播放: {info['title']}")

        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
            if not interaction.guild.voice_client:
                if interaction.user.voice:
                    await interaction.user.voice.channel.connect()
                else:
                    await interaction.followup.send("請先加入語音頻道或讓我加入。")
                    return
            await self.play_next(interaction)

    @app_commands.command(name="pause", description="暫停播放")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ 已暫停播放")
        else:
            await interaction.response.send_message("沒有正在播放的音樂", ephemeral=True)

    @app_commands.command(name="resume", description="繼續播放")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ 已繼續播放")
        else:
            await interaction.response.send_message("沒有暫停的音樂", ephemeral=True)

    @app_commands.command(name="skip", description="跳過目前歌曲")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭ 已跳過歌曲")
        else:
            await interaction.response.send_message("沒有正在播放的音樂", ephemeral=True)

    @app_commands.command(name="queue", description="顯示播放清單")
    async def queue(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            await interaction.response.send_message("播放清單是空的", ephemeral=True)
            return

        text = ""
        for i, song in enumerate(queue[:10], start=1):
            text += f"{i}. [{song.title}]({song.url})\n"

        if len(queue) > 10:
            text += f"...還有 {len(queue)-10} 首歌曲"

        embed = discord.Embed(title="🎵 播放清單", description=text, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="顯示目前播放歌曲")
    async def nowplaying(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            await interaction.response.send_message("目前沒有播放歌曲", ephemeral=True)
            return
        song = queue[0]
        embed = discord.Embed(title="🎶 目前播放", description=f"[{song.title}]({song.url})", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loop", description="切換循環模式 (off / one / all)")
    async def loop(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        mode = self.get_loop_mode(guild_id)
        new_mode = {'off': 'one', 'one': 'all', 'all': 'off'}[mode]
        self.set_loop_mode(guild_id, new_mode)
        await interaction.response.send_message(f"循環模式已切換為 `{new_mode}`")

    @app_commands.command(name="clearqueue", description="清空播放清單")
    async def clearqueue(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        self.queues[guild_id] = []
        await interaction.response.send_message("播放清單已清空")

    @app_commands.command(name="volume", description="設定播放音量 0~100")
    @app_commands.describe(volume="音量百分比")
    async def volume(self, interaction: discord.Interaction, volume: int):
        if not 0 <= volume <= 100:
            await interaction.response.send_message("請輸入 0~100 之間的整數", ephemeral=True)
            return

        guild_id = interaction.guild.id
        self.set_volume(guild_id, volume / 100)

        vc = interaction.guild.voice_client
        if vc and vc.source and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = volume / 100

        await interaction.response.send_message(f"🔊 音量已設定為 {volume}%")

    @app_commands.command(name="lyrics", description="查詢歌詞")
    @app_commands.describe(song="歌曲名稱與歌手，例如：周杰倫 稻香")
    async def lyrics(self, interaction: discord.Interaction, song: str):
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            # 這個 API 用法：/v1/artist/title
            parts = song.split(maxsplit=1)
            artist = parts[0] if len(parts) > 0 else ""
            title = parts[1] if len(parts) > 1 else artist

            url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lyrics = data.get("lyrics", "找不到歌詞。")
                    if len(lyrics) > 4000:
                        lyrics = lyrics[:4000] + "\n...（歌詞過長已截斷）"
                    embed = discord.Embed(title=f"🎶 歌詞：{song}", description=lyrics, color=discord.Color.green())
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"❌ 找不到 `{song}` 的歌詞")

async def setup(bot):
    await bot.add_cog(Music(bot))
