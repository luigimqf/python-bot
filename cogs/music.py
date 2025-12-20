import discord
import yt_dlp
import asyncio
import re
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from discord.ext import commands
from discord import app_commands
from collections import deque
from utils.embeds import create_music_embed, create_error_embed, create_success_embed


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queues = {}
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
        ))

    def is_spotify_url(self, url: str) -> bool:
        return 'spotify.com' in url or 'open.spotify' in url

    async def get_spotify_tracks(self, url: str):
        if 'track' in url:
            track = self.spotify.track(url)
            return [{
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'search_query': f"{track['artists'][0]['name']} - {track['name']}"
            }]
        elif 'playlist' in url:
            playlist_id = re.search(r'playlist/([a-zA-Z0-9]+)', url).group(1)
            results = self.spotify.playlist_items(playlist_id)
            tracks = []
            for item in results['items']:
                track = item['track']
                tracks.append({
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'search_query': f"{track['artists'][0]['name']} - {track['name']}"
                })
            return tracks
        return []
    
    async def search_youtube(self, query, ydl_options):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._extract(query, ydl_options))

    def _extract(self, query, ydl_options):
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            return ydl.extract_info(query, download=False)

    async def play_next(self, voice_client, guild_id, channel):
        if self.song_queues[guild_id]:
            url, title = self.song_queues[guild_id].popleft()

            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn -c:a libopus -b:a 96k',
            }

            source = discord.FFmpegOpusAudio(url, **ffmpeg_options, executable="bin\\ffmpeg\\ffmpeg.exe")

            def after_playing(error):
                if error:
                    print(f"Erro ao tocar música: {error}")
                asyncio.run_coroutine_threadsafe(
                    self.play_next(voice_client, guild_id, channel),
                    self.bot.loop
                )

            voice_client.play(source, after=after_playing)
            
            embed = create_music_embed("Tocando Agora", f"**{title}**")
            asyncio.create_task(channel.send(embed=embed))
        else:
            await voice_client.disconnect()
            self.song_queues[guild_id] = deque()

    @app_commands.command(name="play", description="Toca uma música no canal de voz.")
    @app_commands.describe(query="A música que você quer tocar.")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = create_error_embed("Você precisa estar em um canal de voz para usar este comando.")
            return await interaction.followup.send(embed=embed, ephemeral=True)

        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if not voice_client:
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

        guild_id = str(interaction.guild.id)
        if self.song_queues.get(guild_id) is None:
            self.song_queues[guild_id] = deque()

        ydl_options = {
            'format': 'bestaudio[abr<=96]/bestaudio',
            'noplaylist': True,
            'youtube_include_dash_manifest': False,
            'youtube_include_hls_manifest': False,
        }

        if self.is_spotify_url(query):
            try:
                spotify_tracks = await self.get_spotify_tracks(query)
                
                if not spotify_tracks:
                    embed = create_error_embed("Não foi possível processar o link do Spotify.")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                added_count = 0
                for spotify_track in spotify_tracks:
                    search_query = f"ytsearch:{spotify_track['search_query']}"
                    results = await self.search_youtube(search_query, ydl_options)
                    tracks = results.get('entries', [])
                    
                    if tracks:
                        track = tracks[0]
                        url = track['url']
                        title = f"{spotify_track['artist']} - {spotify_track['name']}"
                        self.song_queues[guild_id].append((url, title))
                        added_count += 1
                
                if added_count == 0:
                    embed = create_error_embed("Nenhuma música do Spotify foi encontrada no YouTube.")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                if added_count == 1:
                    title = f"{spotify_tracks[0]['artist']} - {spotify_tracks[0]['name']}"
                    if voice_client.is_playing():
                        embed = create_music_embed("Adicionado à Fila (Spotify)", f"**{title}**")
                        embed.add_field(name="Posição na fila", value=f"{len(self.song_queues[guild_id])}", inline=True)
                        await interaction.followup.send(embed=embed)
                    else:
                        embed = create_music_embed("Tocando Agora (Spotify)", f"**{title}**")
                        await interaction.followup.send(embed=embed)
                        await self.play_next(voice_client, guild_id, voice_channel)
                else:
                    embed = create_music_embed("Playlist/Álbum Adicionado (Spotify)", f"**{added_count} músicas** adicionadas à fila")
                    await interaction.followup.send(embed=embed)
                    if not voice_client.is_playing():
                        await self.play_next(voice_client, guild_id, voice_channel)
                    
            except Exception as e:
                embed = create_error_embed(f"Erro ao processar link do Spotify: {str(e)}")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        else:
            search_query = f"ytsearch:{query}"
            results = await self.search_youtube(search_query, ydl_options)
            tracks = results.get('entries', [])

            if not tracks:
                embed = create_error_embed("Nenhuma música encontrada para a consulta fornecida.")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            track = tracks[0]
            url = track['url']
            title = track.get('title', 'Título desconhecido')
            
            self.song_queues[guild_id].append((url, title))

            if voice_client.is_playing():
                embed = create_music_embed("Adicionado à Fila", f"**{title}**")
                embed.add_field(name="Posição na fila", value=f"{len(self.song_queues[guild_id])}", inline=True)
                await interaction.followup.send(embed=embed)
            else:
                embed = create_music_embed("Tocando Agora", f"**{title}**")
                await interaction.followup.send(embed=embed)
                await self.play_next(voice_client, guild_id, voice_channel)

    @app_commands.command(name="skip", description="Pula a música atual.")
    async def skip(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        
        if voice_client is None or not voice_client.is_playing():
            embed = create_error_embed("Nenhuma música está sendo tocada no momento.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        voice_client.stop()
        embed = create_success_embed("Música pulada com sucesso!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="Pausa a reprodução.")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None or not voice_client.is_playing():
            embed = create_error_embed("Nenhuma música está sendo tocada no momento.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        voice_client.pause()
        embed = create_success_embed("Reprodução pausada.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resume", description="Retoma a reprodução.")
    async def resume(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None or not voice_client.is_paused():
            embed = create_error_embed("A reprodução não está pausada no momento.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        voice_client.resume()
        embed = create_success_embed("Reprodução retomada.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="Para a reprodução e desconecta do canal de voz.")
    async def stop(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if not voice_client or not voice_client.is_connected():
            embed = create_error_embed("Não estou conectado em nenhum canal de voz.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        guild_id_str = str(interaction.guild.id)

        if guild_id_str in self.song_queues:
            self.song_queues[guild_id_str].clear()

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        await voice_client.disconnect()
        embed = create_success_embed("Desconectado do canal de voz e reprodução parada.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="queue", description="Mostra as músicas na fila.")
    async def queue(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        
        if guild_id not in self.song_queues or not self.song_queues[guild_id]:
            embed = create_error_embed("A fila está vazia.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        queue_list = []
        for i, (url, title) in enumerate(self.song_queues[guild_id], 1):
            queue_list.append(f"{i}. {title}")
        
        queue_text = "\n".join(queue_list[:10])
        if len(self.song_queues[guild_id]) > 10:
            queue_text += f"\n\n... e mais {len(self.song_queues[guild_id]) - 10} música(s)"
        
        embed = create_music_embed("Fila de Músicas", queue_text)
        embed.set_footer(text=f"Total: {len(self.song_queues[guild_id])} música(s)")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))
