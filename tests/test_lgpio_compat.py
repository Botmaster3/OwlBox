import sys
import types

import pytest


def _make_fake_lgpio():
    fake = types.ModuleType("lgpio")
    fake.calls = []
    fake._values = {}
    next_handle = [0]

    def gpiochip_open(chip):
        fake.calls.append(("gpiochip_open", chip))
        handle = next_handle[0]
        next_handle[0] += 1
        return handle

    def gpio_claim_output(handle, pin, level):
        fake.calls.append(("gpio_claim_output", handle, pin, level))
        fake._values[(handle, pin)] = level

    def gpio_claim_input(handle, pin):
        fake.calls.append(("gpio_claim_input", handle, pin))

    def gpio_write(handle, pin, value):
        fake.calls.append(("gpio_write", handle, pin, value))
        fake._values[(handle, pin)] = value

    def gpio_read(handle, pin):
        fake.calls.append(("gpio_read", handle, pin))
        return fake._values.get((handle, pin), 0)

    def gpio_free(handle, pin):
        fake.calls.append(("gpio_free", handle, pin))

    def gpiochip_close(handle):
        fake.calls.append(("gpiochip_close", handle))

    fake.gpiochip_open = gpiochip_open
    fake.gpio_claim_output = gpio_claim_output
    fake.gpio_claim_input = gpio_claim_input
    fake.gpio_write = gpio_write
    fake.gpio_read = gpio_read
    fake.gpio_free = gpio_free
    fake.gpiochip_close = gpiochip_close
    return fake


@pytest.fixture
def fake_lgpio(monkeypatch):
    """Installs a fake `lgpio` module before owlbox.rfid.lgpio_compat is
    imported - real `lgpio` is a Pi-only C extension, not installed here."""
    fake = _make_fake_lgpio()
    monkeypatch.setitem(sys.modules, "lgpio", fake)
    monkeypatch.delitem(sys.modules, "owlbox.rfid.lgpio_compat", raising=False)
    return fake


def test_setup_claims_output_pin_with_initial_level(fake_lgpio):
    from owlbox.rfid.lgpio_compat import LgpioCompat

    gpio = LgpioCompat()
    gpio.setup(4, gpio.OUT, initial=gpio.HIGH)

    assert ("gpio_claim_output", 0, 4, 1) in fake_lgpio.calls


def test_setup_claims_input_pin(fake_lgpio):
    from owlbox.rfid.lgpio_compat import LgpioCompat

    gpio = LgpioCompat()
    gpio.setup(15, gpio.IN)

    assert ("gpio_claim_input", 0, 15) in fake_lgpio.calls


def test_output_and_input_round_trip_through_the_same_backing_store(fake_lgpio):
    from owlbox.rfid.lgpio_compat import LgpioCompat

    gpio = LgpioCompat()
    gpio.setup(4, gpio.OUT)
    gpio.output(4, 1)

    assert gpio.input(4) == 1


def test_repeated_setup_frees_before_reclaiming(fake_lgpio):
    # Matches RPi.GPIO's own leniency: re-setup of an already-claimed pin is
    # a warning there, not an error - lgpio itself would raise 'GPIO busy'
    # on a double-claim, so LgpioCompat must free first.
    from owlbox.rfid.lgpio_compat import LgpioCompat

    gpio = LgpioCompat()
    gpio.setup(4, gpio.OUT)
    gpio.setup(4, gpio.OUT)

    relevant = [c for c in fake_lgpio.calls if c[0] in ("gpio_claim_output", "gpio_free")]
    assert relevant == [
        ("gpio_claim_output", 0, 4, 0),
        ("gpio_free", 0, 4),
        ("gpio_claim_output", 0, 4, 0),
    ]


def test_close_chip_frees_every_claimed_pin_and_closes_the_handle(fake_lgpio):
    from owlbox.rfid.lgpio_compat import LgpioCompat

    gpio = LgpioCompat()
    gpio.setup(4, gpio.OUT)
    gpio.setup(15, gpio.IN)

    gpio.close_chip()

    freed = {c[2] for c in fake_lgpio.calls if c[0] == "gpio_free"}
    assert freed == {4, 15}
    assert ("gpiochip_close", 0) in fake_lgpio.calls


def test_explicit_chip_argument_bypasses_detection(fake_lgpio):
    # An explicit chip= always wins, no revision/gpiochip4 probing at all -
    # covers callers (tests, or a future manual override) that don't want
    # auto-detection.
    from owlbox.rfid.lgpio_compat import LgpioCompat

    LgpioCompat(chip=7)

    assert ("gpiochip_open", 7) in fake_lgpio.calls


