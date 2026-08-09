#!/usr/bin/env python3
"""Standalone RC522 scan test - no OwlBox app, no browser needed.

Reads config/config.yaml (same one the app uses), opens the RC522 exactly
the way owlbox.rfid.mfrc522_reader.Mfrc522Reader does, and prints every UID
it sees. Meant to be run with owlbox.service stopped (both would otherwise
fight over the same SPI0 device and reset GPIO) - `owlbox-stage rfid` does
this for you.

Usage: sudo /opt/owlbox/.venv/bin/python3 /opt/owlbox/scripts/test_rfid.py
Ctrl+C to stop.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from owlbox.config import load_config  # noqa: E402
from owlbox.rfid.mfrc522_reader import Mfrc522Reader  # noqa: E402


def main() -> None:
    config = load_config()
    print(f"RC522 an SPI0 (bus=0, device=0/CE0) mit RST={config.rfid.reset_pin} "
          f"(BCM-Nummerierung)")
    print("Chip auf den Leser legen. Ctrl+C zum Beenden.\n")

    reader = Mfrc522Reader(config.rfid)
    last_uid = None
    missing = 0
    try:
        while True:
            uid = reader.read_uid()
            if uid is not None:
                if uid != last_uid:
                    print(f"  Chip erkannt: {uid}")
                last_uid = uid
                missing = 0
            elif last_uid is not None:
                missing += 1
                if missing >= 5:
                    print("  (Chip abgenommen)")
                    last_uid = None
            time.sleep(0.15)
    except KeyboardInterrupt:
        pass
    finally:
        reader.close()
        print("\nBeendet.")


if __name__ == "__main__":
    main()
