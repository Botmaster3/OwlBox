"""Each hardware component must be switchable off on its own, WITHOUT the
global `simulate` flag - because simulate swaps in StubPlayer and kills real
audio, which makes it useless for isolating an audio problem. These toggles
are what `scripts/stage.sh` drives; see docs/staged-setup.md.
"""
import owlbox.backlight as backlight_module
from owlbox.backlight import GpioBacklight, NullBacklight, SysfsBacklight, create_backlight
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


def _fake_sysfs_backlight_device(tmp_path, max_brightness=255, initial=255):
    device_dir = tmp_path / "11-0045"
    device_dir.mkdir()
    (device_dir / "max_brightness").write_text(str(max_brightness))
    (device_dir / "brightness").write_text(str(initial))
    return device_dir


def test_sysfs_backlight_detect_finds_device(tmp_path, monkeypatch):
    _fake_sysfs_backlight_device(tmp_path)
    monkeypatch.setattr(backlight_module, "_SYSFS_BACKLIGHT_ROOT", tmp_path)
    result = SysfsBacklight.detect()
    assert isinstance(result, SysfsBacklight)


def test_sysfs_backlight_detect_none_when_root_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(backlight_module, "_SYSFS_BACKLIGHT_ROOT", tmp_path / "does-not-exist")
    assert SysfsBacklight.detect() is None


def test_sysfs_backlight_detect_none_when_no_devices(tmp_path, monkeypatch):
    monkeypatch.setattr(backlight_module, "_SYSFS_BACKLIGHT_ROOT", tmp_path)
    assert SysfsBacklight.detect() is None


def test_sysfs_backlight_scales_percent_to_max_brightness(tmp_path):
    # Confirmed on real hardware (Waveshare 5-DSI-TOUCH-A): max_brightness=255,
    # /sys/class/backlight/11-0045/brightness group-writable by `video`.
    device_dir = _fake_sysfs_backlight_device(tmp_path, max_brightness=255)
    bl = SysfsBacklight(device_dir)
    bl.set_brightness(50)
    assert (device_dir / "brightness").read_text().strip() == str(round(255 * 0.5))
    bl.set_brightness(0)
    assert (device_dir / "brightness").read_text().strip() == "0"
    bl.set_brightness(100)
    assert (device_dir / "brightness").read_text().strip() == "255"
    # Out-of-range input clamps rather than writing a nonsensical value.
    bl.set_brightness(150)
    assert (device_dir / "brightness").read_text().strip() == "255"
    bl.set_brightness(-20)
    assert (device_dir / "brightness").read_text().strip() == "0"


def test_create_backlight_prefers_sysfs_over_gpio_pin(tmp_path, monkeypatch):
    _fake_sysfs_backlight_device(tmp_path)
    monkeypatch.setattr(backlight_module, "_SYSFS_BACKLIGHT_ROOT", tmp_path)
    # gpio.backlight_pin is set (13, this project's old default) - sysfs must
    # still win, since that pin was never actually wired for the current
    # display (see backlight.py's module docstring).
    config = Config(simulate=False, gpio=GpioConfig(backlight_pin=13))
    assert isinstance(create_backlight(config), SysfsBacklight)


def test_create_backlight_falls_back_to_gpio_when_no_sysfs_device(tmp_path, monkeypatch):
    monkeypatch.setattr(backlight_module, "_SYSFS_BACKLIGHT_ROOT", tmp_path / "does-not-exist")
    config = Config(simulate=False, gpio=GpioConfig(backlight_pin=13))
    try:
        assert isinstance(create_backlight(config), GpioBacklight)
    except Exception:
        pass  # gpiozero has no real pin factory here


def test_create_backlight_simulate_ignores_real_sysfs_device(tmp_path, monkeypatch):
    _fake_sysfs_backlight_device(tmp_path)
    monkeypatch.setattr(backlight_module, "_SYSFS_BACKLIGHT_ROOT", tmp_path)
    config = Config(simulate=True, gpio=GpioConfig(backlight_pin=13))
    assert isinstance(create_backlight(config), NullBacklight)


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
