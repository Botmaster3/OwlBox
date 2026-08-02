CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE,
    title TEXT NOT NULL,
    cover_path TEXT,
    shuffle INTEGER NOT NULL DEFAULT 0,
    repeat INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    filename TEXT NOT NULL,
    title TEXT,
    duration REAL
);
CREATE INDEX IF NOT EXISTS idx_tracks_story ON tracks(story_id, position);

CREATE TABLE IF NOT EXISTS playback_state (
    uid TEXT PRIMARY KEY,
    track_position INTEGER NOT NULL DEFAULT 0,
    seek_seconds REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Recent RFID scans of chips that aren't assigned to a story yet, so the admin UI
-- can offer "assign this chip" right after someone places a new figure on the box.
CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT NOT NULL,
    seen_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Single admin account gating /admin and the mutating API. Empty table means
-- setup hasn't run yet - the login page redirects to /setup until one exists.
CREATE TABLE IF NOT EXISTS admin_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
