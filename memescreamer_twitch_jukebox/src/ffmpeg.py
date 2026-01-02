import asyncio
from pathlib import Path
from loguru import logger
from src.config import settings


class FFmpegStreamer:
    """Handles FFmpeg streaming to Twitch."""

    def __init__(self):
        self.current_process: asyncio.subprocess.Process | None = None
        self._stop_requested = False

    def _build_drawtext_filter(self, title: str, submitted_by: str, promo_link: str | None) -> str:
        """Build FFmpeg drawtext filter for overlay text."""
        # Escape special characters for FFmpeg
        def escape(text: str) -> str:
            return text.replace("'", "'\\'").replace(":", "\\:").replace("\\", "\\\\")
        
        filters = []
        
        # Title and submitter at bottom
        title_text = escape(f"{title[:50]} - requested by {submitted_by}")
        filters.append(
            f"drawtext=text='{title_text}':fontsize=24:fontcolor=white:"
            f"borderw=2:bordercolor=black:x=20:y=h-60"
        )
        
        # Promo link if provided
        if promo_link:
            promo_text = escape(f"Hear more at: {promo_link}")
            filters.append(
                f"drawtext=text='{promo_text}':fontsize=20:fontcolor=yellow:"
                f"borderw=2:bordercolor=black:x=20:y=h-30"
            )
        
        return ",".join(filters)

    async def stream_file(self, file_path: Path, title: str = "Unknown", 
                          submitted_by: str = "Anonymous", promo_link: str | None = None) -> bool:
        """
        Stream a file to Twitch with optional text overlay.
        Returns True if completed successfully, False if failed/stopped.
        """
        self._stop_requested = False
        
        # Build video filter for text overlay
        vf_filter = self._build_drawtext_filter(title, submitted_by, promo_link)

        cmd = [
            "ffmpeg",
            "-re",  # Read at native framerate
            "-i", str(file_path),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", settings.stream_preset,
            "-b:v", settings.stream_bitrate_video,
            "-maxrate", settings.stream_bitrate_video,
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p",
            "-g", "50",  # Keyframe interval
            "-c:a", "aac",
            "-b:a", settings.stream_bitrate_audio,
            "-ar", "44100",
            "-f", "flv",
            settings.twitch_rtmp_url
        ]

        logger.info(f"Starting stream: {file_path.name}")
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        try:
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            _, stderr = await self.current_process.communicate()

            if self._stop_requested:
                logger.info("Stream stopped by request")
                return False

            if self.current_process.returncode != 0:
                logger.error(f"FFmpeg error: {stderr.decode()[-500:]}")
                return False

            logger.info(f"Stream completed: {file_path.name}")
            return True

        except Exception as e:
            logger.error(f"Stream error: {e}")
            return False
        finally:
            self.current_process = None

    async def stream_idle(self, duration: int = 10):
        """Stream idle screen for a duration (seconds)."""
        idle_image = settings.idle_image

        if not idle_image.exists():
            logger.warning("Idle image not found, sleeping instead")
            await asyncio.sleep(duration)
            return

        cmd = [
            "ffmpeg",
            "-loop", "1",
            "-i", str(idle_image),
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", settings.stream_preset,
            "-b:v", "1000k",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", settings.stream_bitrate_audio,
            "-f", "flv",
            settings.twitch_rtmp_url
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
        except Exception as e:
            logger.error(f"Idle stream error: {e}")
            await asyncio.sleep(duration)

    async def skip(self):
        """Stop current stream."""
        self._stop_requested = True
        if self.current_process:
            self.current_process.terminate()
            try:
                await asyncio.wait_for(self.current_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.current_process.kill()
