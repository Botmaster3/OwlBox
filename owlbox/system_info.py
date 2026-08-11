"""Best-effort system stats for the /admin/info page - disk/memory/CPU temp/uptime/
hardware model. Falls back to None on a dev machine without these /proc/sys files
instead of raising, matching how player.py/network.py degrade without real hardware.

get_hostname()/set_hostname() are the one exception to "read-only" here - lives in
this module anyway rather than a dedicated one, since a device's hostname is exactly
the kind of small system-identity fact this file already deals with (see the admin
nav's hostname badge in _admin_nav.html, added so multiple OwlBoxen in the same house
are distinguishable in the web UI - never shown on the kiosk display itself)."""
from __future__ import annotations

import re
import shutil
import socket
import subprocess
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


# -- hostname (see module docstring for why this write path lives here) -----

_HOSTNAME_INVALID_CHARS = re.compile(r"[^a-z0-9-]")
_HOSTNAME_DASH_RUN = re.compile(r"-{2,}")


def get_hostname() -> str:
    return socket.gethostname()


def normalize_hostname(raw: str) -> str:
    """Turns free-form input ("OwlBox Kinderzimmer!") into a valid single-label
    hostname ("owlbox-kinderzimmer") - lowercase letters/digits/hyphens only, no
    leading/trailing/repeated hyphen, max 63 chars (the DNS/mDNS label limit that
    hostnamectl itself enforces). A parent naming a box after its room shouldn't
    have to know DNS label syntax first, so this normalizes instead of rejecting
    - set_hostname() below reports back what was actually applied."""
    name = raw.strip().lower()
    name = re.sub(r"\s+", "-", name)
    name = _HOSTNAME_INVALID_CHARS.sub("", name)
    name = _HOSTNAME_DASH_RUN.sub("-", name)
    name = name.strip("-")
    return name[:63]


def set_hostname(raw: str) -> tuple[bool, str]:
    """Applies a new system hostname via hostnamectl (needs the owlbox service
    user's passwordless-sudo rule for it, see scripts/install.sh). Returns
    (True, normalized_name) on success or (False, error_message) on failure -
    unlike feedback.py's chimes, a failed hostname change must be visible to
    whoever just clicked "Speichern", not swallowed. Takes effect immediately
    for anything reading the live hostname (this module's own get_hostname(),
    the shell prompt, ...); a reboot is still the reliable way to make the new
    <name>.local resolve everywhere via mDNS/avahi, since avahi-daemon doesn't
    necessarily notice a runtime rename on its own."""
    name = normalize_hostname(raw)
    if not name:
        return False, "Ungültiger Name - bitte Buchstaben oder Zahlen verwenden."
    try:
        result = subprocess.run(
            ["sudo", "hostnamectl", "set-hostname", name],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, name
    return False, (result.stderr or result.stdout or "Hostname konnte nicht geändert werden.").strip()
