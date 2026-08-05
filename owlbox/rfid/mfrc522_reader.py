from __future__ import annotations

import logging
from typing import Optional
from unittest.mock import patch

from .soft_spi import SoftSpi

logger = logging.getLogger("owlbox.rfid")


class Mfrc522Reader:
    """Wraps the MFRC522 RC522 SPI reader (mfrc522 PyPI package) over a
    software (bit-banged) SPI bus on plain GPIOs rather than a hardware SPI
    controller - see docs/hardware.md for why: on the project's standard
    hardware, both hardware SPI buses are already spoken for. SPI0's two
    chip-selects are both claimed by the 3.5" display's own driver overlay
    (CE0 for the screen, CE1 for a touch controller the overlay always
    enables in the kernel, even when touch is left physically unwired), and
    SPI1 sits on the exact GPIOs (18/19/20/21) the HiFiBerry uses for I2S
    audio. That leaves no hardware SPI bus free for the RC522.

    Wiring (BCM numbering, four GPIOs otherwise unused by this project):
    SCK->rfid.sck_pin (default GPIO4), MOSI->rfid.mosi_pin (default GPIO16),
    MISO->rfid.miso_pin (default GPIO15), SDA/CS->rfid.cs_pin (default
    GPIO14), RST->rfid.reset_pin (default GPIO25), plus 3.3V and GND. Do not
    power the RC522 from 5V, it is a 3.3V-only module.
    """

    def __init__(self, rfid_config):
        import RPi.GPIO as GPIO
        import spidev
        from mfrc522 import MFRC522

        soft_spi = SoftSpi(
            sck_pin=rfid_config.sck_pin,
            mosi_pin=rfid_config.mosi_pin,
            miso_pin=rfid_config.miso_pin,
            cs_pin=rfid_config.cs_pin,
        )
        # mfrc522.MFRC522.__init__() always does `self.spi = spidev.SpiDev();
        # self.spi.open(bus, device)` itself, with no way to hand it a
        # different transport - patching spidev.SpiDev for the duration of
        # this one call is the only way to swap in our software SPI without
        # vendoring the (already correct, no need to touch it) register-level
        # protocol logic that makes up the rest of MFRC522.py.
        with patch.object(spidev, "SpiDev", return_value=soft_spi):
            self._reader = MFRC522(
                bus=0,
                device=0,
                pin_mode=GPIO.BCM,
                pin_rst=rfid_config.reset_pin,
            )

    def read_uid(self) -> Optional[str]:
        status, _tag_type = self._reader.MFRC522_Request(self._reader.PICC_REQIDL)
        if status != self._reader.MI_OK:
            return None
        status, uid_bytes = self._reader.MFRC522_Anticoll()
        if status != self._reader.MI_OK or len(uid_bytes) < 4:
            return None
        return "".join(f"{b:02X}" for b in uid_bytes[:4])

    def close(self) -> None:
        try:
            self._reader.spi.close()
        except Exception:  # pragma: no cover - best-effort hardware cleanup
            logger.exception("failed to close RC522 SPI handle")
