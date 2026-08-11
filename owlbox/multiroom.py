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

Nothing here has been exercised against real Snapcast on real hardware or
across multiple real devices - see the "Noch nicht an echter Hardware
verifiziert" note in docs/hardware.md. Every subprocess call degrades to a
returned (False, message) rather than raising, same discipline as
network.py/system_info.py, so a role change that can't actually apply
(e.g. the `multiroom` install stage was never run) is reported back to
whoever clicked "Speichern" instead of silently doing nothing.
"""
from __future__ import annotations

import logging
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
    `master_host`. Returns (True, "ok") or (False, error_message) - the
    caller (Engine.set_multiroom) is responsible for only persisting the new
    role to the DB once this actually succeeds."""
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
            return False, "Keine Hauptbox ausgewählt."
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


def check_peer_reachable(host: str, timeout: float = 1.5) -> bool:
    """Best-effort "is this other OwlBox currently answering" check for the
    peer directory's status dot - a plain GET against its own /api/state,
    which (like this box's) needs no login. Any failure (offline, wrong
    host, firewalled, ...) just means "not reachable" - never raises. Uses
    urllib rather than adding a new "requests" dependency for one lightweight
    check - this project has stayed stdlib-only for HTTP so far."""
    try:
        with urllib.request.urlopen(f"http://{host}:5000/api/state", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False
