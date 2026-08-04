import subprocess
from types import SimpleNamespace

from owlbox import update


def _fake_run(responses):
    """responses: dict mapping the first arg of the command to (returncode, output)."""

    def run(args, cwd=None, capture_output=True, text=True, timeout=None, check=False):
        key = args[0]
        returncode, output = responses.get(key, (0, ""))
        return SimpleNamespace(returncode=returncode, stdout=output, stderr="")

    return run


def test_run_update_reports_git_pull_failure(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run({"git": (1, "conflict")}))
    result = update.run_update()
    assert result == {"ok": False, "step": "git pull", "output": "conflict"}


def test_run_update_skips_install_and_restart_when_already_current(monkeypatch):
    calls = []

    def run(args, cwd=None, capture_output=True, text=True, timeout=None, check=False):
        calls.append(args[0])
        if args[0] == "git":
            return SimpleNamespace(returncode=0, stdout="Already up to date.\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(subprocess, "run", run)
    result = update.run_update()
    assert result == {"ok": True, "output": "Already up to date.", "restarted": False}
    assert calls == ["git"]  # pip/sudo never invoked


def test_run_update_installs_deps_and_restarts_on_new_commits(monkeypatch):
    calls = []

    def run(args, cwd=None, capture_output=True, text=True, timeout=None, check=False):
        calls.append(args[0])
        if args[0] == "git":
            return SimpleNamespace(returncode=0, stdout="Updating abc..def\n", stderr="")
        if str(args[0]).endswith("pip"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[0] == "sudo":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(subprocess, "run", run)
    result = update.run_update()
    assert result["ok"] is True
    assert result["restarted"] is True
    assert calls[0] == "git"
    assert calls[-1] == "sudo"


def test_run_update_reports_pip_install_failure(monkeypatch):
    def run(args, cwd=None, capture_output=True, text=True, timeout=None, check=False):
        if args[0] == "git":
            return SimpleNamespace(returncode=0, stdout="Updating abc..def\n", stderr="")
        if str(args[0]).endswith("pip"):
            return SimpleNamespace(returncode=1, stdout="", stderr="no matching distribution")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(subprocess, "run", run)
    result = update.run_update()
    assert result["ok"] is False
    assert result["step"] == "pip install"
    assert "no matching distribution" in result["output"]


def test_run_update_reports_restart_failure(monkeypatch):
    def run(args, cwd=None, capture_output=True, text=True, timeout=None, check=False):
        if args[0] == "git":
            return SimpleNamespace(returncode=0, stdout="Updating abc..def\n", stderr="")
        if str(args[0]).endswith("pip"):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if args[0] == "sudo":
            return SimpleNamespace(returncode=1, stdout="", stderr="permission denied")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(subprocess, "run", run)
    result = update.run_update()
    assert result["ok"] is False
    assert result["step"] == "restart"
    assert "permission denied" in result["output"]
