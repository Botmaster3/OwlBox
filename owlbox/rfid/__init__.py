from .base import RfidReader
from .simulated import SimulatedRfidReader

__all__ = ["RfidReader", "SimulatedRfidReader", "create_reader"]


def create_reader(config):
    if config.simulate or config.rfid.reader == "simulated":
        return SimulatedRfidReader()
    from .mfrc522_reader import Mfrc522Reader

    return Mfrc522Reader(config.rfid)
