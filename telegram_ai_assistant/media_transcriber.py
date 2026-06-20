import asyncio
import base64
import json
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

SUPPORTED_IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

HEIC_EXTENSIONS = {".heic", ".heif"}


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
    for lang in ("tr", "ru"):
        segs, info = model.transcribe(
            str(audio_path), beam_size=5, vad_filter=True, language=lang
        )
        text = " ".join(s.text.strip() for s in segs).strip()
        logger.info("Transcription lang=%s prob=%.2f: %.80s", lang, info.language_probability, text)
        if len(text) >= 3:
            return text
    return ""


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
    """Ovozli/audio xabarni matnga aylantiradi. Mos kelmasa None qaytaradi."""
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


def _describe_image_sync(mime: str, data: str) -> str:
    """Claude Vision orqali rasm tavsifini sinxron chaqiradi."""
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": mime, "data": data}
                },
                {
                    "type": "text",
                    "text": (
                        "Bu rasmda nima tasvirlangan? "
                        "O'zbek yoki rus tilida, qisqacha (2-4 jumla) tushuntir. "
                        "Agar mahsulot, kiyim, narx yozuvi yoki savdo xabari bo'lsa — alohida ta'kidla."
                    )
                }
            ]
        }]
    )
    return resp.content[0].text.strip() if resp.content else "(tavsif olinmadi)"


async def describe_image_message(tg_client, msg: Any) -> Optional[str]:
    """Rasmni Claude Vision orqali tasvirlaydi."""
    if not getattr(msg, "photo", None):
        return None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "photo"))
            if not path:
                return None
            path = Path(path)
            mime = SUPPORTED_IMAGE_MIME.get(path.suffix.lower(), "image/jpeg")
            with open(path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()
        return await asyncio.to_thread(_describe_image_sync, mime, data)
    except Exception as exc:
        logger.exception("Rasm tavsifi xatosi: %s", exc)
        return None


def _get_video_duration(video_path: Path) -> float:
    """ffprobe orqali video davomiyligini oladi (sekund)."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=10
        )
        info = json.loads(r.stdout)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def _extract_video_frames(video_path: Path, output_dir: Path, n: int = 3) -> list:
    """Videodan n ta kalit kadr ajratadi (25%, 50%, 75% nuqtalardan)."""
    duration = _get_video_duration(video_path)
    if duration < 1:
        duration = 10.0

    frames = []
    for i in range(1, n + 1):
        ts = duration * i / (n + 1)
        frame_path = output_dir / f"frame_{i:02d}.jpg"
        r = subprocess.run(
            [
                "ffmpeg", "-y", "-ss", f"{ts:.2f}", "-i", str(video_path),
                "-frames:v", "1", "-q:v", "3", str(frame_path)
            ],
            capture_output=True, timeout=15
        )
        if r.returncode == 0 and frame_path.exists() and frame_path.stat().st_size > 1000:
            frames.append(frame_path)
    return frames


def _describe_video_sync(frames: list, transcript: str) -> str:
    """Kadrlar + audio transkripsiya asosida video tavsifini beradi."""
    from anthropic import Anthropic
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    content = []
    for i, frame in enumerate(frames[:3]):
        with open(frame, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": data}
        })
        content.append({"type": "text", "text": f"[Kadr {i + 1}]"})

    prompt_parts = ["Bu video kadrlari."]
    if transcript and transcript not in ("(ovoz aniqlanmadi)", "[transkripsiya qilishda xatolik yuz berdi]"):
        prompt_parts.append(f'Audioda aytilgan: "{transcript}".')
    prompt_parts.append(
        "Video nimani ko'rsatadi? O'zbek yoki rus tilida, qisqacha (3-5 jumla) ta'rifla. "
        "Odamlar, harakatlar, mahsulotlar, muhit — barchasini eslatib o't."
    )
    content.append({"type": "text", "text": " ".join(prompt_parts)})

    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        messages=[{"role": "user", "content": content}]
    )
    return resp.content[0].text.strip() if resp.content else "(video tavsifi olinmadi)"


async def analyze_video_file(video_path: Path) -> str:
    """Mahalliy video faylni to'liq tahlil qiladi: audio + kadrlar."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            audio_path = tmpdir_path / "audio.wav"
            transcript = ""
            try:
                await asyncio.to_thread(_extract_audio, video_path, audio_path)
                model = await _get_model()
                async with _transcribe_lock:
                    transcript = await asyncio.to_thread(_transcribe_sync, model, audio_path)
            except Exception as exc:
                logger.warning("Video audio xatosi: %s", exc)

            frames_dir = tmpdir_path / "frames"
            frames_dir.mkdir()
            frames = await asyncio.to_thread(_extract_video_frames, video_path, frames_dir, 3)

            if frames:
                visual_desc = await asyncio.to_thread(_describe_video_sync, frames, transcript)
                if transcript:
                    return f"Audio: {transcript} | Visual: {visual_desc}"
                return f"Visual: {visual_desc}"
            elif transcript:
                return transcript
            return "(video tahlil qilinmadi)"

    except Exception as exc:
        logger.exception("Video tahlil xatosi: %s", exc)
        return "[video tahlilida xatolik]"


async def analyze_video_message(tg_client, msg: Any) -> Optional[str]:
    """Telethon video xabarini yuklab to'liq tahlil qiladi."""
    kind = _media_kind(msg)
    if kind not in ("video", "video_note"):
        return None

    duration = _media_duration(msg)
    if duration is not None and duration > config.MAX_MEDIA_DURATION_SEC:
        minutes = duration // 60
        return f"[Video juda uzun ({minutes} daq.), tahlil qilinmadi]"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            media_path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "media"))
            if not media_path:
                return None
            return await analyze_video_file(Path(media_path))
    except Exception as exc:
        logger.exception("Video xabar tahlil xatosi: %s", exc)
        return "[video tahlilida xatolik]"


