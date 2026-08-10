-- A story is either a local playlist (tracks table) or a livestream (stream_url
-- set, no tracks) - a chip plays whichever one it's assigned to the same way.
CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT UNIQUE,
    title TEXT NOT NULL,
    cover_path TEXT,
    stream_url TEXT,
    shuffle INTEGER NOT NULL DEFAULT 0,
    -- 'off' plays through once and stops; 'folder' loops the whole story
    -- from the first track once the last one ends; 'track' repeats
    -- whichever single track is currently playing instead of advancing.
    repeat TEXT NOT NULL DEFAULT 'off',
    -- Hörstatistik: how often and how long this story/stream has been played.
    play_count INTEGER NOT NULL DEFAULT 0,
    total_seconds REAL NOT NULL DEFAULT 0,
    last_played_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    filename TEXT NOT NULL,
    title TEXT,
    duration REAL,
    -- Set only for a track hard-linked into a "Playlist aus Bibliothek" story
    -- (see create_story_from_tracks in web/api.py) - points at the original
    -- track it was copied from. ON DELETE CASCADE means deleting that
    -- original track (directly, or via its story being deleted) also
    -- deletes every playlist's copy of it automatically; web/api.py reads
    -- this chain first to remove the now-orphaned hard-linked files too,
    -- since SQLite's cascade only removes the DB rows, not files on disk.
    source_track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE
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

-- Chips that trigger an action (play/pause/next/previous/volume/wifi/power)
-- instead of playing a story when scanned - "control cards".
CREATE TABLE IF NOT EXISTS function_tags (
    uid TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Parent chips (e.g. "Vater"/"Mutter"): scanning one logs the web session in
-- (see /api/auth/rfid-login) and puts the kiosk display into parent mode,
-- showing a QR code to the login page - normal story/function tags never
-- reveal that, keeping it out of kids' view.
CREATE TABLE IF NOT EXISTS parent_tags (
    uid TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Generic runtime-tunable settings (max_volume, volume_step, ...), editable from
-- /admin/settings instead of requiring a config.yaml edit + service restart.
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Per-day, per-story listening totals (UTC calendar day) - lets the Info page's
-- Wochenrückblick answer "how much / what got listened to in the last N days"
-- without scanning every scan_log row (that table only keeps the last 20 anyway).
-- stories.total_seconds/play_count above stay the all-time totals; this table is
-- purely additive alongside them, updated in the same repository calls.
CREATE TABLE IF NOT EXISTS daily_listening (
    date TEXT NOT NULL,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    seconds REAL NOT NULL DEFAULT 0,
    plays INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, story_id)
);

-- Uploaded picture pool for the Spiele-Menü (Einstellungen -> Spiel) - the
-- kiosk's one deliberate use of the display's touch hardware (otherwise
-- unused, see docs/hardware.md), unlocked by a dedicated "game_toggle"
-- function tag (see Engine.FUNCTION_ACTIONS). Shared by two mini-games -
-- Memory (match pairs) and Schiebe-Puzzle (reassemble one sliced-up image) -
-- so one upload benefits both instead of asking for the same kind of
-- picture twice. Flat list, no per-story grouping needed - position is just
-- upload order, drawn from client-side (owlbox/web/static/js/game-memory.js,
-- game-puzzle.js).
CREATE TABLE IF NOT EXISTS game_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Uploaded sound-clip pool for the Sound-Memory mini-game (same Spiele-Menü
-- as above) - pairs are matched by ear instead of by sight: tapping a card
-- plays its clip, find the other card with the same clip. Same flat-list/
-- upload-order shape as game_images, just audio instead of images - see
-- game-soundmemory.js.
CREATE TABLE IF NOT EXISTS sound_clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Picture+sound pairs for the Tier-Sound-Quiz mini-game (same Spiele-Menü) -
-- a clip plays (e.g. a cow mooing), the player taps the matching picture out
-- of a few shown. label is optional, admin-only context (e.g. "Kuh") never
-- shown to the player - the game is meant to work by ear/eye, not by text.
-- See game-quiz.js.
CREATE TABLE IF NOT EXISTS quiz_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_filename TEXT NOT NULL,
    sound_filename TEXT NOT NULL,
    label TEXT,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
