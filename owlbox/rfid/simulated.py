from __future__ import annotations

import threading
from typing import Optional


class SimulatedRfidReader:
    """Dev/test stand-in for the real reader. The admin UI's "Chip simulieren" tool
    (and tests) call inject()/clear() to pretend a tag was placed on / taken off the box."""

    def __init__(self):
        self._lock = threading.Lock()
        self._uid: Optional[str] = None
        self._clear_timer: Optional[threading.Timer] = None

    def inject(self, uid: str, hold_seconds: Optional[float] = None) -> None:
        with self._lock:
            if self._clear_timer is not None:
                self._clear_timer.cancel()
                self._clear_timer = None
            self._uid = uid
            if hold_seconds:
                self._clear_timer = threading.Timer(hold_seconds, self.clear)
                self._clear_timer.daemon = True
                self._clear_timer.start()

    def clear(self) -> None:
        with self._lock:
            self._uid = None

    def read_uid(self) -> Optional[str]:
        with self._lock:
            return self._uid

    def close(self) -> None:
        with self._lock:
            if self._clear_timer is not None:
                self._clear_timer.cancel()
