from __future__ import annotations

from pathlib import Path
from typing import Optional

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".mp4", ".ogg", ".oga", ".flac", ".wav", ".opus"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def is_allowed_audio(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_AUDIO_EXTENSIONS


def is_allowed_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS


def probe_audio(path: Path) -> tuple[Optional[float], Optional[str]]:
    """Returns (duration_seconds, title) read from tags, best-effort."""
    try:
        import mutagen

        audio = mutagen.File(path)
    except Exception:
        return None, None
    if audio is None:
        return None, None
    duration = getattr(audio.info, "length", None) if audio.info else None
    title = None
    if audio.tags:
        for key in ("TIT2", "title", "\xa9nam"):
            if key in audio.tags:
                value = audio.tags[key]
                title = str(value[0]) if isinstance(value, list) else str(value)
                break
    return duration, title
