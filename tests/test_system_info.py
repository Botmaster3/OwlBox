from pathlib import Path

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
