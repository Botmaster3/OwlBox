"""Thin SQLite helper: one connection per process, guarded by a lock for writes."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_write_lock = threading.Lock()
_connection: sqlite3.Connection | None = None


def init_db(database_path: Path) -> sqlite3.Connection:
    global _connection
    database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(database_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()
    _connection = conn
    return conn


def get_connection() -> sqlite3.Connection:
    if _connection is None:
        raise RuntimeError("Database not initialized; call init_db() first")
    return _connection


@contextmanager
def write_cursor():
    """Serializes writes; sqlite3 with one connection isn't safe for concurrent writers."""
    with _write_lock:
        conn = get_connection()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
