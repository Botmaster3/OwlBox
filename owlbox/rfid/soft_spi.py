"""Minimal software (bit-banged) SPI master, just enough of spidev.SpiDev's
surface (open/max_speed_hz/xfer2/close) to drop into the `mfrc522` PyPI
package without modifying it - see Mfrc522Reader for why this exists: the
Pi's two hardware SPI controllers are both already spoken for by other parts
of the standard OwlBox hardware (SPI0 by the 3.5" display + its always-on
touch controller, SPI1 by the HiFiBerry's I2S audio pins), leaving no
hardware SPI bus free for the RC522.

SPI mode 0 (CPOL=0, CPHA=0), MSB first - the RC522's only supported mode.
The RC522 has no minimum clock speed (it's a simple shift register), so
toggling GPIOs one bit at a time from Python is slow but entirely fine.
"""
from __future__ import annotations

import time
from typing import Optional


class SoftSpi:
    def __init__(
        self,
        sck_pin: int,
        mosi_pin: int,
        miso_pin: int,
        cs_pin: int,
        gpio_module: Optional[object] = None,
        half_period: float = 0.000002,
    ):
        self._sck = sck_pin
        self._mosi = mosi_pin
        self._miso = miso_pin
        self._cs = cs_pin
        self._gpio = gpio_module
        self._half_period = half_period
        # Accepted for API compatibility with spidev.SpiDev (mfrc522.MFRC522
        # sets this after construction) - meaningless here, bit-banging has
        # no clock-speed register to program.
        self.max_speed_hz = 1_000_000

    def _gpio_module(self):
        if self._gpio is None:
            import RPi.GPIO as GPIO

            self._gpio = GPIO
        return self._gpio

    def open(self, bus: int, device: int) -> None:
        del bus, device  # meaningless here - the pins are already fixed above
        gpio = self._gpio_module()
        if gpio.getmode() is None:
            gpio.setmode(gpio.BCM)
        gpio.setup(self._sck, gpio.OUT, initial=gpio.LOW)
        gpio.setup(self._mosi, gpio.OUT, initial=gpio.LOW)
        gpio.setup(self._miso, gpio.IN)
        gpio.setup(self._cs, gpio.OUT, initial=gpio.HIGH)

    def xfer2(self, data: list[int]) -> list[int]:
        gpio = self._gpio_module()
        received_bytes = []
        gpio.output(self._cs, gpio.LOW)
        try:
            for byte in data:
                received = 0
                for bit_index in range(7, -1, -1):
                    # Data is set up while the clock is low, then sampled by
                    # both sides on the rising edge - standard SPI mode 0.
                    gpio.output(self._mosi, (byte >> bit_index) & 1)
                    time.sleep(self._half_period)
                    gpio.output(self._sck, gpio.HIGH)
                    if gpio.input(self._miso):
                        received |= 1 << bit_index
                    time.sleep(self._half_period)
                    gpio.output(self._sck, gpio.LOW)
                received_bytes.append(received)
        finally:
            gpio.output(self._cs, gpio.HIGH)
        return received_bytes

    def close(self) -> None:
        gpio = self._gpio_module()
        for pin in (self._sck, self._mosi, self._miso, self._cs):
            try:
                gpio.cleanup(pin)
            except Exception:  # pragma: no cover - best-effort hardware cleanup
                pass
