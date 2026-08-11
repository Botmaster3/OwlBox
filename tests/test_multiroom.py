"""owlbox.multiroom - the OS-integration layer behind Mehrraum-Wiedergabe
(Snapcast + mDNS discovery). Every subprocess/network call is mocked here,
same discipline as tests/test_network.py/test_update.py - nothing in this
module has been exercised against real Snapcast or real Avahi mDNS
discovery across multiple real devices (see docs/hardware.md's
"Mehrraum-Wiedergabe" note)."""
import json
import subprocess
import urllib.error
from unittest.mock import patch

import pytest

from owlbox import multiroom


def _fake_run(returncode=0, stdout="", stderr=""):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)
    return run


def test_set_role_rejects_unknown_role():
    ok, message = multiroom.set_role("banana", None)
    assert ok is False
    assert "Unbekannte Rolle" in message


def test_set_role_off_disables_both_services(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda args, **kwargs: (calls.append(args), subprocess.CompletedProcess(args, 0))[1],
    )
    ok, message = multiroom.set_role("off", None)
    assert ok is True
    assert calls == [
        ["sudo", "systemctl", "disable", "--now", "owlbox-snapclient"],
        ["sudo", "systemctl", "disable", "--now", "snapserver"],
    ]


def test_set_role_slave_without_master_host_fails():
    ok, message = multiroom.set_role("slave", None)
    assert ok is False
    assert "Hauptbox" in message


def test_set_role_slave_writes_host_file_and_enables_snapclient(tmp_path, monkeypatch):
    host_file = tmp_path / "host.txt"
    monkeypatch.setattr(multiroom, "HOST_FILE_PATH", str(host_file))
    calls = []
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda args, **kwargs: (calls.append(args), subprocess.CompletedProcess(args, 0))[1],
    )
    ok, message = multiroom.set_role("slave", "owlbox-wohnzimmer.local")
    assert ok is True
    assert host_file.read_text() == "owlbox-wohnzimmer.local\n"
    assert ["sudo", "systemctl", "disable", "--now", "snapserver"] in calls
    assert ["sudo", "systemctl", "enable", "--now", "owlbox-snapclient"] in calls


def test_set_role_master_writes_loopback_host_and_enables_both(tmp_path, monkeypatch):
    host_file = tmp_path / "host.txt"
    monkeypatch.setattr(multiroom, "HOST_FILE_PATH", str(host_file))
    calls = []
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda args, **kwargs: (calls.append(args), subprocess.CompletedProcess(args, 0))[1],
    )
    ok, message = multiroom.set_role("master", "irrelevant - master always uses itself")
    assert ok is True
    assert host_file.read_text() == "127.0.0.1\n"
    assert ["sudo", "systemctl", "enable", "--now", "snapserver"] in calls
    assert ["sudo", "systemctl", "enable", "--now", "owlbox-snapclient"] in calls


def test_set_role_surfaces_systemctl_failure(tmp_path, monkeypatch):
    host_file = tmp_path / "host.txt"
    monkeypatch.setattr(multiroom, "HOST_FILE_PATH", str(host_file))
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 1, stderr="Unit not found"),
    )
    ok, message = multiroom.set_role("master", None)
    assert ok is False
    assert "Unit not found" in message


def test_set_role_surfaces_missing_systemctl_binary(tmp_path, monkeypatch):
    host_file = tmp_path / "host.txt"
    monkeypatch.setattr(multiroom, "HOST_FILE_PATH", str(host_file))
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(OSError("sudo not found")),
    )
    ok, message = multiroom.set_role("master", None)
    assert ok is False
    assert "sudo not found" in message


# -- discover_peers (mDNS via avahi-browse) ----------------------------------

_AVAHI_BROWSE_SAMPLE = (
    "+;eth0;IPv4;owlbox-wohnzimmer;_owlbox._tcp;local\n"
    "=;eth0;IPv4;owlbox-wohnzimmer;_owlbox._tcp;local;owlbox-wohnzimmer.local;192.168.1.42;5000;\n"
    "=;eth0;IPv4;owlbox-kueche;_owlbox._tcp;local;owlbox-kueche.local;192.168.1.43;5000;\n"
)


def test_discover_peers_parses_avahi_browse_output(monkeypatch):
    monkeypatch.setattr("owlbox.multiroom.socket.gethostname", lambda: "owlbox-kinderzimmer")
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=_AVAHI_BROWSE_SAMPLE, stderr=""),
    )
    peers = multiroom.discover_peers()
    assert peers == [
        {"name": "owlbox-wohnzimmer", "host": "192.168.1.42"},
        {"name": "owlbox-kueche", "host": "192.168.1.43"},
    ]


def test_discover_peers_excludes_self(monkeypatch):
    monkeypatch.setattr("owlbox.multiroom.socket.gethostname", lambda: "owlbox-wohnzimmer")
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=_AVAHI_BROWSE_SAMPLE, stderr=""),
    )
    peers = multiroom.discover_peers()
    assert [p["name"] for p in peers] == ["owlbox-kueche"]


def test_discover_peers_returns_empty_list_when_avahi_browse_missing(monkeypatch):
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda *a, **k: (_ for _ in ()).throw(OSError("avahi-browse not found")),
    )
    assert multiroom.discover_peers() == []


def test_discover_peers_returns_empty_list_on_nonzero_exit(monkeypatch):
    # e.g. avahi-daemon not running - avahi-browse exits non-zero rather
    # than raising.
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout="", stderr="Failed to connect to daemon"),
    )
    assert multiroom.discover_peers() == []


def test_discover_peers_ignores_malformed_lines(monkeypatch):
    monkeypatch.setattr("owlbox.multiroom.socket.gethostname", lambda: "owlbox-x")
    monkeypatch.setattr(
        "owlbox.multiroom.subprocess.run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="garbage;too;few;fields\n", stderr=""),
    )
    assert multiroom.discover_peers() == []


# -- query_peer ---------------------------------------------------------------


def test_query_peer_returns_master_status_on_success(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"multiroom": {"master_enabled": True, "master_since": 1000.5}}).encode()

    monkeypatch.setattr("owlbox.multiroom.urllib.request.urlopen", lambda *a, **k: FakeResponse())
    assert multiroom.query_peer("owlbox-wohnzimmer.local") == {"master_enabled": True, "master_since": 1000.5}


def test_query_peer_false_when_peer_is_not_master(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"multiroom": {"master_enabled": False, "master_since": None}}).encode()

    monkeypatch.setattr("owlbox.multiroom.urllib.request.urlopen", lambda *a, **k: FakeResponse())
    assert multiroom.query_peer("owlbox-kueche.local") == {"master_enabled": False, "master_since": None}


def test_query_peer_none_on_connection_error(monkeypatch):
    def raise_error(*a, **k):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr("owlbox.multiroom.urllib.request.urlopen", raise_error)
    assert multiroom.query_peer("offline-box.local") is None


def test_query_peer_none_on_malformed_response(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"not json"

    monkeypatch.setattr("owlbox.multiroom.urllib.request.urlopen", lambda *a, **k: FakeResponse())
    assert multiroom.query_peer("weird-box.local") is None
