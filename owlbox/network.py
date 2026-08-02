"""Thin wrapper around NetworkManager's nmcli for WiFi status/scan/connect.

Status and scanning work unprivileged; toggling the radio and connecting to a
network need passwordless sudo for nmcli on the owlbox service user (see
docs/hardware.md). Every function is best-effort: on a dev machine without
NetworkManager (or in the sandbox this was built in) these simply return
empty/failed results instead of raising, matching how player.py/engine.py
degrade when the real hardware isn't there.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Optional

logger = logging.getLogger("owlbox.network")


def _run(args: list[str], timeout: float = 10.0) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout


def get_status() -> dict:
    enabled = _run(["nmcli", "-t", "-f", "WIFI", "radio"]).strip().lower() == "enabled"

    connected_ssid = None
    for line in _run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"]).splitlines():
        active, _, ssid = line.partition(":")
        if active == "yes" and ssid:
            connected_ssid = ssid
            break

    ip_address = None
    hostname_output = _run(["hostname", "-I"]).split()
    if hostname_output:
        ip_address = hostname_output[0]

    return {"enabled": enabled, "connected_ssid": connected_ssid, "ip_address": ip_address}


def scan_networks() -> list[dict]:
    subprocess.run(["nmcli", "dev", "wifi", "rescan"], capture_output=True, timeout=10, check=False)

    networks = []
    seen = set()
    for line in _run(["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi", "list"]).splitlines():
        ssid, _, signal = line.partition(":")
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        try:
            signal_value = int(signal)
        except ValueError:
            signal_value = None
        networks.append({"ssid": ssid, "signal": signal_value})

    networks.sort(key=lambda n: n["signal"] or 0, reverse=True)
    return networks


def connect(ssid: str, password: str) -> tuple[bool, str]:
    args = ["sudo", "nmcli", "dev", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, "Verbunden."
    return False, (result.stderr or result.stdout or "Verbindung fehlgeschlagen.").strip()


def set_wifi_enabled(enabled: bool) -> None:
    try:
        subprocess.run(["sudo", "nmcli", "radio", "wifi", "on" if enabled else "off"], check=False)
    except Exception:
        logger.exception("failed to toggle wifi radio")
