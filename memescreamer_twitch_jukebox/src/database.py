import aiosqlite
from pathlib import Path
from loguru import logger
from src.models import QueueItem, QueueStatus


class QueueDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS queue (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    file_path TEXT,
                    title TEXT,
                    duration_seconds REAL,
                    submitted_by TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    promo_link TEXT,
                    error_message TEXT,
                    position INTEGER
                )
            """)
            await db.commit()
        logger.info(f"Database initialized at {self.db_path}")

    async def enqueue(self, item: QueueItem) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM queue WHERE status = ?",
                (QueueStatus.PENDING,)
            )
            row = await cursor.fetchone()
            position = row[0]

            await db.execute("""
                INSERT INTO queue (id, url, file_path, title, duration_seconds, 
                                   submitted_by, submitted_at, status, error_message, promo_link, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.id,
                item.url,
                str(item.file_path) if item.file_path else None,
                item.title,
                item.duration_seconds,
                item.submitted_by,
                item.submitted_at.isoformat(),
                item.status,
                item.error_message,
                item.promo_link,
                position
            ))
            await db.commit()
            return position

    async def dequeue(self) -> QueueItem | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM queue 
                WHERE status = ? 
                ORDER BY position ASC 
                LIMIT 1
            """, (QueueStatus.PENDING,))
            row = await cursor.fetchone()

            if not row:
                return None

            item = QueueItem(
                id=row["id"],
                url=row["url"],
                file_path=Path(row["file_path"]) if row["file_path"] else None,
                title=row["title"],
                duration_seconds=row["duration_seconds"],
                submitted_by=row["submitted_by"],
                submitted_at=row["submitted_at"],
                status=row["status"],
                error_message=row["error_message"],
                promo_link=row["promo_link"]
            )
            return item

    async def update_status(self, item_id: str, status: QueueStatus, error: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE queue SET status = ?, error_message = ? WHERE id = ?
            """, (status, error, item_id))
            await db.commit()

    async def update_item(self, item: QueueItem):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE queue SET 
                    file_path = ?, title = ?, duration_seconds = ?, status = ?, error_message = ?
                WHERE id = ?
            """, (
                str(item.file_path) if item.file_path else None,
                item.title,
                item.duration_seconds,
                item.status,
                item.error_message,
                item.id
            ))
            await db.commit()

    async def get_queue(self, limit: int = 10) -> list[QueueItem]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM queue 
                WHERE status = ? 
                ORDER BY position ASC 
                LIMIT ?
            """, (QueueStatus.PENDING, limit))
            rows = await cursor.fetchall()

            return [QueueItem(
                id=row["id"],
                url=row["url"],
                file_path=Path(row["file_path"]) if row["file_path"] else None,
                title=row["title"],
                duration_seconds=row["duration_seconds"],
                submitted_by=row["submitted_by"],
                submitted_at=row["submitted_at"],
                status=row["status"],
                error_message=row["error_message"],
                promo_link=row["promo_link"]
            ) for row in rows]

    async def get_position(self, item_id: str) -> int | None:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM queue 
                WHERE status = ? AND position <= (
                    SELECT position FROM queue WHERE id = ?
                )
            """, (QueueStatus.PENDING, item_id))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def get_now_playing(self) -> QueueItem | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM queue WHERE status = ? LIMIT 1
            """, (QueueStatus.PLAYING,))
            row = await cursor.fetchone()

            if not row:
                return None

            return QueueItem(
                id=row["id"],
                url=row["url"],
                file_path=Path(row["file_path"]) if row["file_path"] else None,
                title=row["title"],
                duration_seconds=row["duration_seconds"],
                submitted_by=row["submitted_by"],
                submitted_at=row["submitted_at"],
                status=row["status"],
                error_message=row["error_message"],
                promo_link=row["promo_link"]
            )

    async def clear_queue(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM queue WHERE status = ?", (QueueStatus.PENDING,))
            await db.commit()

    async def remove_item(self, item_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM queue WHERE id = ?", (item_id,))
            await db.commit()
            return cursor.rowcount > 0
