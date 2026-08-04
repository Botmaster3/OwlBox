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
    _migrate(conn)
    conn.commit()
    _connection = conn
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """`CREATE TABLE IF NOT EXISTS` in schema.sql only takes effect for brand-new
    databases - existing ones need columns added after the fact when the schema
    for an existing table evolves (new tables need no such step)."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(stories)")}
    if "stream_url" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN stream_url TEXT")
    if "play_count" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN play_count INTEGER NOT NULL DEFAULT 0")
    if "total_seconds" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN total_seconds REAL NOT NULL DEFAULT 0")
    if "last_played_at" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN last_played_at TEXT")


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


def backup_to(dest_path: str) -> None:
    """Writes a consistent snapshot of the live database to dest_path, via
    sqlite's own online backup API rather than copying the .db file directly -
    journal_mode=WAL means a raw file copy could miss recent writes still
    sitting in the -wal sidecar file. Held under the same write lock as
    write_cursor() so it can't interleave with an in-progress write."""
    with _write_lock:
        conn = get_connection()
        dest = sqlite3.connect(dest_path)
        try:
            with dest:
                conn.backup(dest)
        finally:
            dest.close()
