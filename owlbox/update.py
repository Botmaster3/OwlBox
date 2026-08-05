"""Self-update from the web UI, in two explicit steps so installing an update is
always the user's own decision rather than something a page load silently does:
  1. check_update() - read-only `git fetch` + compares HEAD against the upstream
     tracking branch, just reports whether anything is behind.
  2. run_update() - `git pull` in the repo, reinstall dependencies if
     requirements.txt changed, then restart the owlbox systemd service (not the
     whole Pi) so the new code takes effect. Requires passwordless sudo for
     `systemctl restart owlbox` - see docs/hardware.md.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .config import REPO_ROOT

logger = logging.getLogger("owlbox.update")

SERVICE_NAME = "owlbox"


def _run(args: list[str], cwd: Optional[Path] = None, timeout: float = 120) -> tuple[bool, str]:
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{' '.join(args)} fehlgeschlagen: {exc}"
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    return result.returncode == 0, output


def get_version_info() -> dict:
    """Best-effort: the running code's version number plus the date of the commit
    it was built from, so the info page can show not just "0.1.0" but since when
    that has been installed. Falls back to date=None if this isn't a git checkout
    (e.g. a tarball install) instead of failing the whole /system/info request."""
    from . import __version__

    ok, date_output = _run(
        ["git", "log", "-1", "--date=format:%d.%m.%Y", "--format=%cd"], cwd=REPO_ROOT
    )
    return {"version": __version__, "date": date_output.strip() if ok and date_output.strip() else None}


def check_update() -> dict:
    """Read-only: fetches from the remote and reports whether new commits are
    available upstream, without touching the working tree, installing anything,
    or restarting the service. Lets the UI show "update available" and leave the
    actual install (run_update()) to an explicit follow-up action."""
    ok, fetch_output = _run(["git", "fetch"], cwd=REPO_ROOT)
    if not ok:
        logger.warning("update check: git fetch failed: %s", fetch_output)
        return {"ok": False, "step": "git fetch", "output": fetch_output}

    ok, count_output = _run(["git", "rev-list", "--count", "HEAD..@{u}"], cwd=REPO_ROOT)
    if not ok:
        logger.warning("update check: git rev-list failed: %s", count_output)
        return {"ok": False, "step": "git rev-list", "output": count_output}

    try:
        behind = int(count_output.strip() or "0")
    except ValueError:
        behind = 0

    return {"ok": True, "update_available": behind > 0, "commits_behind": behind}


def run_update() -> dict:
    """Best-effort at every step - reports what happened rather than raising,
    since this is triggered straight from the web UI."""
    ok, pull_output = _run(["git", "pull", "--ff-only"], cwd=REPO_ROOT)
    if not ok:
        logger.warning("update: git pull failed: %s", pull_output)
        return {"ok": False, "step": "git pull", "output": pull_output}

    already_current = "Already up to date" in pull_output or "bereits aktuell" in pull_output
    if not already_current:
        pip = Path(sys.executable).parent / "pip"
        pip_ok, pip_output = _run(
            [str(pip), "install", "-q", "-r", str(REPO_ROOT / "requirements.txt")], timeout=300
        )
        if not pip_ok:
            logger.warning("update: pip install failed: %s", pip_output)
            return {"ok": False, "step": "pip install", "output": f"{pull_output}\n{pip_output}"}

    if already_current:
        return {"ok": True, "output": pull_output, "restarted": False}

    restart_ok, restart_output = _run(["sudo", "systemctl", "restart", "--no-block", SERVICE_NAME])
    if not restart_ok:
        logger.warning("update: service restart failed: %s", restart_output)
        return {"ok": False, "step": "restart", "output": f"{pull_output}\n{restart_output}"}

    logger.info("update: pulled new code, restart triggered")
    return {"ok": True, "output": pull_output, "restarted": True}
