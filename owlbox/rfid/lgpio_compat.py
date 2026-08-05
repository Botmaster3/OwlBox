"""A tiny RPi.GPIO-compatible shim backed by `lgpio` instead of `RPi.GPIO`.

Needed because `RPi.GPIO` and gpiozero's `lgpio` pin factory cannot coexist in
the same process on current Raspberry Pi OS kernels: confirmed on real
hardware (Pi OS Bookworm, kernel 6.12) - as soon as `RPi.GPIO.setmode()`/
`setup()` runs, it claims GPIO lines project-wide (visible as "already in use,
continuing anyway" warnings even in a brand new process), which then makes
gpiozero's separate `lgpio` pin factory fail with `lgpio.error: 'GPIO busy'`
on completely unrelated pins the RC522 never touches (e.g. the volume
encoder). Since gpiozero (buttons/encoders) needs `lgpio` to work at all on
this kernel, everything else that talks to a GPIO pin - the RC522's software
SPI plus its reset pin - goes through `lgpio` directly too, via this shim,
instead of pulling `RPi.GPIO` into the process at all.

Implements only the handful of calls `owlbox.rfid.soft_spi.SoftSpi` and the
third-party `mfrc522` package actually make on a `GPIO`-like object.
"""
from __future__ import annotations

import lgpio

BCM = "BCM"
OUT = "OUT"
IN = "IN"
HIGH = 1
LOW = 0


class LgpioCompat:
    """One shared lgpio chip handle, reused by both the software-SPI pins and
    the RC522's reset pin so there's a single owner for all of them."""

    BCM = BCM
    OUT = OUT
    IN = IN
    HIGH = HIGH
    LOW = LOW

    def __init__(self, chip: int = 0):
        self._handle = lgpio.gpiochip_open(chip)
        self._mode = None
        self._claimed: set[int] = set()

    def getmode(self):
        return self._mode

    def setmode(self, mode) -> None:
        self._mode = mode

    def setup(self, pin: int, direction, initial=None) -> None:
        if pin in self._claimed:
            # Matches RPi.GPIO's own leniency: re-setup of an already-claimed
            # pin is a no-op warning there, not an error - free and reclaim.
            self._free(pin)
        if direction == OUT:
            level = HIGH if initial == HIGH else LOW
            lgpio.gpio_claim_output(self._handle, pin, level)
        else:
            lgpio.gpio_claim_input(self._handle, pin)
        self._claimed.add(pin)

    def output(self, pin: int, value) -> None:
        lgpio.gpio_write(self._handle, pin, HIGH if value else LOW)

    def input(self, pin: int) -> int:
        return lgpio.gpio_read(self._handle, pin)

    def _free(self, pin: int) -> None:
        try:
            lgpio.gpio_free(self._handle, pin)
        except Exception:  # pragma: no cover - best-effort hardware cleanup
            pass
        self._claimed.discard(pin)

    def cleanup(self, pin: "int | None" = None) -> None:
        pins = [pin] if pin is not None else list(self._claimed)
        for p in pins:
            self._free(p)

    def close_chip(self) -> None:
        """Releases every claimed line and the chip handle itself - call once
        the whole reader (software SPI + reset pin) is done with it."""
        self.cleanup()
        try:
            lgpio.gpiochip_close(self._handle)
        except Exception:  # pragma: no cover - best-effort hardware cleanup
            pass