def _heic_to_jpeg_sync(heic_path: Path, output_path: Path) -> bool:
    """HEIC faylni JPEG ga aylantiradi."""
    try:
        from pillow_heif import register_heif_opener
        from PIL import Image
        register_heif_opener()
        img = Image.open(heic_path)
        img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=90)
        return True
    except Exception as exc:
        logger.warning("HEIC->JPEG aylantirish xatosi: %s", exc)
        return False


async def describe_heic_file(heic_path: Path) -> Optional[str]:
    """HEIC faylni JPEG ga aylantirib Claude Vision orqali tasvirlaydi."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            jpeg_path = Path(tmpdir) / "converted.jpg"
            ok = await asyncio.to_thread(_heic_to_jpeg_sync, heic_path, jpeg_path)
            if not ok or not jpeg_path.exists():
                return "(HEIC rasmni o'qib bo'lmadi)"
            with open(jpeg_path, "rb") as f:
                data = base64.standard_b64encode(f.read()).decode()
        return await asyncio.to_thread(_describe_image_sync, "image/jpeg", data)
    except Exception as exc:
        logger.exception("HEIC tavsifi xatosi: %s", exc)
        return None


async def describe_heic_message(tg_client, msg: Any) -> Optional[str]:
    """Telegram HEIC hujjat xabarini yuklaydi va tasvirlaydi."""
    doc = getattr(msg, "document", None)
    if not doc:
        return None
    filename = ""
    for attr in getattr(doc, "attributes", []):
        fn = getattr(attr, "file_name", None)
        if fn:
            filename = fn
            break
    if Path(filename).suffix.lower() not in HEIC_EXTENSIONS:
        return None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await tg_client.download_media(msg, file=str(Path(tmpdir) / "image.heic"))
            if not path:
                return None
            return await describe_heic_file(Path(path))
    except Exception as exc:
        logger.exception("HEIC xabar tavsifi xatosi: %s", exc)
        return None


def label_for_kind(kind: str) -> str:
    return {
        "voice": "🎤 Ovozli xabar",
        "video_note": "🎥 Round video",
        "video": "🎬 Video",
        "audio": "🎵 Audio",
    }.get(kind, "[media]")


def get_media_kind(msg: Any) -> Optional[str]:
    return _media_kind(msg)
