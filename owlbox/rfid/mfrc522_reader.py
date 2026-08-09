from __future__ import annotations

import logging
import sys
from typing import Optional
from unittest.mock import patch

logger = logging.getLogger("owlbox.rfid")


class Mfrc522Reader:
    """Wraps the MFRC522 RC522 SPI reader (mfrc522 PyPI package) over the
    Pi's real hardware SPI0 bus (bus=0, device=0/CE0), with only the reset
    pin driven via `lgpio` rather than `RPi.GPIO` - see docs/hardware.md:

    - SPI0 is free on this project's standard hardware. The official 7" DSI
      display doesn't use SPI0 at all (unlike the older 3.5" SPI display
      this project used to target, whose overlay claimed both of SPI0's
      chip-selects), and SPI1 sits on the exact GPIOs (18/19/20/21) the
      HiFiBerry uses for I2S audio, so it stays off limits.
      `scripts/install.sh` enables the bus (`dtparam=spi=on`) as part of the
      rfid stage.
    - `RPi.GPIO` and gpiozero's `lgpio` pin factory (needed by the
      buttons/encoders, see owlbox/controls/gpio_controls.py) cannot coexist
      in the same process on current Raspberry Pi OS kernels - confirmed on
      real hardware, RPi.GPIO ends up claiming GPIO lines process-wide as
      soon as it's used at all, which then makes gpiozero's lgpio pin
      factory fail with "GPIO busy" on completely unrelated pins. The
      `mfrc522` package only touches `RPi.GPIO` for the reset pin (the SPI
      data lines go through the kernel's `spidev`, not GPIO bit-banging), so
      only that one reference needs redirecting to `lgpio`.

    Wiring (BCM numbering, standard SPI0 pins otherwise unused by this
    project): SCK->GPIO11, MOSI->GPIO10, MISO->GPIO9, SDA/CS->GPIO8 (CE0),
    RST->rfid.reset_pin (default GPIO26), plus 3.3V and GND. Do not power
    the RC522 from 5V, it is a 3.3V-only module.
    """

    def __init__(self, rfid_config):
        from mfrc522 import MFRC522

        from .lgpio_compat import BCM, LgpioCompat

        self._gpio = LgpioCompat()
        # mfrc522.MFRC522.__init__() unconditionally does
        # `import RPi.GPIO as GPIO` (module-level in mfrc522/MFRC522.py) for
        # its reset-pin handling, which isn't overridable through its public
        # API. Patching it for the duration of this one call swaps in our
        # lgpio-backed GPIO without touching (or needing to vendor) the
        # register-level protocol logic that makes up the rest of
        # MFRC522.py. The SPI transport itself (`self.spi = spidev.SpiDev();
        # self.spi.open(bus, device)`) is left alone - it opens the real
        # kernel /dev/spidev0.0 device, no patching needed.
        mfrc522_module = sys.modules["mfrc522.MFRC522"]
        with patch.object(mfrc522_module, "GPIO", self._gpio):
            self._reader = MFRC522(
                bus=0,
                device=0,
                pin_mode=BCM,
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
        try:
            self._gpio.close_chip()
        except Exception:  # pragma: no cover - best-effort hardware cleanup
            logger.exception("failed to release RC522 GPIO chip handle")
