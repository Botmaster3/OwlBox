from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger("owlbox.controls")

# gpiozero requires an unreasonably large hold_time to effectively disable long-press
# detection when the shutdown feature is turned off in config.
_HOLD_DISABLED = 1e9


class GpioControls:
    """Two push buttons (next/prev) plus a rotary encoder with a push switch
    (volume +/- on rotate, play/pause on click, optional long-press shutdown)."""

    def __init__(
        self,
        gpio_config,
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_toggle_pause: Callable[[], None],
        on_volume_delta: Callable[[int], None],
        on_shutdown: Optional[Callable[[], None]] = None,
    ):
        from gpiozero import Button, RotaryEncoder

        self._on_next = on_next
        self._on_prev = on_prev
        self._on_toggle_pause = on_toggle_pause
        self._on_volume_delta = on_volume_delta
        self._on_shutdown = on_shutdown
        self._long_press_triggered = False

        self._btn_next = Button(gpio_config.button_next, pull_up=True, bounce_time=gpio_config.bounce_time)
        self._btn_next.when_pressed = lambda: self._safe(self._on_next)

        self._btn_prev = Button(gpio_config.button_prev, pull_up=True, bounce_time=gpio_config.bounce_time)
        self._btn_prev.when_pressed = lambda: self._safe(self._on_prev)

        self._encoder = RotaryEncoder(
            gpio_config.encoder_clk,
            gpio_config.encoder_dt,
            max_steps=0,
            bounce_time=gpio_config.bounce_time,
        )
        self._encoder.when_rotated_clockwise = lambda: self._safe(self._on_volume_delta, 1)
        self._encoder.when_rotated_counter_clockwise = lambda: self._safe(self._on_volume_delta, -1)

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
        for device in (self._btn_next, self._btn_prev, self._encoder, self._encoder_button):
            try:
                device.close()
            except Exception:
                pass
