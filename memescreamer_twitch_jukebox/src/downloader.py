import asyncio
import json
from pathlib import Path
from loguru import logger
from src.config import settings
from src.models import QueueItem


class Downloader:
    def __init__(self):
        self.media_dir = settings.media_dir
        self.media_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, item: QueueItem) -> QueueItem:
        """Download media from URL, update item with file_path and metadata."""
        output_template = str(self.media_dir / f"{item.id}.%(ext)s")

        # First, get info without downloading
        info = await self._get_info(item.url)
        if not info:
            item.error_message = "Could not fetch media info"
            return item

        item.title = info.get("title", "Unknown")[:100]
        item.duration_seconds = info.get("duration")

        # Check duration
        if item.duration_seconds and item.duration_seconds > settings.max_duration_seconds:
            item.error_message = f"Duration {item.duration_seconds}s exceeds max {settings.max_duration_seconds}s"
            return item

        # Download
        logger.info(f"Downloading: {item.title}")
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--no-playlist",
            "--max-filesize", f"{settings.max_file_size_mb}m",
            item.url
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)

            if process.returncode != 0:
                logger.error(f"yt-dlp error: {stderr.decode()}")
                item.error_message = "Download failed"
                return item

            # Find the downloaded file
            downloaded_files = list(self.media_dir.glob(f"{item.id}.*"))
            if not downloaded_files:
                item.error_message = "Downloaded file not found"
                return item

            item.file_path = downloaded_files[0]
            logger.info(f"Downloaded: {item.file_path}")
            return item

        except asyncio.TimeoutError:
            item.error_message = "Download timed out"
            return item
        except Exception as e:
            item.error_message = f"Download error: {str(e)}"
            return item

    async def _get_info(self, url: str) -> dict | None:
        cmd = ["yt-dlp", "-j", "--no-playlist", url]
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

            if process.returncode != 0:
                return None

            return json.loads(stdout.decode())
        except:
            return None

    def cleanup(self, item: QueueItem):
        """Remove downloaded file."""
        if item.file_path and item.file_path.exists():
            item.file_path.unlink()
            logger.info(f"Cleaned up: {item.file_path}")
