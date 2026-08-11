"""owlbox.multiroom - the OS-integration layer behind Mehrraum-Wiedergabe
(Snapcast). Every subprocess/network call is mocked here, same discipline as
tests/test_network.py/test_update.py - nothing in this module has been
exercised against real Snapcast or multiple real devices (see
docs/hardware.md's "Mehrraum-Wiedergabe" note)."""
import subprocess
import urllib.error
from unittest.mock import patch

import pytest

from owlbox import multiroom


def _fake_run(returncode=0, stderr=""):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout="", stderr=stderr)
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


def test_check_peer_reachable_true_on_200(monkeypatch):
    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("owlbox.multiroom.urllib.request.urlopen", lambda *a, **k: FakeResponse())
    assert multiroom.check_peer_reachable("owlbox-wohnzimmer.local") is True


def test_check_peer_reachable_false_on_connection_error(monkeypatch):
    def raise_error(*a, **k):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr("owlbox.multiroom.urllib.request.urlopen", raise_error)
    assert multiroom.check_peer_reachable("offline-box.local") is False


def test_check_peer_reachable_false_on_bad_host(monkeypatch):
    # A malformed host (e.g. empty string) raises ValueError inside urllib,
    # not URLError - must still degrade to False, never raise up to the
    # /api/peers route.
    def raise_error(*a, **k):
        raise ValueError("bad host")

    monkeypatch.setattr("owlbox.multiroom.urllib.request.urlopen", raise_error)
    assert multiroom.check_peer_reachable("") is False
