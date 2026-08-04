"""Self-update from the web UI: `git pull` in the repo, reinstall dependencies
if requirements.txt changed, then restart the owlbox systemd service (not the
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
