from owlbox.rfid.soft_spi import SoftSpi


class FakeGPIO:
    """Records every setup()/output() call and feeds back a scripted sequence
    of input() (MISO) values - enough to verify SoftSpi's bit-banging without
    any real hardware."""

    OUT = "OUT"
    IN = "IN"
    HIGH = 1
    LOW = 0
    BCM = "BCM"

    def __init__(self, miso_sequence=None):
        self._miso_sequence = list(miso_sequence or [])
        self.setup_calls = []
        self.output_calls = []  # list of (pin, value), in call order
        self.cleanup_calls = []
        self._mode = None

    def getmode(self):
        return self._mode

    def setmode(self, mode):
        self._mode = mode

    def setup(self, pin, direction, initial=None):
        self.setup_calls.append((pin, direction, initial))

    def output(self, pin, value):
        self.output_calls.append((pin, value))

    def input(self, pin):
        return self._miso_sequence.pop(0)

    def cleanup(self, pin):
        self.cleanup_calls.append(pin)


def _mosi_bits(gpio, mosi_pin):
    return [v for (pin, v) in gpio.output_calls if pin == mosi_pin]


def _cs_values(gpio, cs_pin):
    return [v for (pin, v) in gpio.output_calls if pin == cs_pin]


def test_open_configures_pins_and_default_levels():
    gpio = FakeGPIO()
    spi = SoftSpi(sck_pin=4, mosi_pin=16, miso_pin=15, cs_pin=14, gpio_module=gpio)
    spi.open(0, 0)

    assert (4, gpio.OUT, gpio.LOW) in gpio.setup_calls
    assert (16, gpio.OUT, gpio.LOW) in gpio.setup_calls
    assert (15, gpio.IN, None) in gpio.setup_calls
    assert (14, gpio.OUT, gpio.HIGH) in gpio.setup_calls  # CS idles high


def test_xfer2_sends_bytes_msb_first_on_mosi():
    gpio = FakeGPIO(miso_sequence=[0] * 16)
    spi = SoftSpi(sck_pin=4, mosi_pin=16, miso_pin=15, cs_pin=14, gpio_module=gpio)
    spi.open(0, 0)

    spi.xfer2([0b10110010, 0x00])

    assert _mosi_bits(gpio, 16) == [1, 0, 1, 1, 0, 0, 1, 0] + [0] * 8


def test_xfer2_reads_bytes_msb_first_from_miso():
    # First byte's 8 clock pulses read back zero (ignored), second byte's
    # pulses read back 0b01100110.
    gpio = FakeGPIO(miso_sequence=[0] * 8 + [0, 1, 1, 0, 0, 1, 1, 0])
    spi = SoftSpi(sck_pin=4, mosi_pin=16, miso_pin=15, cs_pin=14, gpio_module=gpio)
    spi.open(0, 0)

    result = spi.xfer2([0x00, 0x00])

    assert result == [0x00, 0b01100110]


def test_xfer2_asserts_cs_low_during_transfer_and_releases_after():
    gpio = FakeGPIO(miso_sequence=[0] * 8)
    spi = SoftSpi(sck_pin=4, mosi_pin=16, miso_pin=15, cs_pin=14, gpio_module=gpio)
    spi.open(0, 0)

    spi.xfer2([0x00])

    cs_values = _cs_values(gpio, 14)
    assert cs_values[0] == gpio.LOW
    assert cs_values[-1] == gpio.HIGH


def test_close_releases_all_four_pins():
    gpio = FakeGPIO()
    spi = SoftSpi(sck_pin=4, mosi_pin=16, miso_pin=15, cs_pin=14, gpio_module=gpio)
    spi.open(0, 0)

    spi.close()

    assert set(gpio.cleanup_calls) == {4, 16, 15, 14}
