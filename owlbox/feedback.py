"""Short acoustic confirmation sounds - RFID scans (chip erkannt / unbekannt /
Funktions-Chip) plus the engine's own startup/shutdown. Played as a
fire-and-forget `aplay` subprocess rather than through the main mpv instance,
so an already-playing story is never interrupted - best-effort: if aplay is
missing, or the ALSA device is busy with mpv already holding it open (common
on setups without dmix), the chime is silently skipped rather than raising.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger("owlbox.feedback")

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "sounds"
CHIMES = {
    "known": ASSETS_DIR / "chip_known.wav",
    "unknown": ASSETS_DIR / "chip_unknown.wav",
    "function": ASSETS_DIR / "function_tag.wav",
    "startup": ASSETS_DIR / "startup.wav",
    "shutdown": ASSETS_DIR / "shutdown.wav",
}


def play_chime(name: str, alsa_device: str) -> None:
    path = CHIMES.get(name)
    if path is None or not path.exists():
        return
    try:
        subprocess.Popen(
            ["aplay", "-q", "-D", alsa_device, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        logger.debug("chime playback unavailable (aplay missing?)")
