#!/usr/bin/env python3
"""Creates the one admin account without the browser-based Ersteinrichtung
wizard - used by scripts/autoinstall.sh so a from-empty-SD-card install can
finish completely unattended. Not meant to be run by hand during a normal,
guided install (open http://<pi-ip>:5000/admin instead, see README.md) -
this exists purely so autoinstall.sh has a non-interactive equivalent.

Idempotent like every other step in this project's install tooling: does
nothing (prints "SKIP") if an admin account already exists, rather than
overwriting it - autoinstall.sh can therefore be re-run safely.

Reads OWLBOX_ADMIN_USER/OWLBOX_ADMIN_PASSWORD from the environment (set by
autoinstall.sh after reading them from a boot-partition file, see there).
Missing username defaults to "eltern"; a missing/empty password is randomly
generated - either way the result is printed as "username=...\npassword=..."
so the caller can save it (autoinstall.sh writes it to
/root/owlbox-admin-credentials.txt, root-only).

Usage: sudo /opt/owlbox/.venv/bin/python3 /opt/owlbox/scripts/create_admin.py
"""
from __future__ import annotations

import os
import secrets
import string
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash  # noqa: E402

from owlbox import repository  # noqa: E402
from owlbox.config import load_config  # noqa: E402
from owlbox.db import init_db  # noqa: E402

DEFAULT_USERNAME = "eltern"
RANDOM_PASSWORD_LENGTH = 16


def random_password(length: int = RANDOM_PASSWORD_LENGTH) -> str:
    # Letters+digits only (no punctuation) - has to be easy to read off a
    # terminal/credentials file and re-type once, not a long-term secret
    # someone memorizes; still ~95 bits of entropy at this length.
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> int:
    config = load_config()
    init_db(config.database_path)

    if repository.get_admin_user() is not None:
        print("SKIP: Verwaltungs-Zugang existiert bereits, nichts geaendert.")
        return 0

    username = os.environ.get("OWLBOX_ADMIN_USER") or DEFAULT_USERNAME
    password = os.environ.get("OWLBOX_ADMIN_PASSWORD") or random_password()
    repository.create_admin_user(username, generate_password_hash(password))
    print(f"username={username}")
    print(f"password={password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
