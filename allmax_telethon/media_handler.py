"""
ALLMAX Media Handler — voice/video_note/video transkriptsiya va rasm encode qilish.
SQLite cache: bir xil message_id ikkinchi marta transkribatsiya qilinmaydi.
"""

import asyncio
import base64
import gc
import logging
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)

_CACHE_DB = Path(__file__).parent / "analytics" / "media_cache.sqlite3"
_whisper_model = None
_model_lock = asyncio.Lock()
_model_last_used: float = 0.0
_MODEL_UNLOAD_AFTER = 600  # 10 daqiqa ishlatilmasa xotiradan tushirish

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
    con.execute("""
        CREATE TABLE IF NOT EXISTS image_cache (
            msg_id   INTEGER PRIMARY KEY,
            mime     TEXT NOT NULL,
            data     TEXT NOT NULL,
            label    TEXT NOT NULL DEFAULT '[Mijoz rasm yubordi]',
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


def _img_cache_get(msg_id: int) -> Optional[list]:
    try:
        con = sqlite3.connect(_CACHE_DB)
        row = con.execute(
            "SELECT mime, data, label FROM image_cache WHERE msg_id=?", (msg_id,)
        ).fetchone()
        con.close()
        if not row:
            return None
        mime, data, label = row
        return [
            {"type": "text", "text": label},
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
        ]
    except Exception:
        return None


def _img_cache_set(msg_id: int, mime: str, data: str, label: str):
    try:
        con = sqlite3.connect(_CACHE_DB)
        con.execute(
            "INSERT OR REPLACE INTO image_cache (msg_id, mime, data, label) VALUES (?,?,?,?)",
            (msg_id, mime, data, label),
        )
        con.commit()
        con.close()
    except Exception as e:
        log.warning("Image cache yozish xatosi: %s", e)


# ---------------------------------------------------------------------------
# Whisper model (lazy load + auto-unload)
# ---------------------------------------------------------------------------
async def _get_model():
    global _whisper_model, _model_last_used
    _model_last_used = time.monotonic()
    if _whisper_model is None:
        async with _model_lock:
            if _whisper_model is None:
                from faster_whisper import WhisperModel
                log.info("Whisper model yuklanmoqda (%s)...", WHISPER_MODEL_SIZE)
                _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
                log.info("Whisper model tayyor")
    return _whisper_model


async def _model_unload_loop():
    """Fon vazifasi: N daqiqa ovoz kelmasa modelni xotiradan tushiradi."""
    global _whisper_model, _model_last_used
    while True:
        await asyncio.sleep(60)
        if _whisper_model is None:
            continue
        idle = time.monotonic() - _model_last_used
        if idle >= _MODEL_UNLOAD_AFTER:
            async with _model_lock:
                if _whisper_model is not None:
                    _whisper_model = None
                    gc.collect()
                    log.info("Whisper model xotiradan tushirildi (%.0f sek ishlatilmadi)", idle)


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
# Audio stream mavjudligini tekshirish
# ---------------------------------------------------------------------------
def _has_audio_stream(path: Path) -> bool:
    """ffprobe orqali faylda hech bo'lmasa bitta audio stream borligini tekshiradi."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True,
        )
        return bool(r.stdout.strip())
    except Exception:
        return True  # ffprobe ishlamasa, harakat qilib ko'ramiz


# ---------------------------------------------------------------------------
# Format detection by magic bytes
# ---------------------------------------------------------------------------
def _detect_audio_format(path: Path) -> Optional[str]:
    """Fayl boshidagi baytlar orqali haqiqiy audio formatni aniqlaydi."""
    try:
        with open(path, "rb") as f:
            header = f.read(12)
        if header[:4] == b"OggS":
            return "ogg"
        if header[:4] == b"\x1a\x45\xdf\xa3":  # EBML (WebM/MKV)
            return "webm"
        if header[:3] == b"ID3" or (len(header) >= 2 and header[0] == 0xff and (header[1] & 0xe0) == 0xe0):
            return "mp3"
        if len(header) >= 8 and header[4:8] in (b"ftyp", b"mdat", b"moov"):
            return "mp4"
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------
def _extract_audio(src: Path, dst: Path):
    """
    Audio/video fayldan audio qismini WAV ga ajratadi.
    Telegram ovoz xabarlari ko'pincha .webm kengaytmali OggS fayl bo'ladi —
    shuning uchun avval haqiqiy formatni aniqlab, ffmpeg ga ko'rsatamiz.
    """
    base_cmd = ["ffmpeg", "-y"]

    fmt = _detect_audio_format(src)
    if fmt:
        base_cmd += ["-f", fmt]
    base_cmd += ["-i", str(src), "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", str(dst)]

    result = subprocess.run(base_cmd, capture_output=True)
    if result.returncode == 0 and dst.exists() and dst.stat().st_size > 0:
        return

    # Fallback: format ko'rsatmasdan
    fallback = ["ffmpeg", "-y", "-i", str(src), "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", str(dst)]
    result2 = subprocess.run(fallback, capture_output=True)
    if result2.returncode != 0:
        stderr = (result2.stderr or b"").decode(errors="replace")
        raise subprocess.CalledProcessError(result2.returncode, fallback, stderr=stderr.encode())


