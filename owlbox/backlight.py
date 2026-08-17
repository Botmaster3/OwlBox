"""Controls the display backlight brightness.

Two independent mechanisms, tried in this order:

1. SysfsBacklight - the display panel's own kernel backlight device
   (/sys/class/backlight/<id>/brightness). Confirmed on real hardware to be
   how this project's current standard display (Waveshare 5-DSI-TOUCH-A)
   actually offers brightness control: its panel driver already registers a
   standard Linux backlight class device (seen as /sys/class/backlight/
   11-0045/ on the confirming unit - the numeric prefix is an I2C bus/address
   pair and can differ across boards/kernel versions, hence the
   directory-listing auto-detect below rather than a hardcoded path), and
   that file is group-writable by `video` - owlbox.service's
   SupplementaryGroups already includes that group, so no extra permission
   setup is needed. No GPIO wiring at all is involved in this path; this
   project's wiring guide for this display only ever specified 4 wires
   (5V/GND/SDA/SCL for power + I2C touch), no separate backlight line - a
   GpioBacklight on gpio.backlight_pin would just be driving a pin that
   was never physically connected to the display in the first place.
2. GpioBacklight - software PWM on a GPIO pin, wired through a driver
   transistor (a Pi GPIO can't source enough current for a backlight LED
   directly - see docs/hardware.md). This was the mechanism the project's
   earlier 7"/3.5" displays needed; kept as a fallback for that kind of
   hardware, used only if no sysfs backlight device is found at all.

In simulate mode, or if neither mechanism is available/configured,
NullBacklight just tracks the requested value without touching any
hardware - same "degrade gracefully" pattern as player.py/network.py.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Protocol

logger = logging.getLogger("owlbox.backlight")

_SYSFS_BACKLIGHT_ROOT = Path("/sys/class/backlight")


class BacklightBase(Protocol):
    def set_brightness(self, percent: int) -> None: ...
    def close(self) -> None: ...


class NullBacklight:
    def set_brightness(self, percent: int) -> None:
        pass

    def close(self) -> None:
        pass


class SysfsBacklight:
    def __init__(self, device_dir: Path):
        self._brightness_path = device_dir / "brightness"
        try:
            self._max = int((device_dir / "max_brightness").read_text().strip())
        except (OSError, ValueError):
            # Confirmed 255 on the one real device this was tested against,
            # but don't hard-fail construction over a missing/unreadable
            # max_brightness file - fall back to the near-universal default
            # for 8-bit backlight controllers rather than refusing to dim
            # at all.
            self._max = 255
        logger.info("using sysfs backlight device %s (max_brightness=%d)", device_dir, self._max)

    @classmethod
    def detect(cls) -> Optional["SysfsBacklight"]:
        if not _SYSFS_BACKLIGHT_ROOT.is_dir():
            return None
        try:
            devices = sorted(d for d in _SYSFS_BACKLIGHT_ROOT.iterdir() if d.is_dir())
        except OSError:
            return None
        if not devices:
            return None
        if len(devices) > 1:
            logger.warning(
                "multiple /sys/class/backlight devices found (%s) - using the first",
                [d.name for d in devices],
            )
        try:
            return cls(devices[0])
        except OSError:
            logger.exception("failed to initialize sysfs backlight at %s", devices[0])
            return None

    def set_brightness(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        value = round(percent / 100 * self._max)
        try:
            self._brightness_path.write_text(str(value))
        except OSError:
            logger.exception("failed to write brightness to %s", self._brightness_path)

    def close(self) -> None:
        pass


class GpioBacklight:
    def __init__(self, pin: int):
        from gpiozero import PWMLED

        self._led = PWMLED(pin)

    def set_brightness(self, percent: int) -> None:
        self._led.value = max(0, min(100, percent)) / 100

    def close(self) -> None:
        self._led.close()


def create_backlight(config) -> BacklightBase:
    if config.simulate:
        return NullBacklight()
    sysfs = SysfsBacklight.detect()
    if sysfs is not None:
        return sysfs
    pin = config.gpio.backlight_pin
    if not pin:
        return NullBacklight()
    return GpioBacklight(pin)
