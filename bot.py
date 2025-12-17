import os
import discord
import logging
import yt_dlp
import asyncio
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from collections import deque

load_dotenv()
TOKEN = os.getenv('TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))

SONG_QUEUES = {}

async def search_youtube(query, ydl_options):
  loop = asyncio.get_event_loop()
  return await loop.run_in_executor(None, lambda: _extract(query, ydl_options))

def _extract(query, ydl_options):
  with yt_dlp.YoutubeDL(ydl_options) as ydl:
    return ydl.extract_info(query, download=False)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
  test_guild = discord.Object(id=GUILD_ID)
  await bot.tree.sync(guild=test_guild)
  await bot.tree.sync()
  print("Bot está pronto.")

@bot.tree.command(name="play", description="Toca uma música no canal de voz.")
@app_commands.describe(query="A música que você quer tocar.")
async def play(interaction: discord.Interaction, query: str):
  await interaction.response.defer()

  voice_channel = interaction.user.voice.channel

  if not voice_channel:
    return await interaction.followup.send(
      content="Você precisa estar em um canal de voz para usar este comando.",
      ephemeral=True
    )

  voice_client = interaction.guild.voice_client

  if not voice_client:
    voice_client = await voice_channel.connect()
  elif voice_client.channel != voice_channel:
    await voice_client.move_to(voice_channel)

  ydl_options = {
    'format': 'bestaudio[abr<=96]/bestaudio',
    'noplaylist': True,
    'youtube_include_dash_manifest': False,
    'youtube_include_hls_manifest': False,
  }

  query = f"ytsearch:{query}"
  results = await search_youtube(query, ydl_options)
  tracks = results.get('entries', [])

  if not tracks:
    await interaction.followup.send("Nenhuma música encontrada para a consulta fornecida.")
    return

  track = tracks[0]
  url = track['url']
  title = track.get('title', 'Titulo desconhecido')

  guild_id = str(interaction.guild.id)
  if(SONG_QUEUES.get(guild_id) is None):
    SONG_QUEUES[guild_id] = deque()
  
  SONG_QUEUES[guild_id].append((url, title))

  if voice_client.is_playing():
    await interaction.followup.send(f"Adicionado à fila: {title}")
  else:
    await interaction.followup.send(f"Tocando agora: {title}")
    await play_next(voice_client, guild_id, voice_channel)

@bot.tree.command(name="skip", description="Pula a música atual.")
async def skip(interaction: discord.Interaction):
  if(interaction.guild.voice_client is None or not interaction.guild.voice_client.is_playing()):
    await interaction.response.send_message("Nenhuma música está sendo tocada no momento.", ephemeral=True)
    return
  
  interaction.guild.voice_client.stop()
  await interaction.response.send_message("Música atual pulada.")

@bot.tree.command(name="pause", description="Pause a reprodução.")
async def pause(interaction: discord.Interaction):
  voice_client = interaction.guild.voice_client

  if(voice_client is None or not voice_client.is_playing()):
    await interaction.response.send_message("Nenhuma música está sendo tocada no momento.", ephemeral=True)
    return

  voice_client.pause()
  await interaction.response.send_message("Reprodução pausada.")

@bot.tree.command(name="resume", description="Retoma a reprodução.")
async def resume(interaction: discord.Interaction):
  voice_client = interaction.guild.voice_client

  if(voice_client is None or not voice_client.is_paused()):
    await interaction.response.send_message("A reprodução não está pausada no momento.", ephemeral=True)
    return

  voice_client.resume()
  await interaction.response.send_message("Reprodução retomada.")

@bot.tree.command(name="stop", description="Para a reprodução e desconecta do canal de voz.")
async def stop(interaction: discord.Interaction):
  voice_client = interaction.guild.voice_client

  if not voice_client or not voice_client.is_connected():
    return await interaction.response.send_message("Não estou conectado em nenhum canal de voz.", ephemeral=True)

  guild_id_str = str(interaction.guild.id)

  if guild_id_str in SONG_QUEUES:
    SONG_QUEUES[guild_id_str].clear()

  if voice_client.is_playing() or voice_client.is_paused():
    voice_client.stop()

  await voice_client.disconnect()
  await interaction.response.send_message("Desconectado do canal de voz e parada a reprodução.")
  
async def play_next(voice_client, guild_id, channel):
  if SONG_QUEUES[guild_id]:
    url, title = SONG_QUEUES[guild_id].popleft()

    ffmpeg_options = {
      'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
      'options': '-vn -c:a libopus -b:a 96k',
    }

    source = discord.FFmpegOpusAudio(url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")

    def after_playing(error):
      if error:
        print(f"Erro ao tocar música: {error}")
      asyncio.run_coroutine_threadsafe(
        play_next(voice_client, guild_id, channel),
        bot.loop
      )

    voice_client.play(source, after=after_playing)
    asyncio.create_task(channel.send(f"Tocando agora: {title}"))

  else:
    await voice_client.disconnect()
    SONG_QUEUES[guild_id] = deque()

bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
