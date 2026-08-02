"""CRUD access to stories/tracks/playback_state/scan_log, on top of db.py."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .db import get_connection, write_cursor


@dataclass
class Track:
    id: int
    story_id: int
    position: int
    filename: str
    title: Optional[str]
    duration: Optional[float]


@dataclass
class Story:
    id: int
    uid: Optional[str]
    title: str
    cover_path: Optional[str]
    shuffle: bool
    repeat: bool
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Story":
        return cls(
            id=row["id"],
            uid=row["uid"],
            title=row["title"],
            cover_path=row["cover_path"],
            shuffle=bool(row["shuffle"]),
            repeat=bool(row["repeat"]),
            created_at=row["created_at"],
        )


def create_story(title: str, uid: Optional[str] = None, cover_path: Optional[str] = None) -> Story:
    with write_cursor() as cur:
        cur.execute(
            "INSERT INTO stories (uid, title, cover_path) VALUES (?, ?, ?)",
            (uid, title, cover_path),
        )
        story_id = cur.lastrowid
    return get_story(story_id)


def add_track(story_id: int, position: int, filename: str, title: Optional[str], duration: Optional[float]) -> Track:
    with write_cursor() as cur:
        cur.execute(
            "INSERT INTO tracks (story_id, position, filename, title, duration) VALUES (?, ?, ?, ?, ?)",
            (story_id, position, filename, title, duration),
        )
        track_id = cur.lastrowid
    row = get_connection().execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    return Track(**dict(row))


def get_story(story_id: int) -> Optional[Story]:
    row = get_connection().execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
    return Story.from_row(row) if row else None


def get_story_by_uid(uid: str) -> Optional[Story]:
    row = get_connection().execute("SELECT * FROM stories WHERE uid = ?", (uid,)).fetchone()
    return Story.from_row(row) if row else None


def list_stories() -> list[Story]:
    rows = get_connection().execute("SELECT * FROM stories ORDER BY created_at DESC").fetchall()
    return [Story.from_row(r) for r in rows]


def get_library_stats() -> dict:
    conn = get_connection()
    story_count = conn.execute("SELECT COUNT(*) AS n FROM stories").fetchone()["n"]
    track_count = conn.execute("SELECT COUNT(*) AS n FROM tracks").fetchone()["n"]
    assigned_count = conn.execute("SELECT COUNT(*) AS n FROM stories WHERE uid IS NOT NULL").fetchone()["n"]
    return {"story_count": story_count, "track_count": track_count, "assigned_count": assigned_count}


def get_tracks(story_id: int) -> list[Track]:
    rows = get_connection().execute(
        "SELECT * FROM tracks WHERE story_id = ? ORDER BY position ASC", (story_id,)
    ).fetchall()
    return [Track(**dict(r)) for r in rows]


def delete_story(story_id: int) -> None:
    with write_cursor() as cur:
        cur.execute("DELETE FROM stories WHERE id = ?", (story_id,))


def delete_track(track_id: int) -> None:
    with write_cursor() as cur:
        cur.execute("DELETE FROM tracks WHERE id = ?", (track_id,))


def reorder_tracks(story_id: int, track_ids: list[int]) -> None:
    with write_cursor() as cur:
        for position, track_id in enumerate(track_ids):
            cur.execute(
                "UPDATE tracks SET position = ? WHERE id = ? AND story_id = ?",
                (position, track_id, story_id),
            )


def next_track_position(story_id: int) -> int:
    row = get_connection().execute(
        "SELECT COALESCE(MAX(position), -1) + 1 AS pos FROM tracks WHERE story_id = ?", (story_id,)
    ).fetchone()
    return row["pos"]


def assign_uid(story_id: int, uid: str) -> None:
    with write_cursor() as cur:
        cur.execute("UPDATE stories SET uid = NULL WHERE uid = ?", (uid,))
        cur.execute("UPDATE stories SET uid = ? WHERE id = ?", (uid, story_id))
        cur.execute("DELETE FROM function_tags WHERE uid = ?", (uid,))


def remove_story_uid(story_id: int) -> None:
    with write_cursor() as cur:
        cur.execute("UPDATE stories SET uid = NULL WHERE id = ?", (story_id,))


def set_cover_path(story_id: int, cover_path: str) -> None:
    with write_cursor() as cur:
        cur.execute("UPDATE stories SET cover_path = ? WHERE id = ?", (cover_path, story_id))


def update_story_flags(story_id: int, shuffle: Optional[bool] = None, repeat: Optional[bool] = None) -> None:
    story = get_story(story_id)
    if story is None:
        return
    shuffle = story.shuffle if shuffle is None else shuffle
    repeat = story.repeat if repeat is None else repeat
    with write_cursor() as cur:
        cur.execute(
            "UPDATE stories SET shuffle = ?, repeat = ? WHERE id = ?",
            (int(shuffle), int(repeat), story_id),
        )


def save_playback_state(uid: str, track_position: int, seek_seconds: float) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO playback_state (uid, track_position, seek_seconds, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(uid) DO UPDATE SET
                track_position = excluded.track_position,
                seek_seconds = excluded.seek_seconds,
                updated_at = excluded.updated_at
            """,
            (uid, track_position, seek_seconds),
        )


