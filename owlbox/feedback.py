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
    if path is None:
        logger.warning("chime '%s' has no known sound file mapped", name)
        return
    if not path.exists():
        logger.warning("chime '%s' sound file missing on disk: %s", name, path)
        return
    try:
        result = subprocess.run(
            ["aplay", "-q", "-D", alsa_device, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=3,
            check=False,
        )
        # Deliberately still a no-op towards the caller either way (a broken
        # chime must never interrupt/crash playback) - but a non-zero exit
        # almost always means aplay couldn't actually open the ALSA device
        # (busy - mpv already has it open without dmix, see this module's
        # docstring - or a stale/wrong audio.alsa_device in config.yaml), so
        # it's worth a WARNING rather than the DEBUG this used to be: that
        # made "pressed Test, heard nothing" produce literally no trace
        # anywhere, even in the journal, since the app's default log level
        # (see main.py) is INFO.
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            logger.warning(
                "chime '%s' via aplay -D %s failed (exit %d): %s",
                name, alsa_device, result.returncode, stderr or "(keine Fehlerausgabe)",
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("chime '%s' playback unavailable (aplay missing or timed out): %s", name, exc)
