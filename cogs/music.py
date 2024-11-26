from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import random
from aiohttp import ClientSession
import re
import urllib.request
import urllib.parse
from dotenv import load_dotenv
import os
import yt_dlp
import asyncio
from discord.ext import commands
import discord
type = "nodejs"
project = "Discord Music Bot"
file = "music_cog.py"


load_dotenv()

youtube_base_url = 'https://www.youtube.com/'
youtube_results_url = youtube_base_url + 'results?'
youtube_watch_url = youtube_base_url + 'watch?v='

yt_dl_options = {
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "age_limit": 21,
    "cookiefile": "youtube_cookies.txt",
    "extract_flat": True,
    "skip_download": True,
    "no_check_certificate": True,
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=1"'
}

ytdl = yt_dlp.YoutubeDL(yt_dl_options)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.voice_clients = {}
        self.current_songs = {}
        self.loop = {}
        self.playlists = {}
        self.loading_playlists = set()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        self.spotify_client = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
        ))

    async def get_random_image(self):
        safe_categories = ['smile', 'wave', 'thumbsup', 'dance']
        category = random.choice(safe_categories)
        async with ClientSession() as session:
            async with session.get(f'https://nekos.best/api/v2/{category}') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'results' in data and len(data['results']) > 0:
                        return data['results'][0].get('url')
        return 'https://example.com/default_image.png'

    async def create_embed(self, title, description, color=discord.Color.blue()):
        embed = discord.Embed(
            title=title, description=description, color=color)
        try:
            image_url = await self.get_random_image()
            embed.set_image(url=image_url)
        except Exception as e:
            print(f"Error getting image: {e}")
        return embed

    async def send_embed(self, ctx, title, description, color=discord.Color.blue()):
        embed = await self.create_embed(title, description, color)
        await ctx.send(embed=embed)

    async def play_next(self, ctx):
        if ctx.guild.id in self.queues and self.queues[ctx.guild.id]:
            if self.loop.get(ctx.guild.id, False):
                self.queues[ctx.guild.id].append(
                    self.current_songs[ctx.guild.id])
            next_song = self.queues[ctx.guild.id].pop(0)
            await self.play_song(ctx, next_song)
        else:
            await self.send_embed(ctx, "Queue Empty", "Playback finished.")
            self.voice_clients[ctx.guild.id].stop()

    async def play_song(self, ctx, song):
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(song['url'], download=False))
            if data is None:
                await self.send_embed(ctx, "Error", f"Could not retrieve data for the song: {song['title']}", discord.Color.red())
                return
            song_url = data.get('url')
            if song_url is None:
                await self.send_embed(ctx, "Error", f"Could not get playable URL for the song: {song['title']}", discord.Color.red())
                return
            player = discord.FFmpegOpusAudio(song_url, **ffmpeg_options)
            if ctx.guild.id in self.voice_clients:
                self.voice_clients[ctx.guild.id].play(
                    player,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next(ctx),
                        self.bot.loop
                    ).result()
                )
                self.current_songs[ctx.guild.id] = song
                await self.send_embed(ctx, "Now Playing", song['title'])
            else:
                await self.send_embed(ctx, "Error", "Not connected to a voice channel.")
        except Exception as e:
            await self.handle_youtube_error(ctx, e)

    async def get_youtube_results(self, query):
        search_query = urllib.parse.urlencode({'search_query': query})
        content = urllib.request.urlopen(youtube_results_url + search_query)
        search_results = re.findall(
            r'/watch\?v=(.{11})', content.read().decode())
        return search_results[:5]

    async def get_video_info(self, video_id):
        url = youtube_watch_url + video_id
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        return {
            'url': url,
            'title': data['title'],
            'duration': data['duration'],
            'uploader': data['uploader']
        }

    async def process_song_selection(self, ctx, videos):
        description = "\n".join([
            f"{i}. {video['title']} - {video['uploader']
                                       } ({video['duration']} seconds)"
            for i, video in enumerate(videos, 1)
        ])
        description += "\n0. Go back"
        embed = await self.create_embed("Search Results", description)
        embed.set_footer(
            text="Please choose a video by entering a number from 0 to 5.")
        await ctx.send(embed=embed)

        def check(m):
            return (
                m.author == ctx.author and
                m.channel == ctx.channel and
                m.content.isdigit() and
                0 <= int(m.content) <= 5
            )

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            choice = int(msg.content)
            if choice == 0:
                return None
            return videos[choice - 1]
        except asyncio.TimeoutError:
            await self.send_embed(ctx, "Timeout", "You didn't choose a video in time.", discord.Color.red())
            return None

    async def process_spotify_track(self, ctx, track):
        try:
            song_name = f"{
                track['name']} - {', '.join([artist['name'] for artist in track['artists']])}"
            search_results = await self.get_youtube_results(song_name)
            if search_results:
                video_info = await self.get_video_info(search_results[0])
                if ctx.guild.id not in self.queues:
                    self.queues[ctx.guild.id] = []
                self.queues[ctx.guild.id].append(video_info)
                return True
        except Exception as e:
            await self.handle_youtube_error(ctx, e)
        return False

    async def load_remaining_playlist(self, ctx, tracks):
        guild_id = ctx.guild.id
        if guild_id not in self.loading_playlists:
            self.loading_playlists.add(guild_id)
            try:
                for track in tracks[1:]:
                    if guild_id not in self.loading_playlists:
                        break
                    await self.process_spotify_track(ctx, track)
                    await asyncio.sleep(0.5)
                await self.send_embed(ctx, "Playlist Loaded", f"Finished loading remaining {len(tracks)-1} tracks from playlist")
            finally:
                if guild_id in self.loading_playlists:
                    self.loading_playlists.remove(guild_id)

    async def handle_youtube_error(self, ctx, error):
        if "Sign in to confirm your age" in str(error):
            await self.send_embed(ctx, "Age Restriction", "This video is age-restricted. Trying to bypass...", discord.Color.yellow())
        elif "Sign in to this account" in str(error):
            await self.send_embed(ctx, "Login Required", "This video requires login. Trying to bypass...", discord.Color.yellow())
        else:
            await self.send_embed(ctx, "YouTube Error", f"An error occurred: {str(error)}", discord.Color.red())

    async def search_spotify_track(self, query):
        try:
            results = self.spotify_client.search(
                q=query, type='track', limit=5)
            tracks = results['tracks']['items']
            if not tracks:
                return None
            track_list = []
            for track in tracks:
                track_info = {
                    'name': track['name'],
                    'artists': [artist['name'] for artist in track['artists']],
                    'duration_ms': track['duration_ms'],
                    'preview_url': track['preview_url'],
                    'external_url': track['external_urls']['spotify']
                }
                track_list.append(track_info)
            return track_list
        except Exception as e:
            print(f"Error searching Spotify: {e}")
            return None

    async def process_spotify_track_selection(self, ctx, tracks):
        description = "\n".join([
            f"{i}. {
                track['name']} - {', '.join(track['artists'])} ({track['duration_ms']//1000}s)"
            for i, track in enumerate(tracks, 1)
        ])
        description += "\n0. Cancel"
        embed = await self.create_embed("Spotify Search Results", description)
        embed.set_footer(
            text="Please choose a track by entering a number from 0 to 5.")
        await ctx.send(embed=embed)

        def check(m):
            return (
                m.author == ctx.author and
                m.channel == ctx.channel and
                m.content.isdigit() and
                0 <= int(m.content) <= 5
            )

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
            choice = int(msg.content)
            if choice == 0:
                return None
            return tracks[choice - 1]
        except asyncio.TimeoutError:
            await self.send_embed(ctx, "Timeout", "You didn't choose a track in time.", discord.Color.red())
            return None

    @commands.command(name='play')
    async def play(self, ctx, *, query):
        await asyncio.sleep(random.uniform(1, 3))
        if ctx.author.voice is None:
            await self.send_embed(ctx, "Error", "You need to be in a voice channel to use this command.", discord.Color.red())
            return

        if ctx.guild.id not in self.voice_clients:
            voice_client = await ctx.author.voice.channel.connect()
            self.voice_clients[ctx.guild.id] = voice_client

        search_results = await self.get_youtube_results(query)
        if not search_results:
            await self.send_embed(ctx, "No Results", "No results found.", discord.Color.red())
            return

        videos = []
        for video_id in search_results:
            video_info = await self.get_video_info(video_id)
            videos.append(video_info)

        chosen_video = await self.process_song_selection(ctx, videos)
        if chosen_video is None:
            return

        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []

        self.queues[ctx.guild.id].append(chosen_video)

        if not self.voice_clients[ctx.guild.id].is_playing():
            await self.play_song(ctx, chosen_video)
        else:
            await self.send_embed(ctx, "Added to Queue", f"Added to queue: {chosen_video['title']}")

    @commands.command(name='playspt')
    async def playspt(self, ctx, *, query):
        await asyncio.sleep(random.uniform(1, 3))
        if ctx.author.voice is None:
            await self.send_embed(ctx, "Error", "You need to be in a voice channel to use this command.", discord.Color.red())
            return

        if ctx.guild.id not in self.voice_clients:
            voice_client = await ctx.author.voice.channel.connect()
            self.voice_clients[ctx.guild.id] = voice_client

        tracks = await self.search_spotify_track(query)
        if not tracks:
            await self.send_embed(ctx, "No Results", "No Spotify tracks found.", discord.Color.red())
            return

        chosen_track = await self.process_spotify_track_selection(ctx, tracks)
        if chosen_track is None:
            return

        search_query = f"{chosen_track['name']
                          } - {', '.join(chosen_track['artists'])}"
        youtube_results = await self.get_youtube_results(search_query)

        if not youtube_results:
            await self.send_embed(ctx, "Error", "Could not find a YouTube version of this track.", discord.Color.red())
            return

        video_info = await self.get_video_info(youtube_results[0])

        if ctx.guild.id not in self.queues:
            self.queues[ctx.guild.id] = []

        self.queues[ctx.guild.id].append(video_info)

        if not self.voice_clients[ctx.guild.id].is_playing():
            await self.play_song(ctx, video_info)
        else:
            await self.send_embed(ctx, "Added to Queue", f"Added to queue: {video_info['title']}")

    @commands.command()
    async def spotify(self, ctx, *, playlist_url: str):
        try:
            if ctx.author.voice is None:
                await self.send_embed(ctx, "Error", "You need to be in a voice channel to use this command.", discord.Color.red())
                return

            if ctx.guild.id not in self.voice_clients:
                voice_client = await ctx.author.voice.channel.connect()
                self.voice_clients[ctx.guild.id] = voice_client

            playlist_id = playlist_url.split('/')[-1].split('?')[0]
            results = self.spotify_client.playlist_tracks(playlist_id)
            tracks = results['items']

            if not tracks:
                await self.send_embed(ctx, "Error", "No tracks found in the playlist.", discord.Color.red())
                return

            first_track = tracks[0]['track']
            success = await self.process_spotify_track(ctx, first_track)

            if success:
                await self.send_embed(ctx, "Spotify Playlist", "Started playing first track. Loading remaining tracks in background...")
                if not self.voice_clients[ctx.guild.id].is_playing():
                    await self.play_next(ctx)
                asyncio.create_task(self.load_remaining_playlist(
                    ctx, [t['track'] for t in tracks]))
            else:
                await self.send_embed(ctx, "Error", "Failed to process the first track. Trying next track...", discord.Color.yellow())
                for track in tracks[1:]:
                    success = await self.process_spotify_track(ctx, track['track'])
                    if success:
                        await self.send_embed(ctx, "Spotify Playlist", "Started playing an alternative track. Loading remaining tracks in background...")
                        if not self.voice_clients[ctx.guild.id].is_playing():
                            await self.play_next(ctx)
                        asyncio.create_task(self.load_remaining_playlist(
                            ctx, [t['track'] for t in tracks]))
                        break
                else:
                    await self.send_embed(ctx, "Error", "Failed to process any tracks from the playlist.", discord.Color.red())
        except Exception as e:
            await self.send_embed(ctx, "Error", f"An error occurred: {str(e)}", discord.Color.red())

    @commands.command()
    async def stop_loading(self, ctx):
        if ctx.guild.id in self.loading_playlists:
            self.loading_playlists.remove(ctx.guild.id)
            await self.send_embed(ctx, "Stopped Loading", "Playlist loading has been cancelled.")
        else:
            await self.send_embed(ctx, "Error", "No playlist is currently being loaded.", discord.Color.red())

    @commands.command(name='pause')
    async def pause(self, ctx):
        if ctx.guild.id in self.voice_clients and self.voice_clients[ctx.guild.id].is_playing():
            self.voice_clients[ctx.guild.id].pause()
            await self.send_embed(ctx, "Paused", "Music paused.")
        else:
            await self.send_embed(ctx, "Error", "No music is playing.", discord.Color.red())

    @commands.command(name='resume')
    async def resume(self, ctx):
        if ctx.guild.id in self.voice_clients and self.voice_clients[ctx.guild.id].is_paused():
            self.voice_clients[ctx.guild.id].resume()
            await self.send_embed(ctx, "Resumed", "Resuming music.")
        else:
            await self.send_embed(ctx, "Error", "No music is paused.", discord.Color.red())

    @commands.command(name='skip')
    async def skip(self, ctx):
        if ctx.guild.id in self.voice_clients and self.voice_clients[ctx.guild.id].is_playing():
            self.voice_clients[ctx.guild.id].stop()
            await self.send_embed(ctx, "Skipped", "Skipped to next track.")
        else:
            await self.send_embed(ctx, "Error", "No music is playing.", discord.Color.red())

    @commands.command(name='queue')
    async def queue(self, ctx):
        if ctx.guild.id in self.queues and self.queues[ctx.guild.id]:
            queue_list = "\n".join(
                [f"{i+1}. {track['title']}" for i, track in enumerate(self.queues[ctx.guild.id])])
            await self.send_embed(ctx, "Current Queue", queue_list)
        else:
            await self.send_embed(ctx, "Queue Empty", "Queue is empty.")

    @commands.command(name='clear_queue')
    async def clear_queue(self, ctx):
        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id].clear()
            await self.send_embed(ctx, "Queue Cleared", "Queue cleared!")
        else:
            await self.send_embed(ctx, "Error", "There is no queue to clear", discord.Color.red())

    @commands.command(name='leave')
    async def leave(self, ctx):
        if ctx.guild.id in self.voice_clients:
            await self.voice_clients[ctx.guild.id].disconnect()
            del self.voice_clients[ctx.guild.id]
            await self.send_embed(ctx, "Disconnected", "Disconnected from voice channel.")
        else:
            await self.send_embed(ctx, "Error", "Not connected to a voice channel.", discord.Color.red())

    @commands.command(name='join')
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if ctx.guild.id not in self.voice_clients:
                voice_client = await channel.connect()
                self.voice_clients[ctx.guild.id] = voice_client
                await self.send_embed(ctx, "Joined", f"Joined {channel.name}")
            else:
                await self.send_embed(ctx, "Already Connected", "Already connected to a voice channel.")
        else:
            await self.send_embed(ctx, "Error", "You need to be in a voice channel to use this command.", discord.Color.red())

    @commands.command(name='loop')
    async def loop(self, ctx):
        self.loop[ctx.guild.id] = not self.loop.get(ctx.guild.id, False)
        status = "enabled" if self.loop[ctx.guild.id] else "disabled"
        await self.send_embed(ctx, "Loop", f"Loop {status}.")

    @commands.command(name='reboot')
    async def reboot(self, ctx):
        if ctx.guild.id in self.current_songs:
            await self.play_song(ctx, self.current_songs[ctx.guild.id])
            await self.send_embed(ctx, "Rebooted", "Rebooting current song.")
        else:
            await self.send_embed(ctx, "Error", "No song is currently playing.", discord.Color.red())


async def setup(bot):
    await bot.add_cog(Music(bot))

# Test the code
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')
    await setup(bot)
