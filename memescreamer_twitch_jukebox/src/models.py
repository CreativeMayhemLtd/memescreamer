from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from pathlib import Path
import uuid


class QueueStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PLAYING = "playing"
    DONE = "done"
    FAILED = "failed"


class QueueItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    file_path: Path | None = None
    title: str = "Unknown"
    duration_seconds: float | None = None
    submitted_by: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    status: QueueStatus = QueueStatus.PENDING
    error_message: str | None = None
    promo_link: str | None = None  # Optional "hear more at" link

    class Config:
        use_enum_values = True
