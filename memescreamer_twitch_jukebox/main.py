import asyncio
import signal
from loguru import logger
from src.config import settings
from src.database import QueueDatabase
from src.streamer import StreamWorker
from src.bot import TwitchBot


async def main():
    # Setup logging
    logger.add(
        "logs/memescreamer_twitch_jukebox_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )

    logger.info("Starting memescreamer_twitch_jukebox Bot")

    # Initialize database
    db = QueueDatabase(settings.database_path)
    await db.init()

    # Create worker and bot
    worker = StreamWorker(db)
    bot = TwitchBot(db, worker)

    # Handle shutdown
    loop = asyncio.get_event_loop()
    
    def shutdown():
        logger.info("Shutting down...")
        worker.stop()
        loop.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    # Start everything
    try:
        await asyncio.gather(
            worker.start(),
            bot.start()
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("memescreamer_twitch_jukebox Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
