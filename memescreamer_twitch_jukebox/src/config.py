from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    # Twitch Bot
    twitch_bot_token: str
    twitch_bot_nick: str
    twitch_channels: str  # comma-separated

    # Twitch Stream Output
    twitch_stream_key: str

    # Moderation
    content_filter_script: Path = Path("/app/content_filter.sh")
    max_duration_seconds: int = 600
    max_file_size_mb: int = 500

    # Paths
    media_dir: Path = Path("/app/media")
    database_path: Path = Path("/app/data/queue.db")

    # Stream Settings
    stream_bitrate_video: str = "3000k"
    stream_bitrate_audio: str = "128k"
    stream_preset: str = "veryfast"
    idle_image: Path = Path("/app/assets/idle.png")

    @property
    def twitch_channel_list(self) -> list[str]:
        return [c.strip() for c in self.twitch_channels.split(",")]

    @property
    def twitch_rtmp_url(self) -> str:
        return f"rtmp://live.twitch.tv/app/{self.twitch_stream_key}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