def test_detect_chip_defaults_to_0_when_no_revision_is_readable(fake_lgpio, monkeypatch, tmp_path):
    # The sandbox/CI environment this test suite normally runs in has neither
    # /proc/device-tree nor a Pi-style /proc/cpuinfo - _detect_chip() must
    # degrade to the historical default rather than raise.
    from owlbox.rfid import lgpio_compat

    monkeypatch.setattr(lgpio_compat, "_get_pi_revision", lambda: None)

    assert lgpio_compat._detect_chip() == 0


def test_detect_chip_picks_4_on_a_pi5_revision_when_gpiochip4_exists(fake_lgpio, monkeypatch):
    from owlbox.rfid import lgpio_compat

    # 0x17 in bits 4-11 is BCM2712 (Pi 5) in the new-style revision code -
    # the rest of the bits are arbitrary/don't matter for this check.
    monkeypatch.setattr(lgpio_compat, "_get_pi_revision", lambda: 0xC04170)
    monkeypatch.setattr(lgpio_compat.os.path, "exists", lambda path: path == "/dev/gpiochip4")

    assert lgpio_compat._detect_chip() == 4


def test_detect_chip_falls_back_to_0_on_pi5_if_gpiochip4_is_missing(fake_lgpio, monkeypatch):
    # Matches gpiozero's own guard: a kernel where the RP1 chip enumerates
    # back at gpiochip0 (no /dev/gpiochip4 node at all) must not still force
    # chip 4 just because the revision says Pi 5.
    from owlbox.rfid import lgpio_compat

    monkeypatch.setattr(lgpio_compat, "_get_pi_revision", lambda: 0xC04170)
    monkeypatch.setattr(lgpio_compat.os.path, "exists", lambda path: False)

    assert lgpio_compat._detect_chip() == 0


def test_detect_chip_defaults_to_0_on_a_non_pi5_revision(fake_lgpio, monkeypatch):
    # 0x11 is a Pi 3B+ (BCM2837B0) - must never pick chip 4, even if
    # /dev/gpiochip4 happens to exist for some unrelated reason.
    from owlbox.rfid import lgpio_compat

    monkeypatch.setattr(lgpio_compat, "_get_pi_revision", lambda: 0xA020D3)
    monkeypatch.setattr(lgpio_compat.os.path, "exists", lambda path: True)

    assert lgpio_compat._detect_chip() == 0


def test_get_pi_revision_reads_device_tree_first(fake_lgpio, monkeypatch, tmp_path):
    from owlbox.rfid import lgpio_compat

    dt_path = tmp_path / "linux,revision"
    dt_path.write_bytes((0xC04170).to_bytes(4, "big"))

    real_open = open

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/device-tree/system/linux,revision":
            return real_open(dt_path, mode, *args, **kwargs)
        raise AssertionError(f"unexpected open: {path}")

    monkeypatch.setattr(lgpio_compat, "open", fake_open, raising=False)

    assert lgpio_compat._get_pi_revision() == 0xC04170


def test_get_pi_revision_falls_back_to_cpuinfo(fake_lgpio, monkeypatch):
    from owlbox.rfid import lgpio_compat

    import io

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/device-tree/system/linux,revision":
            raise FileNotFoundError(path)
        if path == "/proc/cpuinfo":
            return io.StringIO("Hardware\t: BCM2835\nRevision\t: c04170\n")
        raise AssertionError(f"unexpected open: {path}")

    monkeypatch.setattr(lgpio_compat, "open", fake_open, raising=False)

    assert lgpio_compat._get_pi_revision() == 0xC04170


def test_get_pi_revision_strips_the_overvolted_prefix_from_cpuinfo(fake_lgpio, monkeypatch):
    # Old-style 4-hex-digit revision "000d" (Pi Model B rev 2), overvolted -
    # "100" gets prepended ("100000d"); the real code is the last 4 chars.
    from owlbox.rfid import lgpio_compat

    import io

    def fake_open(path, mode="r", *args, **kwargs):
        if path == "/proc/device-tree/system/linux,revision":
            raise FileNotFoundError(path)
        if path == "/proc/cpuinfo":
            return io.StringIO("Revision\t: 100000d\n")
        raise AssertionError(f"unexpected open: {path}")

    monkeypatch.setattr(lgpio_compat, "open", fake_open, raising=False)

    assert lgpio_compat._get_pi_revision() == 0x000D
