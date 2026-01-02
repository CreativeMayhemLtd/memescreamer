import asyncio
from twitchio.ext import commands
from loguru import logger
from src.database import QueueDatabase
from src.models import QueueItem, QueueStatus
from src.streamer import StreamWorker
from src.config import settings


class TwitchBot(commands.Bot):
    def __init__(self, db: QueueDatabase, worker: StreamWorker):
        super().__init__(
            token=settings.twitch_bot_token,
            prefix="!",
            initial_channels=settings.twitch_channel_list
        )
        self.db = db
        self.worker = worker
        
        # Copyright/legal disclaimer shown on first request per user per session
        self._warned_users: set[str] = set()

    async def event_ready(self):
        logger.info(f"Twitch bot connected as {self.nick}")
        logger.info(f"Joined channels: {settings.twitch_channel_list}")

    async def event_message(self, message):
        if message.echo:
            return
        await self.handle_commands(message)

    @commands.command(name="request", aliases=["req", "sr"])
    async def request_command(self, ctx, *, args: str = None):
        """
        Request a song/video. 
        Usage: !request <media_url> [promo_url]
        Example: !request https://example.com/song.mp3 https://youtube.com/watch?v=xxx
        """
        if not args:
            await ctx.send(
                f"@{ctx.author.name} Usage: !request <media_url> [optional_promo_link] | "
                f"Example: !request https://clips.twitch.tv/xxx https://youtube.com/mychannel"
            )
            return

        # Show copyright warning to new users
        if ctx.author.name.lower() not in self._warned_users:
            self._warned_users.add(ctx.author.name.lower())
            await ctx.send(
                f"@{ctx.author.name} ⚠️ NOTICE: By submitting content, you confirm you have "
                f"the rights to share it. No copyrighted, illegal, hateful, or NSFW content. "
                f"Violations may result in a ban."
            )
            await asyncio.sleep(1)  # Brief pause so warning is seen

        # Parse URL and optional promo link
        parts = args.strip().split()
        url = parts[0]
        promo_link = parts[1] if len(parts) > 1 else None

        # Basic URL validation for media URL
        if not any(domain in url.lower() for domain in [
            "twitch.tv", "youtube.com", "youtu.be", "clips.twitch.tv",
            ".mp4", ".mp3", ".webm"
        ]):
            await ctx.send(f"@{ctx.author.name} Please provide a valid Twitch/YouTube URL or direct media link")
            return

        # Validate promo link if provided
        if promo_link:
            if not any(domain in promo_link.lower() for domain in [
                "youtube.com", "youtu.be", "soundcloud.com", "spotify.com",
                "bandcamp.com", "twitter.com", "x.com", "instagram.com"
            ]):
                await ctx.send(
                    f"@{ctx.author.name} Promo link should be YouTube, SoundCloud, Spotify, "
                    f"Bandcamp, or social media. Skipping promo link."
                )
                promo_link = None

        item = QueueItem(
            url=url,
            submitted_by=ctx.author.name,
            promo_link=promo_link
        )

        position = await self.db.enqueue(item)
        
        promo_msg = f" (promo: {promo_link[:30]}...)" if promo_link else ""
        await ctx.send(f"@{ctx.author.name} Added to queue at position #{position}{promo_msg}")
        logger.info(f"Queued: {url} by {ctx.author.name} (promo: {promo_link})")

    @commands.command(name="queue", aliases=["q"])
    async def queue_command(self, ctx):
        """Show the current queue."""
        queue = await self.db.get_queue(limit=5)

        if not queue:
            await ctx.send("Queue is empty!")
            return

        items = [f"{i+1}. {item.title[:30]} ({item.submitted_by})" 
                 for i, item in enumerate(queue)]
        await ctx.send(f"Queue: {' | '.join(items)}")

    @commands.command(name="np", aliases=["nowplaying", "song", "current"])
    async def now_playing_command(self, ctx):
        """Show what's currently playing."""
        item = await self.db.get_now_playing()

        if not item:
            await ctx.send("Nothing currently playing")
            return

        await ctx.send(f"Now playing: {item.title} (requested by {item.submitted_by})")

    @commands.command(name="skip")
    async def skip_command(self, ctx):
        """Skip current item (mod/broadcaster only)."""
        if not (ctx.author.is_mod or ctx.author.is_broadcaster):
            await ctx.send(f"@{ctx.author.name} Only mods can skip!")
            return

        await self.worker.skip()
        await ctx.send("Skipping current item...")

    @commands.command(name="clear")
    async def clear_command(self, ctx):
        """Clear the queue (broadcaster only)."""
        if not ctx.author.is_broadcaster:
            await ctx.send(f"@{ctx.author.name} Only the broadcaster can clear the queue!")
            return

        await self.db.clear_queue()
        await ctx.send("Queue cleared!")

    @commands.command(name="help", aliases=["commands"])
    async def help_command(self, ctx):
        """Show available commands."""
        await ctx.send(
            "Commands: !request <url> [promo_link] | !queue | !np | !skip (mod) | !clear (broadcaster)"
        )
