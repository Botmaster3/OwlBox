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

No time.sleep() between edges (there used to be one, half_period below is
what it used to be sized at - kept only so an explicit delay can still be
requested, see below).
Confirmed on real hardware, via a clean staged bring-up (see
docs/staged-setup.md): audio played back clean through the "display" stage
(app + kiosk running, RFID still off), and started crackling the moment the
"rfid" stage turned RFID on - nothing else changed between those two
states. What's NOT yet confirmed is that the sleep removal below is the
actual fix (only the enable-RFID -> crackling correlation is) - it's the
most plausible mechanism, not a proven one:
Python's time.sleep() has an OS scheduling floor - on the machine used to
investigate this, a requested 2us sleep measured ~75us in practice (~38x),
which would turn the intended "quick" half-period into real, continuous
nanosleep-syscall churn: read_uid() alone issues on the order of a
thousand sleeps, several times a second (rfid.poll_interval), enough
scheduling pressure to intermittently starve mpv's audio thread even
though CPU utilization looks low in a snapshot. That floor wasn't measured
on the actual Pi 3B+ this runs on, so treat the mechanism as the leading
hypothesis, and the removal here as something that still needs to be
re-tested with RFID enabled before calling it fixed.
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
        half_period: float = 0.0,
    ):
        self._sck = sck_pin
        self._mosi = mosi_pin
        self._miso = miso_pin
        self._cs = cs_pin
        self._gpio = gpio_module
        # 0 by default - see the module docstring for why an explicit delay
        # here caused real, measured audio crackling. Only pass a non-zero
        # value if a particular RC522 board/wiring turns out to need extra
        # settle time (flaky reads) - "no minimum clock speed" doesn't rule
        # out a specific breadboard/cable being electrically noisier than
        # the datasheet case.
        self._half_period = half_period
        # Accepted for API compatibility with spidev.SpiDev (mfrc522.MFRC522
        # sets this after construction) - meaningless here, bit-banging has
        # no clock-speed register to program.
        self.max_speed_hz = 1_000_000

    def _gpio_module(self):
        if self._gpio is None:
            # lgpio, not RPi.GPIO - see Mfrc522Reader for why the two can't
            # coexist in the same process on current Raspberry Pi OS kernels.
            from .lgpio_compat import LgpioCompat

            self._gpio = LgpioCompat()
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
                    # No sleep between edges - see the module docstring.
                    gpio.output(self._mosi, (byte >> bit_index) & 1)
                    if self._half_period:
                        time.sleep(self._half_period)
                    gpio.output(self._sck, gpio.HIGH)
                    if gpio.input(self._miso):
                        received |= 1 << bit_index
                    if self._half_period:
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
