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

import os

import lgpio

BCM = "BCM"
OUT = "OUT"
IN = "IN"
HIGH = 1
LOW = 0

# On a Raspberry Pi 5, the 40-pin header's GPIOs are not on the SoC's own
# gpiochip0 anymore - they're behind the separate RP1 southbridge chip,
# which (on the kernels seen so far) enumerates as a *later* gpiochip, not
# necessarily 0. NOT yet verified on real Pi 5 hardware in this project
# (still Pi 3B+ at the time of writing this) - this mirrors, on purpose,
# the exact same detection gpiozero's own installed LGPIOFactory already
# does (see `gpiozero/pins/lgpio.py`/`local.py` in the installed package -
# `chip = 4 if (revision & 0xff0) >> 4 == 0x17 and
# os.path.exists('/dev/gpiochip4') else 0`, 0x17 being the Pi 5's BCM2712
# SoC code in the revision field). Duplicated here, rather than imported
# from gpiozero, to keep this shim dependency-free - but it MUST keep
# agreeing with gpiozero's own choice, since gpiozero drives the buttons/
# encoders on the very same physical header at the very same time (see
# owlbox/controls/gpio_controls.py) - if the two ever picked different
# chips for the same Pi, pin numbers would silently mean different physical
# pins between the two halves of this project's GPIO usage.
_PI5_SOC_CODE = 0x17


def _get_pi_revision() -> "int | None":
    """Same two-source lookup gpiozero's own `get_pi_revision()` uses -
    device-tree first (present on any Bookworm+ image), `/proc/cpuinfo` as
    the older fallback. Returns None (never raises) if neither is readable,
    e.g. when not actually running on a Pi at all - `_detect_chip()` below
    then just falls back to the historical default, chip 0."""
    try:
        with open("/proc/device-tree/system/linux,revision", "rb") as f:
            return int.from_bytes(f.read(4), "big")
    except OSError:
        pass
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("Revision"):
                    revision = line.split(":")[1].strip().lower()
                    if revision.startswith("100"):  # "overvolted" marker prefix
                        revision = revision[-4:]
                    return int(revision, 16)
    except (OSError, ValueError):
        pass
    return None


def _detect_chip() -> int:
    revision = _get_pi_revision()
    if revision is not None and (revision & 0xFF0) >> 4 == _PI5_SOC_CODE and os.path.exists("/dev/gpiochip4"):
        return 4
    return 0


class LgpioCompat:
    """One shared lgpio chip handle, reused by both the software-SPI pins and
    the RC522's reset pin so there's a single owner for all of them."""

    BCM = BCM
    OUT = OUT
    IN = IN
    HIGH = HIGH
    LOW = LOW

    def __init__(self, chip: "int | None" = None):
        if chip is None:
            chip = _detect_chip()
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
