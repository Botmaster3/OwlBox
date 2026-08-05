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
