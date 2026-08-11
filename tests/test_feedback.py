"""owlbox.feedback.play_chime() itself is only ever monkeypatched away in
tests/test_engine.py (the engine tests care about *when* a chime is
triggered, not whether aplay actually produced sound) - these tests cover
the module's own behavior instead: still a no-op towards the caller on
failure (a broken chime must never crash/interrupt playback), but now
loud enough in the logs to actually diagnose a silent "pressed Test, heard
nothing" report instead of vanishing at DEBUG level below the app's
default INFO threshold (see main.py)."""
import logging
import subprocess
from unittest.mock import patch

from owlbox import feedback


def _fake_run(returncode=0, stderr=b""):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout=b"", stderr=stderr)
    return run


def test_play_chime_unknown_name_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="owlbox.feedback"):
        feedback.play_chime("does-not-exist", "hw:0,0")
    assert "no known sound file mapped" in caplog.text


def test_play_chime_success_is_quiet(caplog):
    with caplog.at_level(logging.WARNING, logger="owlbox.feedback"):
        with patch("subprocess.run", side_effect=_fake_run(returncode=0)):
            feedback.play_chime("known", "hw:0,0")
    assert caplog.text == ""


def test_play_chime_nonzero_exit_logs_warning_with_stderr(caplog):
    with caplog.at_level(logging.WARNING, logger="owlbox.feedback"):
        with patch("subprocess.run", side_effect=_fake_run(returncode=1, stderr=b"audio open error: Device or resource busy")):
            feedback.play_chime("known", "hw:0,0")
    assert "exit 1" in caplog.text
    assert "Device or resource busy" in caplog.text


def test_play_chime_missing_aplay_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="owlbox.feedback"):
        with patch("subprocess.run", side_effect=OSError("aplay not found")):
            feedback.play_chime("known", "hw:0,0")
    assert "playback unavailable" in caplog.text


def test_play_chime_timeout_logs_warning(caplog):
    with caplog.at_level(logging.WARNING, logger="owlbox.feedback"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="aplay", timeout=3)):
            feedback.play_chime("known", "hw:0,0")
    assert "playback unavailable" in caplog.text
