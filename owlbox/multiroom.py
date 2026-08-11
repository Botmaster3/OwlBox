"""Mehrraum-Wiedergabe (multi-room audio): synced playback across several
OwlBoxen via Snapcast (https://github.com/badaix/snapcast) - the same
"lean on a proven, purpose-built external tool" approach as AirPlay/
shairport-sync (see docs/hardware.md and Engine.airplay_session_started).

Architecture (see docs/hardware.md's "Mehrraum-Wiedergabe" section for the
full write-up): the Hauptbox's mpv writes raw PCM into a named pipe instead
of straight to its ALSA device (see player.py - only when a role is set,
the default single-box path is untouched); snapserver on the Hauptbox reads
that pipe and streams it to every connected snapclient. Every box that
actually makes sound - the Hauptbox itself included, listening to its own
relayed stream - runs a local snapclient (owlbox-snapclient.service, a
custom unit wrapping the stock `snapclient` binary so it picks up which
host to connect to from a plain text file this module writes, no root
needed for that part - see systemd/owlbox-snapclient.service). Only
enabling/disabling/restarting the two systemd services needs the
passwordless-sudo rules `scripts/install.sh` sets up.

No manual "who is the master" wiring between boxes: every box with the
`multiroom` install stage set up constantly announces itself on the LAN via
mDNS (owlbox-mdns.service, a thin wrapper around `avahi-publish-service` -
reuses the same Avahi that already backs plain <hostname>.local, see
system_info.py/docs/hardware.md, nothing new to install there). One admin
action, on exactly one box, flips "Diese Box ist die Hauptbox" on
(Engine.set_multiroom_master_enabled); every OTHER box discovers who that
is on its own (discover_peers() + query_peer() below, both plain unauthenticated
GETs against /api/state - already public, same as the kiosk's own polling -
no shared secret or login between boxes needed) and applies the matching
Slave role by itself, via Engine._check_multiroom's periodic background
poll. Turn the switch off, or move it to a different box, and every
follower re-derives the new state the same way within one poll interval.

Nothing here has been exercised against real Snapcast/Avahi mDNS discovery
on real hardware or across multiple real devices - see the "Noch nicht an
echter Hardware verifiziert" note in docs/hardware.md. Every subprocess/
network call degrades to a safe fallback (empty list, None, or a returned
(False, message)) rather than raising, same discipline as
network.py/system_info.py.
"""
from __future__ import annotations

import json
import logging
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger("owlbox.multiroom")

ROLES = ("off", "master", "slave")

# Matches player.py's FIFO_PATH (see there) and the pipe source install.sh
# writes into /etc/snapserver.conf - all three must stay in sync.
FIFO_PATH = "/tmp/owlbox-multiroom.fifo"

# Plain text file holding the current snapclient target host - owned/written
# by the owlbox service user directly (no sudo needed for this part), read
# by owlbox-snapclient.service's ExecStart at every (re)start. "127.0.0.1"
# is what a Hauptbox writes here for itself - see set_role() below.
HOST_FILE_PATH = "/tmp/owlbox-multiroom-host.txt"

# mDNS service type every OwlBox with the `multiroom` stage installed
# announces itself under (see systemd/owlbox-mdns.service) and that
# discover_peers() below browses for.
MDNS_SERVICE_TYPE = "_owlbox._tcp"

_SNAPCLIENT_SERVICE = "owlbox-snapclient"
_SNAPSERVER_SERVICE = "snapserver"


