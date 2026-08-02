from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("owlbox.rfid")


class Mfrc522Reader:
    """Wraps the MFRC522 RC522 SPI reader (mfrc522 PyPI package).

    Wiring (BCM numbering): SDA/CS->SPI CE0, SCK->GPIO11, MOSI->GPIO10,
    MISO->GPIO9, RST->rfid.reset_pin (default GPIO25), plus 3.3V and GND.
    Do not power the RC522 from 5V, it is a 3.3V-only module.
    """

    def __init__(self, rfid_config):
        import RPi.GPIO as GPIO
        from mfrc522 import MFRC522

        self._reader = MFRC522(
            bus=rfid_config.spi_bus,
            device=rfid_config.spi_device,
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
