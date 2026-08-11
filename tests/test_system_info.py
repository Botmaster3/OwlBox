import socket
import subprocess
from pathlib import Path
from unittest.mock import patch

from owlbox import system_info


def test_disk_usage_reports_real_numbers(tmp_path):
    usage = system_info.get_disk_usage(tmp_path)
    assert usage["total_bytes"] > 0
    assert usage["free_bytes"] >= 0
    assert usage["used_bytes"] >= 0


def test_memory_info_does_not_raise():
    # Present on Linux (incl. this sandbox); just check it doesn't blow up and,
    # when available, reports a sane positive total.
    info = system_info.get_memory_info()
    if info is not None:
        assert info["total_bytes"] > 0


def test_hardware_and_cpu_temp_degrade_gracefully_off_pi():
    # No /proc/device-tree or thermal_zone0 outside a real Raspberry Pi - must
    # return None instead of raising.
    assert system_info.get_cpu_temperature_celsius() is None or isinstance(
        system_info.get_cpu_temperature_celsius(), float
    )
    model = system_info.get_hardware_model()
    assert model is None or isinstance(model, str)


def test_uptime_is_positive_number_or_none():
    uptime = system_info.get_uptime_seconds()
    assert uptime is None or uptime > 0


# -- hostname -----------------------------------------------------------


def test_get_hostname_matches_socket():
    assert system_info.get_hostname() == socket.gethostname()


def test_normalize_hostname_turns_free_text_into_a_valid_label():
    # A parent naming a box after its room shouldn't need to know DNS syntax.
    assert system_info.normalize_hostname("Kinderzimmer!") == "kinderzimmer"
    assert system_info.normalize_hostname("OwlBox Wohnzimmer") == "owlbox-wohnzimmer"
    assert system_info.normalize_hostname("  spaces   everywhere  ") == "spaces-everywhere"
    assert system_info.normalize_hostname("--already--dashed--") == "already-dashed"
    assert system_info.normalize_hostname("Ünïcode Ä Ö Ü") == "ncode"


def test_normalize_hostname_truncates_to_63_chars():
    assert len(system_info.normalize_hostname("a" * 100)) == 63


def test_normalize_hostname_of_only_junk_is_empty():
    assert system_info.normalize_hostname("!!!") == ""
    assert system_info.normalize_hostname("   ") == ""


def _fake_run(returncode=0, stderr=""):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout="", stderr=stderr)
    return run


def test_set_hostname_rejects_empty_normalized_name():
    ok, message = system_info.set_hostname("!!!")
    assert ok is False
    assert "Ungültiger Name" in message


def test_set_hostname_success_reports_normalized_name():
    with patch("subprocess.run", side_effect=_fake_run(returncode=0)):
        ok, result = system_info.set_hostname("Kinderzimmer!")
    assert ok is True
    assert result == "kinderzimmer"


def test_set_hostname_failure_surfaces_stderr():
    with patch("subprocess.run", side_effect=_fake_run(returncode=1, stderr="Access denied")):
        ok, result = system_info.set_hostname("kinderzimmer")
    assert ok is False
    assert result == "Access denied"


def test_set_hostname_missing_binary_surfaces_error():
    with patch("subprocess.run", side_effect=OSError("hostnamectl not found")):
        ok, result = system_info.set_hostname("kinderzimmer")
    assert ok is False
    assert "hostnamectl not found" in result