def _systemctl(*args: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["sudo", "systemctl", *args], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, "ok"
    return False, (result.stderr or result.stdout or f"systemctl {' '.join(args)} fehlgeschlagen").strip()


def _write_host_file(host: str) -> tuple[bool, str]:
    try:
        Path(HOST_FILE_PATH).write_text(host.strip() + "\n")
    except OSError as exc:
        return False, str(exc)
    return True, "ok"


def set_role(role: str, master_host: Optional[str]) -> tuple[bool, str]:
    """Applies a Mehrraum role: "off" stops/disables both services, "master"
    starts snapserver plus a local snapclient pointed at itself (127.0.0.1 -
    the Hauptbox listens to its own relayed stream exactly like every other
    box, see module docstring), "slave" starts only a snapclient pointed at
    `master_host`. Returns (True, "ok") or (False, error_message). Called
    only by Engine._check_multiroom, and only when the desired role/host
    actually changed since the last check - every call here means a real
    handful of subprocess spawns, not something to do on every poll tick
    regardless of whether anything changed."""
    if role not in ROLES:
        return False, f"Unbekannte Rolle: {role}"

    if role == "off":
        ok1, msg1 = _systemctl("disable", "--now", _SNAPCLIENT_SERVICE)
        ok2, msg2 = _systemctl("disable", "--now", _SNAPSERVER_SERVICE)
        if ok1 and ok2:
            return True, "ok"
        return False, "; ".join(m for ok, m in ((ok1, msg1), (ok2, msg2)) if not ok)

    if role == "slave":
        if not master_host:
            return False, "Keine Hauptbox bekannt."
        ok, msg = _write_host_file(master_host)
        if not ok:
            return False, msg
        # A slave has no business also running its own snapserver.
        _systemctl("disable", "--now", _SNAPSERVER_SERVICE)
        ok, msg = _systemctl("enable", "--now", _SNAPCLIENT_SERVICE)
        if not ok:
            # Might already be running with a stale host - restart to pick
            # up the freshly-written host file either way.
            ok, msg = _systemctl("restart", _SNAPCLIENT_SERVICE)
        return ok, msg

    # role == "master"
    ok, msg = _write_host_file("127.0.0.1")
    if not ok:
        return False, msg
    ok1, msg1 = _systemctl("enable", "--now", _SNAPSERVER_SERVICE)
    ok2, msg2 = _systemctl("enable", "--now", _SNAPCLIENT_SERVICE)
    if not ok2:
        ok2, msg2 = _systemctl("restart", _SNAPCLIENT_SERVICE)
    if ok1 and ok2:
        return True, "ok"
    return False, "; ".join(m for ok, m in ((ok1, msg1), (ok2, msg2)) if not ok)


def discover_peers(timeout: float = 3.0) -> list[dict]:
    """Live mDNS scan (avahi-browse, needs avahi-utils - see the `multiroom`
    install stage) for other OwlBoxen currently announcing themselves on the
    LAN. Returns [{"name": ..., "host": ...}, ...], deduplicated by address,
    excluding this box's own announcement. Best-effort: no avahi-daemon
    running, avahi-utils not installed, or the scan just turning up nothing
    all look the same from here - an empty list, never an exception, since
    "no other boxes found (yet)" is an entirely ordinary, expected result."""
    try:
        result = subprocess.run(
            ["avahi-browse", "-r", "-t", "-p", MDNS_SERVICE_TYPE],
            capture_output=True,
            text=True,
            timeout=timeout + 2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []

    own_hostname = socket.gethostname()
    peers = []
    seen_hosts = set()
    # -p gives one machine-parsable line per event, semicolon-separated.
    # A resolved record starts with "=" and has (at minimum):
    # =;<iface>;<protocol>;<name>;<type>;<domain>;<hostname>;<address>;<port>;<txt>
    for line in result.stdout.splitlines():
        fields = line.split(";")
        if len(fields) < 8 or fields[0] != "=":
            continue
        name, address = fields[3], fields[7]
        if not address or address in seen_hosts or name == own_hostname:
            continue
        seen_hosts.add(address)
        peers.append({"name": name, "host": address})
    return peers


def query_peer(host: str, timeout: float = 1.5) -> Optional[dict]:
    """Single unauthenticated GET against a peer's own /api/state (already
    public - same endpoint the kiosk itself polls, no login/shared secret
    between boxes needed) - serves both the peer list's online/offline dot
    and Engine._check_multiroom's "who currently claims to be Hauptbox"
    question from the one HTTP round trip, rather than two separate ones.
    None means unreachable/malformed response ("don't know"), never raises -
    a peer being temporarily offline must never crash the poll loop."""
    try:
        with urllib.request.urlopen(f"http://{host}:5000/api/state", timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return {"master_enabled": bool(data.get("multiroom", {}).get("master_enabled"))}
