import asyncio
import sys
from pathlib import Path
from loguru import logger
from src.config import settings

# Add hotdog_nothotdog to path for direct Python import
sys.path.insert(0, "/app/hotdog_nothotdog")

try:
    from Hotdog_NotHotDog import (
        load_model, encode_prompts, score_image_path, score_video_frames,
        _policy_decision, PROMPTS, CONFIG
    )
    HOTDOG_AVAILABLE = True
except ImportError:
    HOTDOG_AVAILABLE = False
    logger.warning("Hotdog_NotHotdog classifier not available, falling back to shell script")


class ContentModerator:
    """
    NSFW content filter using Hotdog_NotHotdog CLIP-based classifier.
    https://github.com/CreativeMayhemLtd/memescreamer_Hotdog_NotHotdog
    
    Falls back to shell script if Python import fails.
    """

    def __init__(self):
        self.script_path = settings.content_filter_script
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._device = None
        self._text_features = None
        self._initialized = False

    async def _init_model(self):
        """Lazy-load the CLIP model on first use."""
        if self._initialized or not HOTDOG_AVAILABLE:
            return
        
        try:
            logger.info("Loading Hotdog_NotHotdog CLIP model...")
            # Run in executor to not block async loop
            loop = asyncio.get_event_loop()
            self._model, self._preprocess, self._tokenizer, self._device = await loop.run_in_executor(
                None, load_model
            )
            self._text_features = await loop.run_in_executor(
                None, encode_prompts, PROMPTS, self._model, self._tokenizer, self._device
            )
            self._initialized = True
            logger.info(f"Hotdog_NotHotdog loaded on device: {self._device}")
        except Exception as e:
            logger.error(f"Failed to load Hotdog_NotHotdog: {e}")
            self._initialized = False

    async def check(self, file_path: Path) -> tuple[bool, str | None]:
        """
        Check content against NSFW classifier.
        Returns (approved: bool, rejection_reason: str | None)
        """
        # Try Python-based classifier first
        if HOTDOG_AVAILABLE:
            return await self._check_with_hotdog(file_path)
        
        # Fall back to shell script
        return await self._check_with_script(file_path)

    async def _check_with_hotdog(self, file_path: Path) -> tuple[bool, str | None]:
        """Use Hotdog_NotHotdog Python classifier directly."""
        await self._init_model()
        
        if not self._initialized:
            logger.warning("Hotdog_NotHotdog not initialized, falling back to script")
            return await self._check_with_script(file_path)

        try:
            loop = asyncio.get_event_loop()
            
            # Check if video or image
            video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
            is_video = file_path.suffix.lower() in video_exts
            
            if is_video:
                scores = await loop.run_in_executor(
                    None,
                    score_video_frames,
                    file_path,
                    self._model,
                    self._preprocess,
                    self._text_features,
                    self._device,
                    1.0,  # fps
                    32,   # batch_size
                    200   # max_frames
                )
            else:
                scores = await loop.run_in_executor(
                    None,
                    score_image_path,
                    str(file_path),
                    self._model,
                    self._preprocess,
                    self._text_features,
                    self._device,
                    32
                )
            
            # Use rules-based decision with default threshold
            decision, reason = _policy_decision(scores, {k: 0.20 for k in CONFIG})
            
            if decision == "nsfw":
                logger.warning(f"Content rejected (NSFW): {file_path.name} - {reason}")
                return False, f"NSFW content detected: {reason}"
            
            logger.info(f"Content approved (SFW): {file_path.name}")
            return True, None
            
        except Exception as e:
            logger.error(f"Hotdog_NotHotdog error: {e}")
            # On error, fall back to script
            return await self._check_with_script(file_path)

    async def _check_with_script(self, file_path: Path) -> tuple[bool, str | None]:
        """Fall back to shell script for content filtering."""
        if not self.script_path.exists():
            logger.warning(f"Content filter script not found: {self.script_path}")
            return True, None  # Allow if no script

        try:
            process = await asyncio.create_subprocess_exec(
                str(self.script_path),
                str(file_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

            if process.returncode == 0:
                logger.info(f"Content approved: {file_path.name}")
                return True, None
            else:
                reason = stdout.decode().strip() or stderr.decode().strip() or "Content rejected"
                logger.warning(f"Content rejected: {file_path.name} - {reason}")
                return False, reason

        except asyncio.TimeoutError:
            logger.error("Content filter timed out")
            return False, "Moderation check timed out"
        except Exception as e:
            logger.error(f"Content filter error: {e}")
            return False, f"Moderation error: {str(e)}"
