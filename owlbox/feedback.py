"""Short acoustic confirmation sounds - RFID scans (chip erkannt / unbekannt /
Funktions-Chip) plus the engine's own startup/shutdown. Played via a plain
`aplay` subprocess rather than through the main mpv instance, so an
already-playing story is never interrupted by loading/replacing anything in
its playlist - best-effort: if aplay is missing, or the ALSA device is busy
with mpv already holding it open (common on setups without dmix), the chime
is silently skipped rather than raising.

Volume is controlled by the shared ALSA hardware mixer (see player.py), the
same one mpv uses - there's no separate "chime volume" at the device level,
so engine._play_chime() temporarily drops the mixer to a fixed, quiet level
for the chime's short duration and restores it right after. That means this
call blocks for as long as the chime takes to play (well under a second) -
deliberate, so the caller knows when it's safe to put the volume back.
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
        subprocess.run(
            ["aplay", "-q", "-D", alsa_device, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        logger.debug("chime playback unavailable (aplay missing or timed out)")
