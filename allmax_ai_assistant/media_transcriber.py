import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

import config

logger = logging.getLogger("telegram_ai_assistant.transcriber")

_model = None
_model_lock = asyncio.Lock()
_transcribe_lock = asyncio.Lock()


async def _get_model():
    global _model
    if _model is None:
        async with _model_lock:
            if _model is None:
                from faster_whisper import WhisperModel

                logger.info("Whisper modeli yuklanmoqda: %s", config.WHISPER_MODEL_SIZE)
                _model = WhisperModel(config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _media_kind(msg: Any) -> Optional[str]:
    if getattr(msg, "voice", None):
        return "voice"
    if getattr(msg, "video_note", None):
        return "video_note"
    if getattr(msg, "video", None):
        return "video"
    if getattr(msg, "audio", None):
        return "audio"
    return None


def _media_duration(msg: Any) -> Optional[int]:
    media = msg.voice or msg.video_note or msg.video or msg.audio
    for attr in getattr(media, "attributes", []) or []:
        duration = getattr(attr, "duration", None)
        if duration is not None:
            return int(duration)
    return None


def _extract_audio(src: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", str(dst)],
        check=True,
        capture_output=True,
    )


def _transcribe_sync(model, audio_path: Path) -> str:
    segments, _info = model.transcribe(str(audio_path), beam_size=1, vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()


async def transcribe_file(media_path: Path) -> str:
    """Berilgan media fayldagi nutqni matnga aylantiradi."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.wav"
        await asyncio.to_thread(_extract_audio, media_path, audio_path)
        model = await _get_model()
        async with _transcribe_lock:
            text = await asyncio.to_thread(_transcribe_sync, model, audio_path)
        return text or "(ovoz aniqlanmadi)"


async def transcribe_message(client, msg: Any) -> Optional[str]:
    """Ovozli/video xabarni matnga aylantiradi. Mos kelmasa None qaytaradi."""
    kind = _media_kind(msg)
    if kind is None:
        return None

    duration = _media_duration(msg)
    if duration is not None and duration > config.MAX_MEDIA_DURATION_SEC:
        minutes = duration // 60
        return f"[Media juda uzun ({minutes} daq.), transkripsiya qilinmadi]"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            media_path = await client.download_media(msg, file=str(tmpdir_path / "media"))
            if not media_path:
                return None
            return await transcribe_file(Path(media_path))
    except Exception as exc:
        logger.exception("Transkripsiya xatosi: %s", exc)
        return "[transkripsiya qilishda xatolik yuz berdi]"


def label_for_kind(kind: str) -> str:
    return {
        "voice": "🎤 Ovozli xabar",
        "video_note": "🎥 Video xabar",
        "video": "🎥 Video",
        "audio": "🎵 Audio",
    }.get(kind, "[media]")


def get_media_kind(msg: Any) -> Optional[str]:
    return _media_kind(msg)
