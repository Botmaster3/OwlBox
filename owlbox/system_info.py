"""Best-effort system stats for the /admin/info page - disk/memory/CPU temp/uptime/
hardware model. Falls back to None on a dev machine without these /proc/sys files
instead of raising, matching how player.py/network.py degrade without real hardware."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


def get_disk_usage(path: Path) -> dict:
    usage = shutil.disk_usage(path)
    return {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free}


def get_memory_info() -> Optional[dict]:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, _, rest = line.partition(":")
            rest = rest.strip()
            if rest.endswith("kB"):
                values[key] = int(rest[:-2].strip()) * 1024
    except (OSError, ValueError):
        return None
    total = values.get("MemTotal")
    if total is None:
        return None
    available = values.get("MemAvailable")
    used = total - available if available is not None else None
    return {"total_bytes": total, "available_bytes": available, "used_bytes": used}


def get_cpu_temperature_celsius() -> Optional[float]:
    try:
        raw = Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()
        return int(raw) / 1000
    except (OSError, ValueError):
        return None


def get_uptime_seconds() -> Optional[float]:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def get_hardware_model() -> Optional[str]:
    try:
        return Path("/proc/device-tree/model").read_text().strip("\x00").strip()
    except OSError:
        return None


def get_os_pretty_name() -> Optional[str]:
    try:
        data = {}
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                data[key] = value.strip('"')
        return data.get("PRETTY_NAME")
    except OSError:
        return None
