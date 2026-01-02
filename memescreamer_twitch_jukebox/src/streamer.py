import asyncio
from loguru import logger
from src.database import QueueDatabase
from src.downloader import Downloader
from src.moderator import ContentModerator
from src.ffmpeg import FFmpegStreamer
from src.models import QueueItem, QueueStatus
from src.config import settings


class StreamWorker:
    """Main worker that processes the queue and streams to Twitch."""

    def __init__(self, db: QueueDatabase):
        self.db = db
        self.downloader = Downloader()
        self.moderator = ContentModerator()
        self.ffmpeg = FFmpegStreamer()
        self.running = False
        self.current_item: QueueItem | None = None

    async def start(self):
        """Start the streaming worker loop."""
        self.running = True
        logger.info("Stream worker started")

        while self.running:
            try:
                item = await self.db.dequeue()

                if not item:
                    logger.debug("Queue empty, streaming idle...")
                    await self.ffmpeg.stream_idle(duration=30)
                    continue

                await self._process_item(item)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(5)

    async def _process_item(self, item: QueueItem):
        """Process a single queue item."""
        self.current_item = item
        logger.info(f"Processing: {item.url} (requested by {item.submitted_by})")

        try:
            # Download
            await self.db.update_status(item.id, QueueStatus.DOWNLOADING)
            item = await self.downloader.download(item)

            if item.error_message or not item.file_path:
                await self.db.update_status(item.id, QueueStatus.FAILED, item.error_message)
                return

            # Moderate
            approved, reason = await self.moderator.check(item.file_path)
            if not approved:
                await self.db.update_status(item.id, QueueStatus.FAILED, reason)
                self.downloader.cleanup(item)
                return

            # Stream
            await self.db.update_status(item.id, QueueStatus.PLAYING)
            await self.db.update_item(item)
            success = await self.ffmpeg.stream_file(
                item.file_path,
                title=item.title,
                submitted_by=item.submitted_by,
                promo_link=item.promo_link
            )

            # Cleanup
            status = QueueStatus.DONE if success else QueueStatus.FAILED
            await self.db.update_status(item.id, status)
            self.downloader.cleanup(item)

        except Exception as e:
            logger.error(f"Error processing {item.id}: {e}")
            await self.db.update_status(item.id, QueueStatus.FAILED, str(e))
            if item.file_path:
                self.downloader.cleanup(item)
        finally:
            self.current_item = None

    async def skip(self):
        """Skip the current item."""
        if self.current_item:
            logger.info(f"Skipping: {self.current_item.title}")
            await self.ffmpeg.skip()

    def stop(self):
        """Stop the worker."""
        self.running = False
