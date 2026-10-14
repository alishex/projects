import asyncio
import logging

from faster_whisper import WhisperModel

from app.config import WHISPER_MODEL_SIZE

log = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        log.info("Whisper модели (%s) юкланмоқда...", WHISPER_MODEL_SIZE)
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _transcribe_sync(file_path: str) -> str:
    model = _get_model()
    segments, _ = model.transcribe(file_path, language="uz")
    return " ".join(seg.text.strip() for seg in segments)


async def transcribe(file_path: str) -> str:
    # faster-whisper bloklovchi (sync) chaqiruv — event loopni ushlab qolmaslik
    # uchun alohida threadda ishga tushiriladi.
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _transcribe_sync, file_path)
