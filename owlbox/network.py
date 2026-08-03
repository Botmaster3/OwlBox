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
import socket
import subprocess
from typing import Optional

logger = logging.getLogger("owlbox.network")

# Fixed connection-profile name for the fallback hotspot (see start_hotspot below) -
# distinctive on purpose so it never collides with a real SSID and can reliably be
# filtered out of "known networks" (Einstellungen shouldn't offer to "reconnect to"
# or "forget" the box's own recovery hotspot).
HOTSPOT_CONNECTION_NAME = "OwlBox-Hotspot"

# NetworkManager's own default subnet/gateway for a shared ("Hotspot") connection -
# used as a fallback if the actual address can't be read back from the interface.
HOTSPOT_FALLBACK_IP = "10.42.0.1"


def get_lan_ip() -> str:
    """Best-effort local IP address other devices on the LAN could reach this Pi at.

    Used for the login QR code on the kiosk display - request.host is useless there
    since the kiosk browser loads http://localhost:5000/, which means nothing to a
    phone scanning the code. Opening a UDP "connection" doesn't send any packets, it
    just asks the OS to pick the outbound interface/address for that route, which is
    exactly the address other devices on the same network would use to reach us.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _run(args: list[str], timeout: float = 10.0) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout


def get_status() -> dict:
    enabled = _run(["nmcli", "-t", "-f", "WIFI", "radio"]).strip().lower() == "enabled"

    connected_ssid = None
    signal = None
    # ACTIVE,SSID,SIGNAL - parsed from the right since SIGNAL is always the last,
    # numeric field, in case a pathological SSID itself contained a colon.
    for line in _run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"]).splitlines():
        active, _, rest = line.partition(":")
        ssid, _, signal_str = rest.rpartition(":")
        if active == "yes" and ssid:
            connected_ssid = ssid
            try:
                signal = int(signal_str)
            except ValueError:
                signal = None
            break

    ip_address = None
    hostname_output = _run(["hostname", "-I"]).split()
    if hostname_output:
        ip_address = hostname_output[0]

    return {"enabled": enabled, "connected_ssid": connected_ssid, "ip_address": ip_address, "signal": signal}


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


def list_known_networks() -> list[dict]:
    """Saved WiFi connection profiles - NetworkManager remembers the password once
    you've connected successfully, so the settings page can offer "reconnect
    without retyping the password" and "forget this network", independent of
    what's currently in scan range.
    """
    active_ssid = get_status()["connected_ssid"]
    networks = []
    for line in _run(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"]).splitlines():
        name, _, conn_type = line.partition(":")
        if conn_type != "802-11-wireless" or not name or name == HOTSPOT_CONNECTION_NAME:
            continue
        networks.append({"name": name, "active": name == active_ssid})
    return networks


def connect_known(name: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["sudo", "nmcli", "connection", "up", name], capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, "Verbunden."
    return False, (result.stderr or result.stdout or "Verbindung fehlgeschlagen.").strip()


def forget_network(name: str) -> None:
    try:
        subprocess.run(["sudo", "nmcli", "connection", "delete", name], check=False)
    except Exception:
        logger.exception("failed to delete wifi connection profile")


def set_wifi_enabled(enabled: bool) -> None:
    try:
        subprocess.run(["sudo", "nmcli", "radio", "wifi", "on" if enabled else "off"], check=False)
    except Exception:
        logger.exception("failed to toggle wifi radio")


def start_hotspot(ssid: str, password: str) -> bool:
    """Turns the Pi's own WiFi radio into an access point, so a laptop/phone can join it
    directly and reach the admin UI to fix the real WiFi settings - used as a recovery
    fallback (see engine.py) when no known network has been reachable for a while.
    """
    try:
        result = subprocess.run(
            [
                "sudo",
                "nmcli",
                "device",
                "wifi",
                "hotspot",
                "ifname",
                "wlan0",
                "con-name",
                HOTSPOT_CONNECTION_NAME,
                "ssid",
                ssid,
                "password",
                password,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        logger.exception("failed to start fallback hotspot")
        return False
    if result.returncode != 0:
        logger.warning("nmcli hotspot start failed: %s", (result.stderr or result.stdout).strip())
    return result.returncode == 0


def stop_hotspot() -> None:
    try:
        subprocess.run(
            ["sudo", "nmcli", "connection", "down", HOTSPOT_CONNECTION_NAME], capture_output=True, timeout=10, check=False
        )
    except Exception:
        logger.exception("failed to stop fallback hotspot")


def get_hotspot_ip() -> str:
    """Best-effort gateway address of the active hotspot, for the "open this URL" hint -
    falls back to NetworkManager's own default shared-connection subnet if it can't be
    read back (e.g. right after the hotspot just came up)."""
    output = _run(["nmcli", "-g", "IP4.ADDRESS", "device", "show", "wlan0"]).strip()
    address = output.splitlines()[0].split("/")[0] if output else ""
    return address or HOTSPOT_FALLBACK_IP


def try_reconnect_known_networks() -> bool:
    """Tries each remembered WiFi profile in turn (skipping our own hotspot profile) -
    used while the fallback hotspot is active, to periodically check whether a known
    network has come back into range without waiting for a user to intervene."""
    for net in list_known_networks():
        if net["active"]:
            continue
        try:
            result = subprocess.run(
                ["sudo", "nmcli", "connection", "up", net["name"]],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return True
    return False
