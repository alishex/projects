"""
ALLMAX Media Handler — voice/video_note/video transkriptsiya va rasm encode qilish.
SQLite cache: bir xil message_id ikkinchi marta transkribatsiya qilinmaydi.
"""

import asyncio
import base64
import logging
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

_CACHE_DB = Path(__file__).parent / "analytics" / "media_cache.sqlite3"
_whisper_model = None
_model_lock = asyncio.Lock()

WHISPER_MODEL_SIZE = "base"
MAX_DURATION_SEC   = 600  # 10 daqiqadan uzun bo'lsa skip

SUPPORTED_IMAGE_MIME = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".webp": "image/webp",
    ".gif":  "image/gif",
}


# ---------------------------------------------------------------------------
# SQLite cache
# ---------------------------------------------------------------------------
def _init_cache():
    _CACHE_DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(_CACHE_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            msg_id   INTEGER PRIMARY KEY,
            text     TEXT NOT NULL,
            created  TEXT DEFAULT (datetime('now'))
        )
    """)
    con.commit()
    con.close()


def _cache_get(msg_id: int) -> Optional[str]:
    try:
        con = sqlite3.connect(_CACHE_DB)
        row = con.execute("SELECT text FROM transcriptions WHERE msg_id=?", (msg_id,)).fetchone()
        con.close()
        return row[0] if row else None
    except Exception:
        return None


def _cache_set(msg_id: int, text: str):
    try:
        con = sqlite3.connect(_CACHE_DB)
        con.execute("INSERT OR REPLACE INTO transcriptions (msg_id, text) VALUES (?,?)", (msg_id, text))
        con.commit()
        con.close()
    except Exception as e:
        log.warning("Media cache yozish xatosi: %s", e)


# ---------------------------------------------------------------------------
# Whisper model (lazy load)
# ---------------------------------------------------------------------------
async def _get_model():
    global _whisper_model
    if _whisper_model is None:
        async with _model_lock:
            if _whisper_model is None:
                from faster_whisper import WhisperModel
                log.info("Whisper model yuklanmoqda (%s)...", WHISPER_MODEL_SIZE)
                _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
                log.info("Whisper model tayyor")
    return _whisper_model


# ---------------------------------------------------------------------------
# Media type helpers
# ---------------------------------------------------------------------------
def get_media_kind(msg: Any) -> Optional[str]:
    if getattr(msg, "voice", None):
        return "voice"
    if getattr(msg, "video_note", None):
        return "video_note"
    if getattr(msg, "video", None):
        return "video"
    if getattr(msg, "audio", None):
        return "audio"
    return None


def get_duration(msg: Any) -> Optional[int]:
    media = msg.voice or msg.video_note or msg.video or msg.audio
    if not media:
        return None
    for attr in getattr(media, "attributes", []) or []:
        dur = getattr(attr, "duration", None)
        if dur is not None:
            return int(dur)
    return None


def media_label(kind: str) -> str:
    return {
        "voice":      "🎤 Ovozli xabar",
        "video_note": "🎥 Video xabar (doira)",
        "video":      "🎥 Video",
        "audio":      "🎵 Audio",
    }.get(kind, "[media]")


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------
def _extract_audio(src: Path, dst: Path):
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", str(dst)],
        check=True, capture_output=True,
    )


def _transcribe_sync(model, audio_path: Path) -> str:
    segments, _ = model.transcribe(str(audio_path), beam_size=1, vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()


async def transcribe_message(tg_client, msg: Any) -> Optional[str]:
    """Ovozli/video xabarnini matnga o'giradi. Cache ishlatadi."""
    kind = get_media_kind(msg)
    if kind is None:
        return None

    cached = _cache_get(msg.id)
    if cached is not None:
        return cached

    duration = get_duration(msg)
    if duration and duration > MAX_DURATION_SEC:
        result = f"[{media_label(kind)} — {duration // 60} daq., juda uzun]"
        _cache_set(msg.id, result)
        return result

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            media_path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "media"))
            if not media_path:
                return f"[{media_label(kind)} — yuklanmadi]"

            audio_path = Path(tmpdir) / "audio.wav"
            await asyncio.to_thread(_extract_audio, Path(media_path), audio_path)

            model = await _get_model()
            text = await asyncio.to_thread(_transcribe_sync, model, audio_path)

        label = media_label(kind)
        result = f"[{label}: {text}]" if text else f"[{label} — ovoz aniqlanmadi]"
        _cache_set(msg.id, result)
        return result

    except Exception as e:
        log.warning("Transkriptsiya xatosi msg_id=%s: %s", msg.id, e)
        return f"[{media_label(kind)} — xatolik]"


# ---------------------------------------------------------------------------
# Image encoding for Claude Vision
# ---------------------------------------------------------------------------
async def encode_image_for_claude(tg_client, msg: Any) -> Optional[list]:
    """Rasmni Claude Vision uchun base64 content block ro'yxatiga o'giradi."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "img"))
            if not path:
                return None

            path = Path(path)
            mime = SUPPORTED_IMAGE_MIME.get(path.suffix.lower(), "image/jpeg")

            with open(path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()

        return [
            {"type": "text", "text": "[Mijoz rasm yubordi]"},
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
        ]
    except Exception as e:
        log.warning("Rasm encode xatosi: %s", e)
        return None


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
_init_cache()
