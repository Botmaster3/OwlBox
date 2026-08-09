from .base import NullControls

__all__ = ["NullControls", "create_controls"]


def create_controls(
    config,
    on_next,
    on_prev,
    on_toggle_pause,
    on_volume_delta,
    on_seek,
    on_brightness_delta,
    on_shutdown=None,
):
    # gpio.enabled is the per-component switch (see GpioConfig.enabled):
    # simulate turns off everything at once, this turns off only the physical
    # buttons/encoders while real audio keeps working.
    if config.simulate or not config.gpio.enabled:
        return NullControls()
    from .gpio_controls import GpioControls

    return GpioControls(
        config.gpio,
        on_next,
        on_prev,
        on_toggle_pause,
        on_volume_delta,
        on_seek,
        on_brightness_delta,
        on_shutdown,
    )
