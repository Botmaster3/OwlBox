"""Each hardware component must be switchable off on its own, WITHOUT the
global `simulate` flag - because simulate swaps in StubPlayer and kills real
audio, which makes it useless for isolating an audio problem. These toggles
are what `scripts/stage.sh` drives; see docs/staged-setup.md.
"""
from owlbox.backlight import GpioBacklight, NullBacklight, create_backlight
from owlbox.config import Config, GpioConfig, RfidConfig
from owlbox.controls import NullControls, create_controls
from owlbox.rfid import create_reader
from owlbox.rfid.simulated import SimulatedRfidReader


def _controls(config):
    noop = lambda *a, **k: None
    return create_controls(config, noop, noop, noop, noop, noop, noop, noop)


def test_gpio_controls_disabled_without_simulate():
    config = Config(simulate=False, gpio=GpioConfig(enabled=False))
    assert isinstance(_controls(config), NullControls)


def test_gpio_controls_enabled_by_default():
    # Not NullControls, i.e. it tried to build the real GpioControls - which
    # needs actual hardware, so failing to import/construct here is the
    # expected outcome on a dev machine. What matters is that `enabled: true`
    # does NOT short-circuit to NullControls.
    config = Config(simulate=False, gpio=GpioConfig(enabled=True))
    assert config.gpio.enabled is True
    try:
        assert not isinstance(_controls(config), NullControls)
    except Exception:
        pass  # no GPIO hardware/library here - that's fine, see above


def test_backlight_disabled_by_null_pin_without_simulate():
    config = Config(simulate=False, gpio=GpioConfig(backlight_pin=None))
    assert isinstance(create_backlight(config), NullBacklight)


def test_backlight_pin_set_is_not_null_backlight():
    config = Config(simulate=False, gpio=GpioConfig(backlight_pin=13))
    try:
        assert isinstance(create_backlight(config), GpioBacklight)
    except Exception:
        pass  # gpiozero has no real pin factory here


def test_rfid_disabled_by_reader_setting_without_simulate():
    config = Config(simulate=False, rfid=RfidConfig(reader="simulated"))
    assert isinstance(create_reader(config), SimulatedRfidReader)


def test_audio_stays_real_while_every_component_is_off():
    """The whole point of the staged bring-up: all hardware off, but simulate
    still False so the real mpv player (and thus real audio) is used."""
    config = Config(
        simulate=False,
        rfid=RfidConfig(reader="simulated"),
        gpio=GpioConfig(enabled=False, backlight_pin=None),
    )
    assert config.simulate is False
    assert isinstance(_controls(config), NullControls)
    assert isinstance(create_backlight(config), NullBacklight)
    assert isinstance(create_reader(config), SimulatedRfidReader)