def _transcribe_sync(model, audio_path: Path) -> str:
    # Turkiy tillar oilasida: tr (turk) → o'zbek so'zlarini eng yaxshi taniydi.
    # Fallback: ru (rus) — ko'p o'zbeklar rus tilida ham gaplashadi.
    for lang in ("tr", "ru"):
        segs, info = model.transcribe(
            str(audio_path), beam_size=5, vad_filter=True, language=lang
        )
        text = " ".join(s.text.strip() for s in segs).strip()
        log.info("Transcription lang=%s prob=%.2f: %.80s", lang, info.language_probability, text)
        if len(text) >= 3:
            return text
    return ""


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

            # Audio stream yo'q bo'lsa (VP9 sticker, silent video) — transcribe qilmaylik
            has_audio = await asyncio.to_thread(_has_audio_stream, Path(media_path))
            if not has_audio:
                result = f"[{media_label(kind)} — audio yo'q]"
                _cache_set(msg.id, result)
                return result

            audio_path = Path(tmpdir) / "audio.wav"
            await asyncio.to_thread(_extract_audio, Path(media_path), audio_path)

            model = await _get_model()
            text = await asyncio.to_thread(_transcribe_sync, model, audio_path)

        label = media_label(kind)
        result = f"[{label}: {text}]" if text else f"[{label} — ovoz aniqlanmadi]"
        _cache_set(msg.id, result)
        return result

    except subprocess.CalledProcessError as e:
        stderr_tail = (e.stderr or b"").decode(errors="replace")[-400:]
        log.warning("Transkriptsiya xatosi msg_id=%s exit=%s | ffmpeg stderr: %s", msg.id, e.returncode, stderr_tail)
        result = f"[{media_label(kind)} — xatolik]"
        _cache_set(msg.id, result)
        return result
    except Exception as e:
        log.warning("Transkriptsiya xatosi msg_id=%s: %s", msg.id, e)
        result = f"[{media_label(kind)} — xatolik]"
        _cache_set(msg.id, result)
        return result


# ---------------------------------------------------------------------------
# Image encoding for Claude Vision
# ---------------------------------------------------------------------------
async def encode_image_for_claude(tg_client, msg: Any) -> Optional[list]:
    """Rasmni Claude Vision uchun base64 content block ro'yxatiga o'giradi. SQLite cache ishlatadi."""
    cached = _img_cache_get(msg.id)
    if cached is not None:
        return cached

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "img"))
            if not path:
                return None

            path = Path(path)
            mime = SUPPORTED_IMAGE_MIME.get(path.suffix.lower(), "image/jpeg")

            with open(path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()

        label = "[Mijoz rasm yubordi]"
        _img_cache_set(msg.id, mime, data, label)
        return [
            {"type": "text", "text": label},
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
        ]
    except Exception as e:
        log.warning("Rasm encode xatosi: %s", e)
        return None


# ---------------------------------------------------------------------------
# GIF first-frame extraction for Claude Vision
# ---------------------------------------------------------------------------
def _extract_gif_frame_sync(src: Path, dst: Path):
    """GIF/MPEG4 animatsiyasidan birinchi kadrni JPEG ga oladi."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(dst)],
        check=True, capture_output=True,
    )


async def encode_gif_for_claude(tg_client, msg: Any) -> Optional[list]:
    """
    Telegram GIF (MPEG4 animatsiya) dan birinchi kadrni olib,
    Claude Vision uchun image block sifatida qaytaradi. SQLite cache ishlatadi.
    """
    cached = _img_cache_get(msg.id)
    if cached is not None:
        return cached

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            media_path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "gif"))
            if not media_path:
                return None

            frame_path = Path(tmpdir) / "frame.jpg"
            await asyncio.to_thread(_extract_gif_frame_sync, Path(media_path), frame_path)

            if not frame_path.exists() or frame_path.stat().st_size == 0:
                return None

            with open(frame_path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()

        label = "[Mijoz GIF yubordi]"
        _img_cache_set(msg.id, "image/jpeg", data, label)
        return [
            {"type": "text", "text": label},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
        ]
    except Exception as e:
        log.warning("GIF encode xatosi: %s", e)
        return None


# ---------------------------------------------------------------------------
# Sticker encoding for Claude Vision (WebP → base64)
# ---------------------------------------------------------------------------
async def encode_sticker_for_claude(tg_client, msg: Any) -> Optional[list]:
    """Telegram stikerini WebP formatda Claude Vision uchun qaytaradi."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "sticker"))
            if not path:
                return None

            path = Path(path)
            # Animated stickers are .tgs (lottie) — skip, only static WebP
            if path.suffix.lower() == ".tgs":
                return None

            mime = SUPPORTED_IMAGE_MIME.get(path.suffix.lower(), "image/webp")
            with open(path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()

        return [
            {"type": "text", "text": "[Mijoz stiker yubordi]"},
            {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}},
        ]
    except Exception as e:
        log.warning("Stiker encode xatosi: %s", e)
        return None


# ---------------------------------------------------------------------------
# Startup (prewarm o'chirildi — lazy load + auto-unload ishlatiladi)
# ---------------------------------------------------------------------------
async def prewarm_whisper():
    """Unload loopini ishga tushiradi. Model endi lazy-load qilinadi."""
    asyncio.create_task(_model_unload_loop())
    log.info("Whisper: lazy-load rejimi, %d sek inactivity = unload", _MODEL_UNLOAD_AFTER)


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
_init_cache()
