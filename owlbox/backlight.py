"""Controls the display backlight brightness via software PWM on a GPIO pin.

By default the backlight is hardwired straight to a 3.3V pin (see docs/hardware.md) -
simple, but always on at full brightness. Dimming requires rewiring that line to a
free GPIO through a driver transistor (a Pi GPIO can't source enough current for the
backlight directly) and setting gpio.backlight_pin accordingly. Until that's done -
or in simulate mode - NullBacklight just tracks the requested value without touching
any hardware, the same "degrade gracefully" pattern as player.py/network.py.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger("owlbox.backlight")


class BacklightBase(Protocol):
    def set_brightness(self, percent: int) -> None: ...
    def close(self) -> None: ...


class NullBacklight:
    def set_brightness(self, percent: int) -> None:
        pass

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
    pin = config.gpio.backlight_pin
    if config.simulate or not pin:
        return NullBacklight()
    return GpioBacklight(pin)
