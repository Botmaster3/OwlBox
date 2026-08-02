from __future__ import annotations


class NullControls:
    """Used in simulate mode / on dev machines without real GPIO hardware."""

    def close(self) -> None:
        pass
