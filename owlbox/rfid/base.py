from __future__ import annotations

from typing import Optional, Protocol


class RfidReader(Protocol):
    """A reader only ever reports what's in front of it *right now* - no blocking,
    no debouncing. The engine's poll loop decides what "removed" means."""

    def read_uid(self) -> Optional[str]:
        """Return the hex UID of a tag currently in range, or None if none is present."""
        ...

    def close(self) -> None: ...
