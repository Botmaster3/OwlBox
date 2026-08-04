"""CRUD access to stories/tracks/playback_state/scan_log, on top of db.py."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .db import get_connection, write_cursor

# 'off' plays through once and stops; 'folder' loops the whole story from
# the first track once the last one ends; 'track' repeats whichever single
# track is currently playing instead of advancing. See Engine._apply_repeat
# and Player.set_repeat_mode for where this actually takes effect.
REPEAT_MODES = ("off", "track", "folder")


@dataclass
class Track:
    id: int
    story_id: int
    position: int
    filename: str
    title: Optional[str]
    duration: Optional[float]
    # Set only for a track hard-linked into a playlist story from an
    # existing one (see create_story_from_tracks in web/api.py) - points at
    # the original track. None for every normally-uploaded track.
    source_track_id: Optional[int] = None


@dataclass
class Story:
    id: int
    uid: Optional[str]
    title: str
    cover_path: Optional[str]
    stream_url: Optional[str]
    shuffle: bool
    repeat: str
    play_count: int
    total_seconds: float
    last_played_at: Optional[str]
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Story":
        return cls(
            id=row["id"],
            uid=row["uid"],
            title=row["title"],
            cover_path=row["cover_path"],
            stream_url=row["stream_url"],
            shuffle=bool(row["shuffle"]),
            repeat=row["repeat"] if row["repeat"] in REPEAT_MODES else "off",
            play_count=row["play_count"],
            total_seconds=row["total_seconds"],
            last_played_at=row["last_played_at"],
            created_at=row["created_at"],
        )


def create_story(
    title: str, uid: Optional[str] = None, cover_path: Optional[str] = None, stream_url: Optional[str] = None
) -> Story:
    with write_cursor() as cur:
        cur.execute(
            "INSERT INTO stories (uid, title, cover_path, stream_url) VALUES (?, ?, ?, ?)",
            (uid, title, cover_path, stream_url),
        )
        story_id = cur.lastrowid
    return get_story(story_id)


def add_track(
    story_id: int,
    position: int,
    filename: str,
    title: Optional[str],
    duration: Optional[float],
    source_track_id: Optional[int] = None,
) -> Track:
    with write_cursor() as cur:
        cur.execute(
            "INSERT INTO tracks (story_id, position, filename, title, duration, source_track_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (story_id, position, filename, title, duration, source_track_id),
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


# -- Hörstatistik (play count / listening time per story) -------------------


def increment_play_count(story_id: int) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE stories SET play_count = play_count + 1, last_played_at = datetime('now') WHERE id = ?",
            (story_id,),
        )
        _bump_daily_listening(cur, story_id, seconds=0, plays=1)


def add_listening_seconds(story_id: int, seconds: float) -> None:
    if seconds <= 0:
        return
    with write_cursor() as cur:
        cur.execute("UPDATE stories SET total_seconds = total_seconds + ? WHERE id = ?", (seconds, story_id))
        _bump_daily_listening(cur, story_id, seconds=seconds, plays=0)


def _bump_daily_listening(cur, story_id: int, seconds: float, plays: int) -> None:
    """Upserts today's (UTC) row in daily_listening - the per-day breakdown
    behind the Info page's Wochenrückblick. Called from within the same
    write_cursor transaction as the all-time total it accompanies."""
    cur.execute(
        """
        INSERT INTO daily_listening (date, story_id, seconds, plays)
        VALUES (date('now'), ?, ?, ?)
        ON CONFLICT(date, story_id) DO UPDATE SET
            seconds = seconds + excluded.seconds,
            plays = plays + excluded.plays
        """,
        (story_id, seconds, plays),
    )


def get_listening_stats() -> dict:
    conn = get_connection()
    totals = conn.execute(
        "SELECT COALESCE(SUM(play_count), 0) AS plays, COALESCE(SUM(total_seconds), 0) AS seconds FROM stories"
    ).fetchone()
    top_rows = conn.execute(
        """
        SELECT id, title, stream_url, play_count, total_seconds, last_played_at
        FROM stories
        WHERE play_count > 0
        ORDER BY total_seconds DESC
        LIMIT 5
        """
    ).fetchall()
    return {
        "total_plays": totals["plays"],
        "total_seconds": totals["seconds"],
        "top_stories": [
            {
                "id": r["id"],
                "title": r["title"],
                "is_stream": bool(r["stream_url"]),
                "play_count": r["play_count"],
                "total_seconds": r["total_seconds"],
                "last_played_at": r["last_played_at"],
            }
            for r in top_rows
        ],
    }


def get_weekly_review(days: int = 7) -> dict:
    """Listening totals over the last `days` days (UTC calendar days, today
    included) plus the top 3 stories in that window - the Info page's
    Wochenrückblick. Independent of the all-time totals in get_listening_stats."""
    conn = get_connection()
    cutoff = f"-{days - 1} days"
    totals = conn.execute(
        "SELECT COALESCE(SUM(seconds), 0) AS seconds, COALESCE(SUM(plays), 0) AS plays "
        "FROM daily_listening WHERE date >= date('now', ?)",
        (cutoff,),
    ).fetchone()
    top_rows = conn.execute(
        """
        SELECT s.id, s.title, s.stream_url, SUM(d.seconds) AS seconds, SUM(d.plays) AS plays
        FROM daily_listening d
        JOIN stories s ON s.id = d.story_id
        WHERE d.date >= date('now', ?)
        GROUP BY d.story_id
        ORDER BY seconds DESC
        LIMIT 3
        """,
        (cutoff,),
    ).fetchall()
    return {
        "days": days,
        "total_seconds": totals["seconds"],
        "total_plays": totals["plays"],
        "top_stories": [
            {
                "id": r["id"],
                "title": r["title"],
                "is_stream": bool(r["stream_url"]),
                "seconds": r["seconds"],
                "plays": r["plays"],
            }
            for r in top_rows
        ],
    }


def get_tracks(story_id: int) -> list[Track]:
    rows = get_connection().execute(
        "SELECT * FROM tracks WHERE story_id = ? ORDER BY position ASC", (story_id,)
    ).fetchall()
    return [Track(**dict(r)) for r in rows]


def get_track(track_id: int) -> Optional[Track]:
    row = get_connection().execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    return Track(**dict(row)) if row else None


def list_all_tracks() -> list[dict]:
    """Every track in the library with its parent story's title - source
    list for building a playlist out of already-uploaded tracks instead of
    uploading new files (see create_story_from_tracks in web/api.py)."""
    rows = get_connection().execute(
        """
        SELECT tracks.id, tracks.story_id, tracks.filename, tracks.title, tracks.duration,
               stories.title AS story_title
        FROM tracks
        JOIN stories ON stories.id = tracks.story_id
        WHERE stories.stream_url IS NULL
        ORDER BY stories.title COLLATE NOCASE, tracks.position ASC
        """
    ).fetchall()
    return [
        {
            "id": r["id"],
            "story_id": r["story_id"],
            "story_title": r["story_title"],
            "filename": r["filename"],
            "title": r["title"] or r["filename"],
            "duration": r["duration"],
        }
        for r in rows
    ]


def get_cascade_track_ids(seed_track_ids: list[int]) -> list[Track]:
    """Every track that disappears if the given tracks are deleted: the
    seeds themselves plus, transitively, every playlist's hard-linked copy
    of any of them (tracks.source_track_id ON DELETE CASCADE - see
    schema.sql). Call this *before* the actual delete (the DB rows are
    gone afterwards) so callers can also remove the now-orphaned
    hard-linked files from disk, which the DB-level cascade doesn't
    touch."""
    if not seed_track_ids:
        return []
    placeholders = ",".join("?" for _ in seed_track_ids)
    rows = get_connection().execute(
        f"""
        WITH RECURSIVE cascade(id) AS (
            SELECT id FROM tracks WHERE id IN ({placeholders})
            UNION
            SELECT tracks.id FROM tracks JOIN cascade ON tracks.source_track_id = cascade.id
        )
        SELECT tracks.* FROM tracks JOIN cascade ON tracks.id = cascade.id
        """,
        seed_track_ids,
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
        cur.execute("DELETE FROM parent_tags WHERE uid = ?", (uid,))


def remove_story_uid(story_id: int) -> None:
    with write_cursor() as cur:
        cur.execute("UPDATE stories SET uid = NULL WHERE id = ?", (story_id,))


def set_cover_path(story_id: int, cover_path: str) -> None:
    with write_cursor() as cur:
        cur.execute("UPDATE stories SET cover_path = ? WHERE id = ?", (cover_path, story_id))


def update_story_flags(story_id: int, shuffle: Optional[bool] = None, repeat: Optional[str] = None) -> None:
    story = get_story(story_id)
    if story is None:
        return
    shuffle = story.shuffle if shuffle is None else shuffle
    repeat = story.repeat if repeat is None else repeat
    if repeat not in REPEAT_MODES:
        raise ValueError(f"invalid repeat mode: {repeat!r}")
    with write_cursor() as cur:
        cur.execute(
            "UPDATE stories SET shuffle = ?, repeat = ? WHERE id = ?",
            (int(shuffle), repeat, story_id),
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


# -- parent tags (Vater/Mutter/...) -----------------------------------------


def list_parent_tags() -> list[dict]:
    rows = get_connection().execute("SELECT uid, label FROM parent_tags ORDER BY created_at ASC").fetchall()
    return [{"uid": r["uid"], "label": r["label"]} for r in rows]


def get_parent_tag_label(uid: str) -> Optional[str]:
    row = get_connection().execute("SELECT label FROM parent_tags WHERE uid = ?", (uid,)).fetchone()
    return row["label"] if row else None


def is_parent_tag(uid: str) -> bool:
    return get_parent_tag_label(uid) is not None


def add_parent_tag(uid: str, label: str) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO parent_tags (uid, label) VALUES (?, ?)
            ON CONFLICT(uid) DO UPDATE SET label = excluded.label
            """,
            (uid, label),
        )
        cur.execute("UPDATE stories SET uid = NULL WHERE uid = ?", (uid,))
        cur.execute("DELETE FROM function_tags WHERE uid = ?", (uid,))


def delete_parent_tag(uid: str) -> None:
    with write_cursor() as cur:
        cur.execute("DELETE FROM parent_tags WHERE uid = ?", (uid,))


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
        cur.execute("DELETE FROM parent_tags WHERE uid = ?", (uid,))


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
