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
-- rfid_uid is optional: a chip that, when scanned, logs this account into the
-- web UI from whatever browser is waiting on /login - no keyboard needed.
CREATE TABLE IF NOT EXISTS admin_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rfid_uid TEXT UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Chips that trigger an action (play/pause/next/previous/volume/wifi/power)
-- instead of playing a story when scanned - "control cards".
CREATE TABLE IF NOT EXISTS function_tags (
    uid TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Generic runtime-tunable settings (max_volume, volume_step, ...), editable from
-- /admin/settings instead of requiring a config.yaml edit + service restart.
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
