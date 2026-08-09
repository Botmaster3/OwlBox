#!/usr/bin/env python3
"""Standalone button/rotary-encoder test - no OwlBox app, no browser needed.

Wires up the exact same GpioControls class the real app uses, but with
print callbacks instead of playback/volume/brightness logic, so wiring can
be verified by watching stdout rather than by starting a story. Meant to be
run with owlbox.service stopped (both would otherwise fight over the same
GPIO pins) - `owlbox-stage controls` does this for you.

Usage: sudo /opt/owlbox/.venv/bin/python3 /opt/owlbox/scripts/test_controls.py
Ctrl+C to stop.
"""
from __future__ import annotations

import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from owlbox.config import load_config  # noqa: E402
from owlbox.controls.gpio_controls import GpioControls  # noqa: E402


def main() -> None:
    config = load_config()
    g = config.gpio
    print(f"Taster: next=GPIO{g.button_next} prev=GPIO{g.button_prev}")
    print(f"Lautstaerke-Encoder: clk=GPIO{g.encoder_clk} dt=GPIO{g.encoder_dt} switch=GPIO{g.encoder_switch}")
    print(f"Helligkeits-Encoder: clk=GPIO{g.brightness_encoder_clk} dt=GPIO{g.brightness_encoder_dt}")
    print("(BCM-Nummerierung)\n")
    print("Taster druecken / Encoder drehen und beobachten. Ctrl+C zum Beenden.\n")

    controls = GpioControls(
        g,
        on_next=lambda: print("  -> Weiter (Taster next)"),
        on_prev=lambda: print("  -> Zurueck (Taster prev)"),
        on_toggle_pause=lambda: print("  -> Play/Pause (Encoder-Klick)"),
        on_volume_delta=lambda d: print(f"  -> Lautstaerke {'+1' if d > 0 else '-1'} (Encoder gedreht)"),
        on_seek=lambda s: print(f"  -> Spulen {s:+.0f}s (Taster gehalten)"),
        on_brightness_delta=lambda d: print(f"  -> Helligkeit {'+1' if d > 0 else '-1'} (2. Encoder gedreht)"),
        on_shutdown=lambda: print("  -> Shutdown-Geste erkannt (Encoder-Klick lang gehalten)"),
    )

    stop = False

    def handle_sigint(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_sigint)
    try:
        while not stop:
            time.sleep(0.1)
    finally:
        controls.close()
        print("\nBeendet.")


if __name__ == "__main__":
    main()