def get_playback_state(uid: str) -> tuple[int, float]:
    row = get_connection().execute(
        "SELECT track_position, seek_seconds FROM playback_state WHERE uid = ?", (uid,)
    ).fetchone()
    if row is None:
        return 0, 0.0
    return row["track_position"], row["seek_seconds"]


def log_scan(uid: str) -> None:
    with write_cursor() as cur:
        cur.execute("INSERT INTO scan_log (uid) VALUES (?)", (uid,))
        cur.execute(
            """
            DELETE FROM scan_log WHERE id NOT IN (
                SELECT id FROM scan_log ORDER BY id DESC LIMIT 20
            )
            """
        )


def get_last_scan() -> Optional[dict]:
    row = get_connection().execute("SELECT id, uid FROM scan_log ORDER BY id DESC LIMIT 1").fetchone()
    return {"id": row["id"], "uid": row["uid"]} if row else None


def get_last_unknown_scan() -> Optional[str]:
    row = get_connection().execute(
        """
        SELECT uid FROM scan_log
        WHERE uid NOT IN (SELECT uid FROM stories WHERE uid IS NOT NULL)
        ORDER BY id DESC LIMIT 1
        """
    ).fetchone()
    return row["uid"] if row else None


@dataclass
class AdminUser:
    id: int
    username: str
    password_hash: str
    rfid_uid: Optional[str]
    created_at: str


def get_admin_user() -> Optional[AdminUser]:
    """There's only ever one admin account - a single row in this table."""
    row = get_connection().execute("SELECT * FROM admin_user ORDER BY id LIMIT 1").fetchone()
    return AdminUser(**dict(row)) if row else None


def create_admin_user(username: str, password_hash: str) -> AdminUser:
    with write_cursor() as cur:
        cur.execute(
            "INSERT INTO admin_user (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
    return get_admin_user()


def update_admin_user(username: str, password_hash: str) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE admin_user SET username = ?, password_hash = ? WHERE id = (SELECT id FROM admin_user ORDER BY id LIMIT 1)",
            (username, password_hash),
        )


def set_admin_rfid_uid(uid: Optional[str]) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE admin_user SET rfid_uid = ? WHERE id = (SELECT id FROM admin_user ORDER BY id LIMIT 1)",
            (uid,),
        )


# -- function tags (control cards: play/pause/next/previous/volume/wifi/power) --


def list_function_tags() -> list[dict]:
    rows = get_connection().execute("SELECT uid, action FROM function_tags ORDER BY created_at DESC").fetchall()
    return [{"uid": r["uid"], "action": r["action"]} for r in rows]


def get_function_tag(uid: str) -> Optional[str]:
    row = get_connection().execute("SELECT action FROM function_tags WHERE uid = ?", (uid,)).fetchone()
    return row["action"] if row else None


def set_function_tag(uid: str, action: str) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO function_tags (uid, action) VALUES (?, ?)
            ON CONFLICT(uid) DO UPDATE SET action = excluded.action
            """,
            (uid, action),
        )
        cur.execute("UPDATE stories SET uid = NULL WHERE uid = ?", (uid,))


def delete_function_tag(uid: str) -> None:
    with write_cursor() as cur:
        cur.execute("DELETE FROM function_tags WHERE uid = ?", (uid,))


# -- generic runtime settings ------------------------------------------------


def get_setting(key: str) -> Optional[str]:
    row = get_connection().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def get_int_setting(key: str, default: int) -> int:
    value = get_setting(key)
    return int(value) if value is not None else default


def set_setting(key: str, value: str) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, str(value)),
        )
