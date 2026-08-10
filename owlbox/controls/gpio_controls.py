from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger("owlbox.controls")

# gpiozero requires an unreasonably large hold_time to effectively disable long-press
# detection when the shutdown feature is turned off in config.
_HOLD_DISABLED = 1e9


class GpioControls:
    """Two push buttons (next/prev) plus two rotary encoders: one with a push switch
    for volume (rotate = volume +/-, click = play/pause, optional long-press shutdown),
    and one dedicated to display brightness (rotate = brightness +/-, click = toggle
    night mode, if gpio_config.brightness_encoder_switch is wired)."""

    def __init__(
        self,
        gpio_config,
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_toggle_pause: Callable[[], None],
        on_volume_delta: Callable[[int], None],
        on_seek: Callable[[float], None],
        on_brightness_delta: Callable[[int], None],
        on_shutdown: Optional[Callable[[], None]] = None,
        on_night_toggle: Optional[Callable[[], None]] = None,
    ):
        from gpiozero import Button, RotaryEncoder

        self._on_next = on_next
        self._on_prev = on_prev
        self._on_toggle_pause = on_toggle_pause
        self._on_volume_delta = on_volume_delta
        self._on_seek = on_seek
        self._on_brightness_delta = on_brightness_delta
        self._on_shutdown = on_shutdown
        self._on_night_toggle = on_night_toggle
        self._long_press_triggered = False
        self._seek_step_seconds = gpio_config.seek_step_seconds
        self._next_held = False
        self._prev_held = False

        # Next/prev act on release, not on press: a short tap jumps to the next/
        # previous track, but holding past seek_hold_seconds instead repeatedly
        # fast-forwards/rewinds within the current track (when_held fires every
        # seek_hold_seconds while held, thanks to hold_repeat) and suppresses the
        # track jump that would otherwise fire on release.
        self._btn_next = Button(
            gpio_config.button_next,
            pull_up=True,
            bounce_time=gpio_config.bounce_time,
            hold_time=gpio_config.seek_hold_seconds,
            hold_repeat=True,
        )
        self._btn_next.when_held = self._handle_next_held
        self._btn_next.when_released = self._handle_next_released

        self._btn_prev = Button(
            gpio_config.button_prev,
            pull_up=True,
            bounce_time=gpio_config.bounce_time,
            hold_time=gpio_config.seek_hold_seconds,
            hold_repeat=True,
        )
        self._btn_prev.when_held = self._handle_prev_held
        self._btn_prev.when_released = self._handle_prev_released

        self._encoder = RotaryEncoder(
            gpio_config.encoder_clk,
            gpio_config.encoder_dt,
            max_steps=0,
            bounce_time=gpio_config.bounce_time,
        )
        self._encoder.when_rotated_clockwise = lambda: self._safe(self._on_volume_delta, 1)
        self._encoder.when_rotated_counter_clockwise = lambda: self._safe(self._on_volume_delta, -1)

        self._brightness_encoder = RotaryEncoder(
            gpio_config.brightness_encoder_clk,
            gpio_config.brightness_encoder_dt,
            max_steps=0,
            bounce_time=gpio_config.bounce_time,
        )
        self._brightness_encoder.when_rotated_clockwise = lambda: self._safe(self._on_brightness_delta, 1)
        self._brightness_encoder.when_rotated_counter_clockwise = lambda: self._safe(self._on_brightness_delta, -1)

        # Optional: the brightness encoder's own push switch, toggling night
        # mode. Only wired if a pin is actually configured - unlike the volume
        # encoder's switch (always present, this project's baseline hardware),
        # this one was unwired hardware until night mode existed, so None
        # (feature disabled, no pin claimed) has to stay a valid choice.
        self._brightness_encoder_button = None
        switch_pin = gpio_config.brightness_encoder_switch
        if switch_pin is not None and on_night_toggle is not None:
            self._brightness_encoder_button = Button(
                switch_pin, pull_up=True, bounce_time=gpio_config.bounce_time
            )
            self._brightness_encoder_button.when_released = lambda: self._safe(self._on_night_toggle)

        shutdown_after = gpio_config.shutdown_hold_seconds
        hold_time = shutdown_after if shutdown_after and shutdown_after > 0 else _HOLD_DISABLED
        self._encoder_button = Button(
            gpio_config.encoder_switch, pull_up=True, bounce_time=gpio_config.bounce_time, hold_time=hold_time
        )
        self._encoder_button.when_released = self._handle_encoder_release
        if shutdown_after and shutdown_after > 0 and on_shutdown is not None:
            self._encoder_button.when_held = self._handle_shutdown

    def _safe(self, fn: Callable, *args) -> None:
        try:
            fn(*args)
        except Exception:
            logger.exception("control callback failed")

    def _handle_next_held(self) -> None:
        self._next_held = True
        self._safe(self._on_seek, self._seek_step_seconds)

    def _handle_next_released(self) -> None:
        if self._next_held:
            self._next_held = False
            return
        self._safe(self._on_next)

    def _handle_prev_held(self) -> None:
        self._prev_held = True
        self._safe(self._on_seek, -self._seek_step_seconds)

    def _handle_prev_released(self) -> None:
        if self._prev_held:
            self._prev_held = False
            return
        self._safe(self._on_prev)

    def _handle_encoder_release(self) -> None:
        if self._long_press_triggered:
            self._long_press_triggered = False
            return
        self._safe(self._on_toggle_pause)

    def _handle_shutdown(self) -> None:
        self._long_press_triggered = True
        logger.warning("encoder held for shutdown threshold, triggering shutdown callback")
        if self._on_shutdown is not None:
            self._safe(self._on_shutdown)

    def close(self) -> None:
        devices = [
            self._btn_next,
            self._btn_prev,
            self._encoder,
            self._encoder_button,
            self._brightness_encoder,
        ]
        if self._brightness_encoder_button is not None:
            devices.append(self._brightness_encoder_button)
        for device in devices:
            try:
                device.close()
            except Exception:
                pass
