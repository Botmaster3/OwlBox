from .base import NullControls

__all__ = ["NullControls", "create_controls"]


def create_controls(config, on_next, on_prev, on_toggle_pause, on_volume_delta, on_seek, on_shutdown=None):
    if config.simulate:
        return NullControls()
    from .gpio_controls import GpioControls

    return GpioControls(config.gpio, on_next, on_prev, on_toggle_pause, on_volume_delta, on_seek, on_shutdown)
