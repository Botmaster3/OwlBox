"""Ties RFID, buttons/encoder and the player together into the box's actual behaviour:
placing a known chip resumes its story, taking it off pauses and remembers where you were,
an unknown chip gets logged so the admin UI can offer to assign it right away."""
from __future__ import annotations

import json
import logging
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from . import feedback, multiroom, network, repository, system_info, themes
from .backlight import create_backlight
from .controls import create_controls
from .player import create_player
from .rfid import create_reader

logger = logging.getLogger("owlbox.engine")

_ALARM_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _wall_clock_now() -> datetime:
    """Thin wrapper around datetime.now() so tests can monkeypatch a fixed
    time instead of fighting the datetime builtin's own immutability."""
    return datetime.now()

# Function tags ("control cards"): scanning one of these runs an action instead of
# playing a story. (value, German label) - the label is what the RFID-tags admin
# page shows in the action picker.
FUNCTION_ACTIONS = [
    ("play", "Play"),
    ("pause", "Pause"),
    ("toggle_pause", "Play/Pause umschalten"),
    ("next", "Weiter"),
    ("previous", "Zurück"),
    ("volume_up", "Lauter"),
    ("volume_down", "Leiser"),
    ("wifi_on", "WLAN an"),
    ("wifi_off", "WLAN aus"),
    ("shuffle_toggle", "Shuffle an/aus"),
    ("repeat_folder_toggle", "Wiederholung Ordner an/aus"),
    ("repeat_track_toggle", "Wiederholung Track an/aus"),
    ("sleep_timer_15", "Einschlaf-Timer 15 Min"),
    ("sleep_timer_30", "Einschlaf-Timer 30 Min"),
    ("sleep_timer_45", "Einschlaf-Timer 45 Min"),
    ("sleep_timer_60", "Einschlaf-Timer 60 Min"),
    ("sleep_timer_cancel", "Einschlaf-Timer abbrechen"),
    ("restart", "Pi neu starten"),
    ("shutdown", "Pi herunterfahren"),
    ("game_toggle", "Spiele-Menü an/aus"),
]
FUNCTION_ACTION_VALUES = {value for value, _label in FUNCTION_ACTIONS}


class Engine:
    def __init__(self, config):
        self._config = config
        self._player = create_player(config)
        self._rfid = create_reader(config)
        self._controls = create_controls(
            config,
            on_next=self.manual_next,
            on_prev=self.manual_prev,
            on_toggle_pause=self.manual_toggle_pause,
            on_volume_delta=self._handle_volume_delta,
            on_seek=self.manual_seek,
            on_brightness_delta=self._handle_brightness_delta,
            on_shutdown=self._handle_shutdown if config.gpio.shutdown_hold_seconds else None,
            on_night_toggle=self.toggle_night_mode,
        )

        self._lock = threading.RLock()
        self._current_uid: Optional[str] = None
        self._current_story: Optional[repository.Story] = None
        # Unlike _current_story (which reflects whatever tag is on the
        # reader right now, and goes back to None the moment a function or
        # parent tag is scanned), this tracks whichever local story's
        # playlist is actually loaded into mpv - so a shuffle/repeat
        # function-card scanned after lifting the story chip still knows
        # what to apply itself to.
        self._loaded_story_id: Optional[int] = None
        self._current_function_action: Optional[str] = None
        self._current_parent_label: Optional[str] = None
        self._last_unknown_uid: Optional[str] = None
        self._max_volume = repository.get_int_setting("max_volume", 100)
        self._volume_step = repository.get_int_setting("volume_step", config.audio.volume_step)
        # Persisted the same way max_volume/volume_step already are - confirmed
        # on real hardware this was missing entirely: every restart of
        # owlbox.service (e.g. each `owlbox-stage <name>` step during the
        # staged bring-up, or just a normal reboot) silently reset playback
        # volume to config.audio.default_volume, discarding whatever the user
        # had actually set via the encoder/web UI. Falls back to
        # default_volume only when nothing has ever been saved yet (a
        # genuinely fresh install).
        self._volume = min(
            repository.get_int_setting("volume", config.audio.default_volume), self._max_volume
        )
        # Mirrors whatever volume was last actually handed to the player -
        # normally equal to self._volume, but briefly diverges from it during
        # a chime (see _play_chime_at, which drops the player to a quiet
        # level and back without touching self._volume, the real target) or
        # a sleep-timer fade (_check_sleep_timer). get_state() reports this
        # instead of querying the player/hardware mixer live - see
        # _apply_volume for why.
        self._last_applied_volume = self._volume
        self._chime_enabled = {
            name: bool(repository.get_int_setting(f"chime_enabled_{name}", 1 if config.audio.chime_enabled else 0))
            for name in feedback.CHIMES
        }
        self._chime_volume_percent = repository.get_int_setting(
            "chime_volume_percent", round(config.audio.chime_volume_ratio * 100)
        )
        stored_theme = repository.get_setting("theme")
        self._theme = stored_theme if themes.is_valid_theme(stored_theme) else themes.DEFAULT_THEME
        self._auto_theme_enabled = self._load_auto_theme_enabled()
        self._custom_theme_colors = self._load_custom_theme_colors()
        self._missing_reads = 0
        self._tag_present = False
        self._last_stat_time: Optional[float] = None
        self._sleep_timer_end: Optional[float] = None
        self._sleep_timer_minutes: Optional[float] = None
        self._sleep_fade_seconds = config.playback.sleep_fade_seconds
        self._sleep_timer_fading = False

        # Auto-sleep (sleeping-owl screen) - distinct from the sleep timer above:
        # this triggers *because* playback has been paused for a while, rather
        # than forcing a pause after a set time.
        self._auto_sleep_minutes = repository.get_int_setting(
            "auto_sleep_minutes", int(config.playback.auto_sleep_minutes)
        )
        self._paused_since: Optional[float] = None
        self._sleep_mode_active = False

        # Weckmodus (Einstellungen -> Audio): daily alarm that starts a
        # chosen story at a fixed time, ramping the volume up gently over
        # _alarm_fade_seconds instead of blasting in at full volume - the
        # reverse of the sleep timer's fade-out above. Persisted (unlike
        # game_mode/night_mode below) since a wake time set once should
        # survive a restart; _alarm_last_triggered_date is the one exception,
        # deliberately never persisted - it only exists to stop the same
        # alarm firing twice within its trigger minute, and starting fresh
        # after a restart just means "hasn't fired today yet", which is
        # always a safe assumption to fall back to.
        self._alarm_enabled = bool(repository.get_int_setting("alarm_enabled", 0))
        self._alarm_time = repository.get_setting("alarm_time") or "07:00"
        alarm_story_id = repository.get_int_setting("alarm_story_id", 0)
        self._alarm_story_id: Optional[int] = alarm_story_id or None
        self._alarm_fade_seconds = repository.get_int_setting("alarm_fade_seconds", 60)
        self._alarm_last_triggered_date = None
        self._alarm_fading = False
        self._alarm_fade_start = 0.0

        # AirPlay (optional OS-level add-on, shairport-sync - see
        # docs/hardware.md; not managed by this process at all, just ducked
        # around). shairport-sync's own before/after-play hook scripts call
        # airplay_session_started()/_ended() below over local HTTP. Purely a
        # live flag, never persisted - "is AirPlay audio flowing right now"
        # can't meaningfully outlive a restart anyway (shairport-sync would
        # have to open a whole new session against a freshly restarted
        # process regardless).
        self._airplay_active = False
        self._airplay_paused_our_playback = False

        # Mehrraum-Wiedergabe (optional OS-level add-on, Snapcast - see
        # owlbox/multiroom.py and docs/hardware.md). "off"/"master"/"slave",
        # persisted like the alarm settings above - a role set once should
        # survive a restart, unlike the live-only AirPlay flag above it
        # (there's no external process re-announcing this the way
        # shairport-sync re-announces a session).
        self._multiroom_role = repository.get_setting("multiroom_role") or "off"
        if self._multiroom_role not in multiroom.ROLES:
            self._multiroom_role = "off"
        master_peer_id = repository.get_int_setting("multiroom_master_peer_id", 0)
        self._multiroom_master_peer_id: Optional[int] = master_peer_id or None

        # Spiele-Menü (Einstellungen -> Spiel): toggled on/off by a dedicated
        # RFID function tag ("game_toggle" - see FUNCTION_ACTIONS/_execute_
        # function_action), same momentary-scan-toggles-state pattern as
        # shuffle_toggle. Never persisted - always starts off after a
        # restart, same reasoning as night mode above: physical state (is
        # the box currently in game mode) shouldn't outlive a reboot. Which
        # mini-game is currently open (if any) is purely a client-side
        # concern (see owlbox/web/static/js/game.js) - the engine only knows
        # whether the game screen as a whole is showing.
        self._game_mode_active = False

        self._backlight = create_backlight(config)
        self._min_brightness = repository.get_int_setting("min_brightness", 0)
        self._max_brightness = repository.get_int_setting("max_brightness", 100)
        self._brightness_step = repository.get_int_setting("brightness_step", config.gpio.brightness_step)
        self._brightness = max(
            self._min_brightness, min(self._max_brightness, repository.get_int_setting("brightness", 100))
        )
        # Night mode: a deliberately separate, deeper dim level from the usual
        # min/max_brightness range (that pair bounds the day-to-day slider/
        # encoder, night mode intentionally overrides it) - toggled by
        # pressing the brightness encoder's switch (see GpioControls) or the
        # web UI, not something that runs on a schedule. Never persisted
        # across a restart - always starts back in day mode, same as the
        # sleep-timer/auto-sleep state below never surviving one either.
        self._night_brightness = repository.get_int_setting("night_brightness", 5)
        self._night_mode_active = False
        self._day_brightness: Optional[int] = None

        # Cached WLAN reception, refreshed periodically in _loop rather than on every
        # get_state() call - nmcli is a subprocess call, too slow to run on every poll
        # from every open page (kiosk + Home + Einstellungen all hit /api/state every
        # second).
        self._wifi_enabled = False
        self._wifi_signal: Optional[int] = None
        self._last_wifi_check: Optional[float] = None

        # Fallback hotspot state machine (see _check_wifi_fallback) - kicks in once
        # WiFi has been enabled-but-disconnected for a while, so the box is never
        # fully unreachable just because the configured network moved/changed.
        self._hotspot_active = False
        self._hotspot_ip: Optional[str] = None
        self._wifi_disconnected_since: Optional[float] = None
        self._last_hotspot_retry: Optional[float] = None

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._player.start(self._multiroom_role)
        self._apply_volume(self._volume)
        self._backlight.set_brightness(self._brightness)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._play_chime("startup")
        logger.info("engine started (simulate=%s)", self._config.simulate)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        # Final exact save - the periodic autosave in _loop() only runs every
        # playback.position_save_interval seconds, so without this a clean
        # shutdown (systemd stop, reboot) could lose a few seconds of progress.
        self._persist_current_position()
        self._controls.close()
        self._rfid.close()
        self._player.stop()
        self._backlight.close()

    # -- background loop -------------------------------------------------

    def _loop(self) -> None:
        last_save = time.monotonic()
        poll_interval = self._config.rfid.poll_interval
        save_interval = self._config.playback.position_save_interval
        threshold = self._config.rfid.missing_reads_to_remove

        while not self._stop_event.is_set():
            try:
                uid = self._rfid.read_uid()
                if uid is not None:
                    self._missing_reads = 0
                    was_present = self._tag_present
                    if uid != self._current_uid:
                        self._handle_tag_present(uid)
                    self._tag_present = True
                    if not was_present:
                        # Edge-triggered: only an actual placement (tag was off,
                        # now it's on) wakes the box - a tag that's been sitting
                        # there the whole time it was asleep must not re-wake it
                        # on every single poll tick just for still being present.
                        self._wake_from_sleep_on_scan()
                else:
                    if self._tag_present:
                        self._missing_reads += 1
                        if self._missing_reads >= threshold:
                            self._handle_tag_removed()
                            self._tag_present = False

                now = time.monotonic()
                if now - last_save >= save_interval:
                    self._persist_current_position()
                    last_save = now

                self._check_sleep_timer(now)
                self._check_auto_sleep(now)
                self._check_alarm(now)
                self._check_wifi_status(now)
            except Exception:
                logger.exception("engine loop iteration failed")

            self._stop_event.wait(poll_interval)

    # -- RFID transitions --------------------------------------------------

    def _media_path(self, story: repository.Story, track: repository.Track) -> Path:
        return self._config.media_dir / str(story.id) / track.filename

    def _load_story_locked(self, story: repository.Story, persistence_key: str) -> None:
        """Loads `story`'s playlist into the player and starts it, resuming from
        the saved position for `persistence_key` (unless shuffled). Shared by a
        physical chip scan (_handle_tag_present) and starting a story straight
        from the web UI (play_story) - the two differ only in how they arrive
        at a story plus a stable key to save/resume its position against.
        Caller must already hold self._lock."""
        repository.increment_play_count(story.id)
        self._last_stat_time = time.monotonic()
        self._play_chime("known")

        if story.stream_url:
            # A livestream has no tracks/position to resume - always join live,
            # and it has no shuffle/repeat concept either.
            self._loaded_story_id = None
            self._player.load_playlist([story.stream_url])
            self._apply_volume(self._volume)
            logger.info("streaming '%s' (%s) from %s", story.title, persistence_key, story.stream_url)
            return

        self._loaded_story_id = story.id
        tracks = repository.get_tracks(story.id)
        filepaths = [str(self._media_path(story, t)) for t in tracks]
        if story.shuffle:
            # A saved resume position was recorded against last time's track
            # order - meaningless once shuffle puts a different track at that
            # same index, so start fresh rather than resuming into whatever
            # landed there.
            track_pos, seek_seconds = 0, 0.0
        else:
            track_pos, seek_seconds = repository.get_playback_state(persistence_key)
            if track_pos >= len(filepaths):
                track_pos, seek_seconds = 0, 0.0
        self._player.load_playlist(filepaths, start_index=track_pos, start_seconds=seek_seconds)
        self._player.set_shuffle(story.shuffle)
        self._player.set_repeat_mode(story.repeat)
        self._apply_volume(self._volume)
        logger.info(
            "playing '%s' (%s) from track %s @ %.1fs", story.title, persistence_key, track_pos, seek_seconds
        )

    def _handle_tag_present(self, uid: str) -> None:
        with self._lock:
            if self._current_uid is not None:
                self._persist_position_locked()

            story = repository.get_story_by_uid(uid)
            repository.log_scan(uid)
            self._current_uid = uid
            self._current_function_action = None
            self._current_parent_label = None

            if story is not None:
                self._current_story = story
                self._load_story_locked(story, uid)
                return

            self._current_story = None

            parent_label = repository.get_parent_tag_label(uid)
            if parent_label is not None:
                self._current_parent_label = parent_label
                logger.info("parent tag scanned (uid=%s, label=%s)", uid, parent_label)
                return

            action = repository.get_function_tag(uid)
            if action is not None:
                self._current_function_action = action
                self._play_chime("function")
                self._execute_function_action(action)
                return

            self._last_unknown_uid = uid
            self._play_chime("unknown")
            logger.info("unknown RFID tag scanned: %s", uid)

    def _handle_tag_removed(self) -> None:
        with self._lock:
            if self._current_uid is None:
                return
            if self._current_story is not None:
                # Story tags keep playing after the chip is lifted (unlike function/
                # parent tags below, which are momentary) - uid/story stay "current"
                # so playback continues uninterrupted and placing the same chip back
                # is a no-op instead of reloading/rewinding the playlist.
                self._persist_position_locked()
                logger.info("tag removed (uid=%s), story keeps playing", self._current_uid)
            else:
                self._current_uid = None
            self._current_function_action = None
            self._current_parent_label = None
            self._missing_reads = 0

    # -- starting/stopping a story from the web UI --------------------------

    def play_story(self, story_id: int) -> bool:
        """Starts a specific story directly - the web UI's equivalent of
        placing its chip on the reader, for a "▶ Play" button in the library.
        Runs the exact same playlist-loading path as a physical scan
        (_load_story_locked), just arrived at via story_id instead of a uid
        lookup. Works whether or not the story has an assigned chip: one
        without gets a stable "web:<id>" position-persistence key instead of
        a real uid, so its resume position still survives across web-UI
        plays (and keeps working if a chip gets assigned to it later - the
        two just track resume position separately until then). Returns False
        if the story doesn't exist."""
        story = repository.get_story(story_id)
        if story is None:
            return False
        key = story.uid if story.uid else f"web:{story.id}"
        with self._lock:
            if self._current_uid is not None:
                self._persist_position_locked()
            repository.log_scan(key)
            self._current_uid = key
            self._current_story = story
            self._current_function_action = None
            self._current_parent_label = None
            self._load_story_locked(story, key)
        self._wake_from_sleep_on_scan()
        return True

    def stop_playback(self) -> None:
        """Pauses and fully clears the "now playing" state (story/uid/loaded
        playlist) - the web UI's equivalent of lifting a chip that *doesn't*
        keep playing afterward. Unlike manual_pause(), which just pauses
        while leaving story/uid loaded, this also resets the dashboard back
        to "kein Chip aufgelegt". The exact position is still saved first
        (same persistence key as always), so the next play - chip or web UI -
        resumes right where this one stopped, it just isn't shown as "current"
        in the meantime."""
        with self._lock:
            self._persist_position_locked()
            self._current_uid = None
            self._current_story = None
            self._current_function_action = None
            self._current_parent_label = None
            self._loaded_story_id = None
        self._player.pause()

    def _execute_function_action(self, action: str) -> None:
        logger.info("executing RFID function tag action: %s", action)
        if action == "play":
            self.manual_play()
        elif action == "pause":
            self.manual_pause()
        elif action == "toggle_pause":
            self.manual_toggle_pause()
        elif action == "next":
            self.manual_next()
        elif action == "previous":
            self.manual_prev()
        elif action == "volume_up":
            self._handle_volume_delta(1)
        elif action == "volume_down":
            self._handle_volume_delta(-1)
        elif action == "wifi_on":
            self._set_wifi(True)
        elif action == "wifi_off":
            self._set_wifi(False)
        elif action == "shuffle_toggle":
            self._toggle_current_shuffle()
        elif action == "repeat_folder_toggle":
            self._toggle_current_repeat("folder")
        elif action == "repeat_track_toggle":
            self._toggle_current_repeat("track")
        elif action == "sleep_timer_15":
            self.start_sleep_timer(15)
        elif action == "sleep_timer_30":
            self.start_sleep_timer(30)
        elif action == "sleep_timer_45":
            self.start_sleep_timer(45)
        elif action == "sleep_timer_60":
            self.start_sleep_timer(60)
        elif action == "sleep_timer_cancel":
            self.cancel_sleep_timer()
        elif action == "restart":
            self.request_restart()
        elif action == "shutdown":
            self.request_shutdown()
        elif action == "game_toggle":
            self.toggle_game_mode()
        else:
            logger.warning("unknown function tag action: %s", action)

    def _set_wifi(self, enabled: bool) -> None:
        network.set_wifi_enabled(enabled)

    def _toggle_current_shuffle(self) -> None:
        # Scanning this function tag has already cleared _current_story (see
        # _handle_tag_present), so target whatever story is actually loaded
        # into the player instead - a no-op if nothing has ever played yet.
        # First placement turns shuffle on, lifting the chip and placing it
        # again turns it back off (each placement is a fresh scan, since
        # _handle_tag_removed resets _current_uid once the chip is lifted).
        if self._loaded_story_id is None:
            return
        story = repository.get_story(self._loaded_story_id)
        if story is not None:
            self.set_story_shuffle(self._loaded_story_id, not story.shuffle)

    def _toggle_current_repeat(self, mode: str) -> None:
        # Same on/off-per-placement idea as shuffle above, but per repeat
        # mode: placing the "Ordner" card again while it's already the
        # active mode turns repeat off; placing it while "Track" is active
        # switches straight to "Ordner" instead of turning it off.
        if self._loaded_story_id is None:
            return
        story = repository.get_story(self._loaded_story_id)
        if story is not None:
            new_mode = "off" if story.repeat == mode else mode
            self.set_story_repeat(self._loaded_story_id, new_mode)

    def _check_wifi_status(self, now: float, interval: float = 5.0) -> None:
        if self._last_wifi_check is not None and now - self._last_wifi_check < interval:
            return
        self._last_wifi_check = now
        status = network.get_status()
        with self._lock:
            self._wifi_enabled = status["enabled"]
            self._wifi_signal = status["signal"] if status["connected_ssid"] else None
        self._check_wifi_fallback(now, status)

    def _check_wifi_fallback(self, now: float, status: dict) -> None:
        """Starts a recovery hotspot once WiFi has been enabled-but-disconnected for
        longer than config.network.hotspot_after_seconds, so the box stays reachable
        even if its configured network moves, changes password, or disappears - see
        docs/hardware.md. Stops it again as soon as either a real connection comes
        back or a periodic retry manages to reconnect to a remembered network.
        """
        cfg = self._config.network

        if not status["enabled"]:
            # User explicitly turned WiFi off - respect that instead of fighting it.
            with self._lock:
                was_active = self._hotspot_active
                self._hotspot_active = False
                self._wifi_disconnected_since = None
                self._last_hotspot_retry = None
            if was_active:
                network.stop_hotspot()
            return

        if status["connected_ssid"]:
            with self._lock:
                was_active = self._hotspot_active
                self._hotspot_active = False
                self._wifi_disconnected_since = None
                self._last_hotspot_retry = None
            if was_active:
                logger.info("wifi reconnected (%s), stopping fallback hotspot", status["connected_ssid"])
                network.stop_hotspot()
            return

        with self._lock:
            hotspot_active = self._hotspot_active
            should_retry = hotspot_active and (
                self._last_hotspot_retry is None or now - self._last_hotspot_retry >= cfg.hotspot_retry_interval_seconds
            )
            if should_retry:
                self._last_hotspot_retry = now
            if not hotspot_active and self._wifi_disconnected_since is None:
                self._wifi_disconnected_since = now
            should_start = (
                not hotspot_active
                and self._wifi_disconnected_since is not None
                and now - self._wifi_disconnected_since >= cfg.hotspot_after_seconds
            )

        if should_retry:
            logger.info("fallback hotspot active, checking for a known network back in range")
            if network.try_reconnect_known_networks():
                logger.info("reconnected to a known network, stopping fallback hotspot")
                network.stop_hotspot()
                with self._lock:
                    self._hotspot_active = False
                    self._last_hotspot_retry = None
        elif should_start:
            logger.warning(
                "no wifi connection for %.0fs, starting fallback hotspot '%s'",
                cfg.hotspot_after_seconds,
                cfg.hotspot_ssid,
            )
            if network.start_hotspot(cfg.hotspot_ssid, cfg.hotspot_password):
                hotspot_ip = network.get_hotspot_ip()
                with self._lock:
                    self._hotspot_active = True
                    self._hotspot_ip = hotspot_ip
                    self._last_hotspot_retry = now

    def _persist_position_locked(self) -> None:
        if self._current_uid is None or self._current_story is None:
            return
        status = self._player.get_status()
        if not self._current_story.stream_url:
            repository.save_playback_state(self._current_uid, status["playlist_pos"], status["time_pos"])
        self._accumulate_listening_time_locked(status)

    def _accumulate_listening_time_locked(self, status: dict) -> None:
        # Hörstatistik: attribute only the time elapsed since the last call (this one
        # or the play-start reset in _handle_tag_present) to avoid double/under-counting
        # across periodic autosave ticks, tag switches, and removals alike.
        now = time.monotonic()
        if self._last_stat_time is not None and status.get("playing"):
            elapsed = now - self._last_stat_time
            if elapsed > 0 and self._current_story is not None:
                repository.add_listening_seconds(self._current_story.id, elapsed)
        self._last_stat_time = now

    def _persist_current_position(self) -> None:
        with self._lock:
            self._persist_position_locked()

    # -- manual controls (buttons, encoder, web API) ------------------------

    def _is_streaming(self) -> bool:
        return bool(self._current_story and self._current_story.stream_url)

    def manual_next(self) -> None:
        if self._is_streaming():
            return
        self._player.next()

    def manual_prev(self) -> None:
        if self._is_streaming():
            return
        status = self._player.get_status()
        if status["time_pos"] > self._config.playback.restart_track_after_seconds:
            self._player.seek(0)
        else:
            self._player.previous()

    def manual_seek(self, delta_seconds: float) -> None:
        if self._is_streaming():
            return
        self._player.seek(delta_seconds, absolute=False)

    def manual_seek_to(self, seconds: float) -> None:
        if self._is_streaming():
            return
        self._player.seek(max(0, seconds), absolute=True)

    def manual_play(self) -> None:
        with self._lock:
            self._wake_from_sleep_locked()
        self._player.play()

    def manual_pause(self) -> None:
        self._player.pause()

    def manual_toggle_pause(self) -> None:
        with self._lock:
            self._wake_from_sleep_locked()
        self._player.toggle_pause()

    def set_story_repeat(self, story_id: int, mode: str) -> bool:
        """Persists the story's repeat mode and, if that story is the one
        actually loaded into the player, applies it live right away too -
        otherwise a change made while it's playing would only take effect
        the next time this chip gets scanned again. Checked against
        _loaded_story_id rather than _current_story: a shuffle/repeat
        function-card scanned after lifting the story chip has already
        cleared _current_story, but the story's audio is still loaded."""
        if mode not in repository.REPEAT_MODES:
            return False
        repository.update_story_flags(story_id, repeat=mode)
        with self._lock:
            if self._current_story is not None and self._current_story.id == story_id:
                self._current_story.repeat = mode
            if self._loaded_story_id == story_id:
                self._player.set_repeat_mode(mode)
        return True

    def set_story_shuffle(self, story_id: int, enabled: bool) -> None:
        """Persists the story's shuffle flag and, if that story is the one
        actually loaded into the player, applies it live right away too -
        same reasoning as set_story_repeat above."""
        repository.update_story_flags(story_id, shuffle=enabled)
        with self._lock:
            if self._current_story is not None and self._current_story.id == story_id:
                self._current_story.shuffle = enabled
            if self._loaded_story_id == story_id:
                self._player.set_shuffle(enabled)

    def manual_set_volume(self, percent: int) -> None:
        with self._lock:
            self._set_volume_locked(percent)

    def _handle_volume_delta(self, direction: int) -> None:
        with self._lock:
            self._set_volume_locked(self._volume + direction * self._volume_step)

    def _apply_volume(self, percent: int) -> None:
        # The one place that's allowed to call self._player.set_volume()
        # directly - keeps self._last_applied_volume in sync with whatever
        # the player was actually just told, so get_state() can report it
        # without querying the player/hardware mixer live (see its comment
        # for why that matters). Called either under self._lock, or (from
        # start(), before the background thread exists) with nothing else
        # able to race it yet.
        self._last_applied_volume = percent
        self._player.set_volume(percent)

    def _set_volume_locked(self, percent: int) -> None:
        previous = self._volume
        self._volume = max(0, min(self._max_volume, percent))
        self._apply_volume(self._volume)
        # Persist the real target volume (not chime/fade dips, which never go
        # through here - see _apply_volume/_play_chime_at) so it survives a
        # restart of owlbox.service instead of resetting to config default
        # every time - same pattern as max_volume/volume_step below.
        repository.set_setting("volume", self._volume)
        # Turning all the way down to 0 pauses, turning back up resumes - mirrors
        # a real volume knob/mute button instead of just playing silently at 0.
        # Raising the volume also wakes the box from the auto-sleep screen, even
        # if it was paused (asleep) at a level above 0, not just from mute.
        if previous > 0 and self._volume == 0:
            self._player.pause()
        elif self._volume > previous and (previous == 0 or self._sleep_mode_active):
            self._wake_from_sleep_locked()
            self._player.play()

    def set_max_volume(self, percent: int) -> None:
        with self._lock:
            self._max_volume = max(1, min(100, percent))
            repository.set_setting("max_volume", self._max_volume)
            if self._volume > self._max_volume:
                self._volume = self._max_volume
                self._apply_volume(self._volume)
                repository.set_setting("volume", self._volume)

    def set_volume_step(self, percent: int) -> None:
        with self._lock:
            self._volume_step = max(1, min(50, percent))
            repository.set_setting("volume_step", self._volume_step)

    def set_chime_type_enabled(self, name: str, enabled: bool) -> None:
        if name not in feedback.CHIMES:
            return
        with self._lock:
            self._chime_enabled[name] = bool(enabled)
            repository.set_setting(f"chime_enabled_{name}", int(enabled))

    def set_chime_volume_percent(self, percent: int) -> None:
        with self._lock:
            self._chime_volume_percent = max(0, min(100, percent))
            repository.set_setting("chime_volume_percent", self._chime_volume_percent)

    def get_theme(self) -> str:
        """The theme actually in effect right now - whichever auto-eligible
        theme's calendar window matches today AND still has its own toggle
        on (see themes.get_auto_theme) wins over the manually picked one."""
        with self._lock:
            auto = themes.get_auto_theme(self._auto_theme_enabled)
            return auto or self._theme

    def get_manual_theme(self) -> str:
        with self._lock:
            return self._theme

    def get_seasonal_theme_active(self) -> Optional[str]:
        with self._lock:
            return themes.get_auto_theme(self._auto_theme_enabled)

    def get_auto_theme_enabled(self) -> Dict[str, bool]:
        with self._lock:
            return dict(self._auto_theme_enabled)

    def get_custom_theme_colors(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._custom_theme_colors)

    def set_theme(self, name: str) -> bool:
        if not themes.is_valid_theme(name):
            return False
        with self._lock:
            self._theme = name
            repository.set_setting("theme", name)
            # Picking a theme by hand is a clear "use this one now" signal -
            # if some *other* theme's auto window is active today and would
            # otherwise keep overriding this choice, turn just that one
            # toggle off so the click actually sticks. Every other theme's
            # toggle is left alone - unlike the old single global switch,
            # picking a theme in December no longer has to also silently
            # disable Ostern for next spring.
            current_auto = themes.get_auto_theme(self._auto_theme_enabled)
            if current_auto is not None and current_auto != name:
                self._auto_theme_enabled[current_auto] = False
                self._save_auto_theme_enabled()
        return True

    def set_auto_theme_enabled(self, theme_id: str, enabled: bool) -> bool:
        if theme_id not in themes.auto_themeable_ids():
            return False
        with self._lock:
            self._auto_theme_enabled[theme_id] = bool(enabled)
            self._save_auto_theme_enabled()
        return True

    def set_custom_theme_colors(self, colors: Dict[str, str]) -> bool:
        """Validates and merges `colors` into the saved custom-theme palette
        (a partial update is fine, e.g. changing just one field) and makes
        "custom" the active theme - same "editing it is a use-it-now signal"
        reasoning as set_theme(). Every value is validated here rather than
        trusting the caller: these end up in an inline `style` attribute
        (see web/__init__.py), so an unvalidated value would be a CSS/HTML
        injection route, not just a cosmetic bug."""
        updated = {}
        for key, value in colors.items():
            if key == "bar_radius":
                if not themes.is_valid_bar_radius(value):
                    return False
            elif key in themes.CUSTOM_THEME_VARS:
                if not themes.is_valid_custom_color(value):
                    return False
            else:
                return False
            updated[key] = value
        if not updated:
            return False
        with self._lock:
            self._custom_theme_colors.update(updated)
            repository.set_setting("custom_theme_colors", json.dumps(self._custom_theme_colors))
            self._theme = themes.CUSTOM_THEME_ID
            repository.set_setting("theme", themes.CUSTOM_THEME_ID)
            current_auto = themes.get_auto_theme(self._auto_theme_enabled)
            if current_auto is not None:
                self._auto_theme_enabled[current_auto] = False
                self._save_auto_theme_enabled()
        return True

    def _save_auto_theme_enabled(self) -> None:
        repository.set_setting("auto_theme_enabled", json.dumps(self._auto_theme_enabled))

    @staticmethod
    def _load_auto_theme_enabled() -> Dict[str, bool]:
        raw = repository.get_setting("auto_theme_enabled")
        stored = json.loads(raw) if raw else {}
        return {theme_id: bool(stored.get(theme_id, True)) for theme_id in themes.auto_themeable_ids()}

    @staticmethod
    def _load_custom_theme_colors() -> Dict[str, str]:
        raw = repository.get_setting("custom_theme_colors")
        stored = json.loads(raw) if raw else {}
        colors = dict(themes.DEFAULT_CUSTOM_THEME_COLORS)
        colors.update({k: v for k, v in stored.items() if k in colors})
        return colors

    def _play_chime(self, name: str) -> None:
        # No simulate-mode gate here on purpose - feedback.play_chime() already
        # degrades gracefully (no-op) if aplay/the audio device isn't available,
        # the same pattern as network.py/backlight.py elsewhere in this module.
        if not self._chime_enabled.get(name, False):
            return
        self._play_chime_at(name, self._chime_volume_percent)

    def test_chime(self, name: str, volume_percent: Optional[int] = None) -> None:
        # Ignores the per-type enabled toggle on purpose - "test" should let you
        # preview a chime even while deciding whether to keep it disabled.
        if name not in feedback.CHIMES:
            return
        percent = self._chime_volume_percent if volume_percent is None else max(0, min(100, volume_percent))
        self._play_chime_at(name, percent)

    def _play_chime_at(self, name: str, percent: int) -> None:
        with self._lock:
            chime_volume = round(self._max_volume * percent / 100)
            restore_to = self._volume
            # Chimes share the hardware mixer with the story (see feedback.py) -
            # drop it to a fixed, quiet level just for the chime, then restore
            # the real volume. play_chime() blocks until the chime finishes so
            # the restore below can't race a background loop tick.
            self._apply_volume(chime_volume)
            # try/finally matters here, not just style: real hardware showed
            # the hardware ALSA mixer stuck at the quiet chime_volume level
            # (e.g. 14% - almost exactly chime_volume_ratio's default 15%)
            # after a staged bring-up's rapid-fire `systemctl restart`/`stop`
            # cycles - a SIGTERM arriving while this call is still blocked in
            # feedback.play_chime()'s subprocess.run (up to its 3s timeout,
            # more likely to actually take that long if aplay is fighting
            # mpv for the same ALSA device - see feedback.py) turns into a
            # SystemExit unwinding straight through this frame, skipping the
            # restore below entirely - and nothing on the next start
            # re-applies it either, since Engine.start()'s own
            # _apply_volume(self._volume) call already happens fine before
            # this exact same race can repeat. A bare "restore after" line
            # only works when nothing ever interrupts it; finally runs
            # regardless.
            try:
                feedback.play_chime(name, self._config.audio.alsa_device)
            finally:
                self._apply_volume(restore_to)

    # -- display brightness -----------------------------------------------------

    def manual_set_brightness(self, percent: int) -> None:
        with self._lock:
            self._exit_night_mode_without_restoring_locked()
            self._brightness = max(self._min_brightness, min(self._max_brightness, percent))
            repository.set_setting("brightness", self._brightness)
            self._backlight.set_brightness(self._brightness)

    def _exit_night_mode_without_restoring_locked(self) -> None:
        """A direct brightness set (slider, or rotating the very encoder
        night mode's own switch lives on) always means "I want exactly this
        brightness now" - silently keep night mode flagged active underneath
        it, and the next button press would instead throw the just-picked
        value away and jump back to whatever "day" brightness was remembered
        before night mode started, which would make no sense to whoever just
        set it. Caller must already hold self._lock."""
        self._night_mode_active = False
        self._day_brightness = None

    def _handle_brightness_delta(self, direction: int) -> None:
        with self._lock:
            self._exit_night_mode_without_restoring_locked()
            self._brightness = max(
                self._min_brightness,
                min(self._max_brightness, self._brightness + direction * self._brightness_step),
            )
            repository.set_setting("brightness", self._brightness)
            self._backlight.set_brightness(self._brightness)

    def set_brightness_step(self, percent: int) -> None:
        with self._lock:
            self._brightness_step = max(1, min(50, percent))
            repository.set_setting("brightness_step", self._brightness_step)

    def set_min_brightness(self, percent: int) -> None:
        with self._lock:
            self._min_brightness = max(0, min(99, percent))
            if self._min_brightness >= self._max_brightness:
                # Push the upper bound out of the way rather than silently
                # ignoring the requested minimum.
                self._max_brightness = min(100, self._min_brightness + 1)
                repository.set_setting("max_brightness", self._max_brightness)
            repository.set_setting("min_brightness", self._min_brightness)
            if self._brightness < self._min_brightness:
                self._brightness = self._min_brightness
                repository.set_setting("brightness", self._brightness)
                self._backlight.set_brightness(self._brightness)

    def set_max_brightness(self, percent: int) -> None:
        with self._lock:
            self._max_brightness = max(1, min(100, percent))
            if self._max_brightness <= self._min_brightness:
                self._min_brightness = max(0, self._max_brightness - 1)
                repository.set_setting("min_brightness", self._min_brightness)
            repository.set_setting("max_brightness", self._max_brightness)
            if self._brightness > self._max_brightness:
                self._brightness = self._max_brightness
                repository.set_setting("brightness", self._brightness)
                self._backlight.set_brightness(self._brightness)

    # -- night mode -------------------------------------------------------------
    # Manual dim/undim toggle, deliberately independent of min/max_brightness
    # (see the __init__ comment) - "day" here just means "brightness as it was
    # right before night mode was switched on", not a literal time of day.

    def _set_night_mode_locked(self, active: bool) -> None:
        """Caller must already hold self._lock."""
        if active == self._night_mode_active:
            return
        if active:
            self._day_brightness = self._brightness
            self._night_mode_active = True
            self._brightness = max(0, min(100, self._night_brightness))
        else:
            self._night_mode_active = False
            if self._day_brightness is not None:
                self._brightness = self._day_brightness
            self._day_brightness = None
        repository.set_setting("brightness", self._brightness)
        self._backlight.set_brightness(self._brightness)

    def toggle_night_mode(self) -> None:
        """Wired to the brightness encoder's push switch - one press dims to
        night_brightness and remembers the current ("day") brightness, the
        next press restores it. See docs/hardware.md for the wiring."""
        with self._lock:
            self._set_night_mode_locked(not self._night_mode_active)
        logger.info("night mode %s", "activated" if self._night_mode_active else "deactivated")

    def set_night_mode_active(self, active: bool) -> None:
        """Explicit set (vs. toggle_night_mode's flip) - used by the web UI,
        where a checkbox/button needs to land on a known state rather than
        blindly flipping whatever the physical encoder last left it at."""
        with self._lock:
            self._set_night_mode_locked(active)

    def set_night_brightness(self, percent: int) -> None:
        with self._lock:
            self._night_brightness = max(0, min(100, percent))
            repository.set_setting("night_brightness", self._night_brightness)
            if self._night_mode_active:
                self._brightness = self._night_brightness
                repository.set_setting("brightness", self._brightness)
                self._backlight.set_brightness(self._brightness)

    # -- sleep timer ----------------------------------------------------------

    def start_sleep_timer(self, minutes: float) -> None:
        with self._lock:
            self._sleep_timer_minutes = minutes
            self._sleep_timer_end = time.monotonic() + minutes * 60
        logger.info("sleep timer set: %.1f minutes", minutes)

    def cancel_sleep_timer(self) -> None:
        with self._lock:
            self._sleep_timer_end = None
            self._sleep_timer_minutes = None
            self._restore_volume_after_fade_locked()

    def _restore_volume_after_fade_locked(self) -> None:
        # No-op unless a fade was actually in progress - safe to call from
        # anywhere the timer might stop before reaching zero.
        if self._sleep_timer_fading:
            self._sleep_timer_fading = False
            self._apply_volume(self._volume)

    def _check_sleep_timer(self, now: float) -> None:
        with self._lock:
            if self._sleep_timer_end is None:
                return
            remaining = self._sleep_timer_end - now
            if remaining <= 0:
                self._sleep_timer_end = None
                self._sleep_timer_minutes = None
                self._sleep_timer_fading = False
                logger.info("sleep timer expired, pausing playback")
                self._persist_position_locked()
                self._player.pause()
                # Restore the real volume so the next play/resume isn't silent -
                # the fade only ever touches the player's instantaneous output,
                # never the configured target volume (self._volume).
                self._apply_volume(self._volume)
                return
            if self._sleep_fade_seconds > 0 and remaining <= self._sleep_fade_seconds:
                self._sleep_timer_fading = True
                faded = round(self._volume * (remaining / self._sleep_fade_seconds))
                self._apply_volume(faded)
            else:
                self._restore_volume_after_fade_locked()

    # -- Spiele-Menü --------------------------------------------------------
    # Purely a display-mode flag - the menu, which mini-game is open and its
    # logic live entirely client-side (owlbox/web/static/js/game*.js). The
    # only server-side content is the per-game media pools (game_images,
    # sound_clips, quiz_items - see repository.py/api.py). Independent of
    # playback: toggling it doesn't pause/resume anything, a story can keep
    # playing in the background while the kiosk shows the game screen
    # instead of the now-playing view.

    def toggle_game_mode(self) -> None:
        with self._lock:
            self._game_mode_active = not self._game_mode_active
            active = self._game_mode_active
        logger.info("game mode %s", "activated" if active else "deactivated")

    # -- auto-sleep (sleeping-owl screen) --------------------------------------

    def set_auto_sleep_minutes(self, minutes: int) -> None:
        with self._lock:
            self._auto_sleep_minutes = max(0, minutes)
            repository.set_setting("auto_sleep_minutes", self._auto_sleep_minutes)

    def _wake_from_sleep_locked(self) -> None:
        # Safe to call unconditionally from any "resume-ish" action - a no-op
        # unless the box was actually asleep.
        if self._sleep_mode_active:
            self._sleep_mode_active = False
            self._paused_since = None
            logger.info("auto-sleep: woke up")

    def _wake_from_sleep_on_scan(self) -> None:
        # Placing/re-scanning a tag while a chip is already sitting on the reader
        # doesn't go through _handle_tag_present (uid hasn't changed) - checked
        # here on every poll instead so "scan a tag" reliably wakes the box up.
        with self._lock:
            if not self._sleep_mode_active:
                return
            self._wake_from_sleep_locked()
        self._player.play()

    def _check_auto_sleep(self, now: float) -> None:
        with self._lock:
            if self._sleep_mode_active or self._auto_sleep_minutes <= 0:
                return
            if self._current_story is None or self._is_streaming():
                self._paused_since = None
                return
            if not self._player.get_status().get("paused"):
                self._paused_since = None
                return
            if self._paused_since is None:
                self._paused_since = now
                return
            if now - self._paused_since >= self._auto_sleep_minutes * 60:
                self._sleep_mode_active = True
                logger.info(
                    "auto-sleep: paused for %.0f min, showing sleeping-owl screen", self._auto_sleep_minutes
                )

    # -- Weckmodus ------------------------------------------------------------

    def set_alarm(
        self,
        enabled: bool,
        time_str: str,
        story_id: Optional[int],
        fade_seconds: int,
    ) -> None:
        if not _ALARM_TIME_RE.match(time_str):
            raise ValueError("time_str must be HH:MM")
        with self._lock:
            self._alarm_enabled = enabled
            self._alarm_time = time_str
            self._alarm_story_id = story_id
            self._alarm_fade_seconds = max(0, fade_seconds)
            repository.set_setting("alarm_enabled", int(enabled))
            repository.set_setting("alarm_time", time_str)
            repository.set_setting("alarm_story_id", story_id or 0)
            repository.set_setting("alarm_fade_seconds", self._alarm_fade_seconds)

    def _check_alarm(self, now: float) -> None:
        # Two clocks in play here on purpose: `now` (time.monotonic) paces the
        # fade-in the same way _check_sleep_timer paces its fade-out, while
        # matching "is it time to wake up yet" needs actual wall-clock time -
        # monotonic time has no relationship to the hour of day.
        trigger_story_id = None
        with self._lock:
            if self._alarm_fading:
                elapsed = now - self._alarm_fade_start
                if self._alarm_fade_seconds <= 0 or elapsed >= self._alarm_fade_seconds:
                    self._alarm_fading = False
                    self._apply_volume(self._volume)
                else:
                    self._apply_volume(round(self._volume * (elapsed / self._alarm_fade_seconds)))

            if not self._alarm_enabled or self._alarm_story_id is None:
                return
            wall_now = _wall_clock_now()
            if wall_now.strftime("%H:%M") != self._alarm_time:
                return
            if self._alarm_last_triggered_date == wall_now.date():
                return
            # Only wakes an idle/paused box - a story already playing (a kid
            # got up early and started listening themselves, or an earlier
            # scan is still going) is never interrupted by the alarm.
            if self._player.get_status().get("playing"):
                return
            self._alarm_last_triggered_date = wall_now.date()
            trigger_story_id = self._alarm_story_id

        if trigger_story_id is not None:
            logger.info("alarm: waking with story id=%s", trigger_story_id)
            if self.play_story(trigger_story_id):
                with self._lock:
                    self._alarm_fade_start = now
                    self._alarm_fading = self._alarm_fade_seconds > 0
                    self._apply_volume(0 if self._alarm_fading else self._volume)
            else:
                logger.warning("alarm: configured story id=%s no longer exists", trigger_story_id)

    # -- AirPlay --------------------------------------------------------------
    # Called by shairport-sync's own session hook scripts (run_this_before_
    # play_begins/run_this_after_play_ends in its config, POSTing to
    # /api/airplay/session-{start,end} - see owlbox/web/api.py) rather than
    # from anywhere inside this process: shairport-sync is an entirely
    # separate OS-level service, not something this codebase starts/stops or
    # even knows how to talk to except over that one local HTTP round-trip.

    def airplay_session_started(self) -> None:
        with self._lock:
            self._airplay_active = True
            # Only duck (and later resume) if OwlBox itself was actually
            # playing - never start playback that wasn't already happening
            # just because an AirPlay session began.
            if self._player.get_status().get("playing"):
                self._persist_position_locked()
                self._player.pause()
                self._airplay_paused_our_playback = True
            else:
                self._airplay_paused_our_playback = False
        logger.info(
            "AirPlay session started%s", " (paused OwlBox playback)" if self._airplay_paused_our_playback else ""
        )

    def airplay_session_ended(self) -> None:
        with self._lock:
            self._airplay_active = False
            resume = self._airplay_paused_our_playback
            self._airplay_paused_our_playback = False
        if resume:
            self._player.play()
        logger.info("AirPlay session ended%s", " (resumed OwlBox playback)" if resume else "")

    # -- Mehrraum-Wiedergabe (Snapcast) --------------------------------------

    def set_multiroom(self, role: str, master_peer_id: Optional[int]) -> tuple[bool, str]:
        """Applies and persists a Mehrraum role. Only ever persists the new
        role once multiroom.set_role() has actually confirmed applying it at
        the OS level succeeded - a role that failed to apply must not read
        back as active in the UI (see set_hostname's identical reasoning in
        system_info.py). Restarting owlbox.service is still required
        afterwards for player.py to pick up the new audio routing - this
        only flips the systemd services and the persisted setting."""
        if role not in multiroom.ROLES:
            raise ValueError(f"Unbekannte Rolle: {role}")
        master_host = None
        if role == "slave":
            if not master_peer_id:
                return False, "Keine Hauptbox ausgewählt."
            peer = repository.get_peer(master_peer_id)
            if peer is None:
                return False, "Ausgewählte Hauptbox wurde nicht gefunden - evtl. wurde sie aus der Liste gelöscht."
            master_host = peer.host

        ok, message = multiroom.set_role(role, master_host)
        if not ok:
            return False, message

        with self._lock:
            self._multiroom_role = role
            self._multiroom_master_peer_id = master_peer_id if role == "slave" else None
            repository.set_setting("multiroom_role", role)
            repository.set_setting("multiroom_master_peer_id", (master_peer_id if role == "slave" else 0) or 0)
        return True, "ok"

    def _handle_shutdown(self) -> None:
        logger.warning("shutdown requested via encoder long-press")
        self.request_shutdown()

    def request_shutdown(self) -> None:
        self._persist_current_position()
        self._play_chime("shutdown")
        try:
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
        except Exception:
            logger.exception("failed to invoke shutdown")

    def request_restart(self) -> None:
        self._persist_current_position()
        self._play_chime("shutdown")
        try:
            subprocess.run(["sudo", "shutdown", "-r", "now"], check=False)
        except Exception:
            logger.exception("failed to invoke restart")

    def simulate_scan(self, uid: str, hold_seconds: Optional[float] = None) -> None:
        inject = getattr(self._rfid, "inject", None)
        if inject is None:
            raise RuntimeError("simulate_scan is only available with the simulated RFID reader")
        inject(uid, hold_seconds=hold_seconds)

    def simulate_remove(self) -> None:
        clear = getattr(self._rfid, "clear", None)
        if clear is None:
            raise RuntimeError("simulate_remove is only available with the simulated RFID reader")
        clear()

    # -- state for the web UI ------------------------------------------------

    def get_state(self) -> dict:
        with self._lock:
            story = self._current_story
            current_uid = self._current_uid
            function_action = self._current_function_action
            parent_label = self._current_parent_label
            last_unknown = self._last_unknown_uid
            volume = self._last_applied_volume
            max_volume = self._max_volume
            volume_step = self._volume_step
            chime_enabled = dict(self._chime_enabled)
            chime_volume_percent = self._chime_volume_percent
            manual_theme = self._theme
            auto_theme_enabled = dict(self._auto_theme_enabled)
            custom_theme_colors = dict(self._custom_theme_colors)
            seasonal_theme_active = themes.get_auto_theme(auto_theme_enabled)
            theme = seasonal_theme_active or manual_theme
            sleep_timer_end = self._sleep_timer_end
            sleep_timer_minutes = self._sleep_timer_minutes
            auto_sleep_minutes = self._auto_sleep_minutes
            sleep_mode_active = self._sleep_mode_active
            game_mode_active = self._game_mode_active
            brightness = self._brightness
            min_brightness = self._min_brightness
            max_brightness = self._max_brightness
            brightness_step = self._brightness_step
            night_brightness = self._night_brightness
            night_mode_active = self._night_mode_active
            wifi_enabled = self._wifi_enabled
            wifi_signal = self._wifi_signal
            hotspot_active = self._hotspot_active
            hotspot_ip = self._hotspot_ip
            alarm_enabled = self._alarm_enabled
            alarm_time = self._alarm_time
            alarm_story_id = self._alarm_story_id
            alarm_fade_seconds = self._alarm_fade_seconds
            airplay_active = self._airplay_active
            multiroom_role = self._multiroom_role
            multiroom_master_peer_id = self._multiroom_master_peer_id
        alarm_story_title = None
        if alarm_story_id is not None:
            alarm_story = repository.get_story(alarm_story_id)
            alarm_story_title = alarm_story.title if alarm_story is not None else None
        # Cheap local DB lookup, not a network call - a live reachability
        # check against the peer belongs in the dedicated /api/peers
        # endpoint only (get_state() is polled every second by every open
        # page, see the volume-override comment below for why that matters).
        multiroom_master_peer = None
        if multiroom_master_peer_id is not None:
            multiroom_master_peer = repository.get_peer(multiroom_master_peer_id)
        status = self._player.get_status()
        # Overrides player.get_status()'s own placeholder "volume" (see its
        # comment - MpvPlayer used to fill this via a live `amixer sget`
        # read, a subprocess spawn on every single call) with
        # self._last_applied_volume, captured above under the lock. THE
        # actual root cause of a real-hardware "continuous crackling during
        # playback" complaint that turned out to have nothing to do with
        # config.txt/kernel overlays at all: /api/state is polled every
        # second from every open page (kiosk + any open admin tab, see the
        # __init__ comment on _wifi_enabled above for the same lesson learned
        # about nmcli) - each poll was forking an amixer subprocess just to
        # report a value the Engine already knows precisely, because
        # _apply_volume() is the only thing that ever changes it (there's no
        # separate hardware volume pot on this project's amp to read back
        # independently). That steady drip of process spawns was enough
        # added CPU contention on a Pi 3B+ - already tight on cycles because
        # the kiosk's Chromium runs fully software-rendered, see
        # docs/hardware.md - to starve mpv's audio thread often enough to be
        # audible, even with the generous --audio-buffer=1.0 already in
        # place for exactly this class of problem. Deliberately
        # self._last_applied_volume and not self._volume: the two briefly
        # diverge during a chime or sleep-timer fade (see _apply_volume's
        # comment) - self._volume alone would have silently hidden that
        # dip from anything polling state, changing user-visible behaviour.
        status["volume"] = volume

        sleep_timer_remaining = None
        if sleep_timer_end is not None:
            sleep_timer_remaining = max(0, round(sleep_timer_end - time.monotonic()))

        track_title = None
        track_titles: list[str] = []
        current_track_index: Optional[int] = None
        if story is not None and not story.stream_url:
            tracks = repository.get_tracks(story.id)
            track_titles = [t.title or Path(t.filename).stem for t in tracks]
            index = status.get("playlist_pos", 0)
            if 0 <= index < len(track_titles):
                track_title = track_titles[index]
                current_track_index = index

        is_unknown = (
            story is None and function_action is None and parent_label is None and current_uid is not None
        )

        return {
            "uid": current_uid,
            "story": None
            if story is None
            else {
                "id": story.id,
                "title": story.title,
                "cover_url": f"/media/{story.id}/{story.cover_path}" if story.cover_path else None,
                "track_title": track_title,
                "tracks": track_titles,
                "current_track_index": current_track_index,
                "is_stream": bool(story.stream_url),
                "shuffle": story.shuffle,
                "repeat": story.repeat,
            },
            "function_tag": function_action,
            "unknown_tag": current_uid if is_unknown else None,
            "last_unknown_uid": last_unknown,
            "player": status,
            "settings": {
                "max_volume": max_volume,
                "volume_step": volume_step,
                "brightness": brightness,
                "min_brightness": min_brightness,
                "max_brightness": max_brightness,
                "brightness_step": brightness_step,
                "night_brightness": night_brightness,
                "night_mode_active": night_mode_active,
                "auto_sleep_minutes": auto_sleep_minutes,
                "chime_enabled": chime_enabled,
                "chime_volume_percent": chime_volume_percent,
                "theme": theme,
                "manual_theme": manual_theme,
                "auto_theme_enabled": auto_theme_enabled,
                "seasonal_theme_active": seasonal_theme_active,
                "custom_theme_colors": custom_theme_colors,
                "advent_candles": themes.get_advent_candle_count(),
                "christmas_eve": themes.is_christmas_eve(),
            },
            "sleep_timer": {
                "active": sleep_timer_end is not None,
                "minutes": sleep_timer_minutes,
                "remaining_seconds": sleep_timer_remaining,
            },
            "auto_sleep": {
                "active": sleep_mode_active,
                "minutes": auto_sleep_minutes,
            },
            "wifi": {
                "enabled": wifi_enabled,
                "signal": wifi_signal,
                "hotspot_active": hotspot_active,
                "hotspot_ssid": self._config.network.hotspot_ssid if hotspot_active else None,
                "hotspot_password": self._config.network.hotspot_password if hotspot_active else None,
                "hotspot_ip": hotspot_ip if hotspot_active else None,
            },
            "parent_mode": {"active": parent_label is not None, "label": parent_label},
            "game_mode": {"active": game_mode_active},
            "alarm": {
                "enabled": alarm_enabled,
                "time": alarm_time,
                "story_id": alarm_story_id,
                "story_title": alarm_story_title,
                "fade_seconds": alarm_fade_seconds,
            },
            "airplay": {"active": airplay_active},
            "multiroom": {
                "role": multiroom_role,
                "master_peer_id": multiroom_master_peer_id,
                "master_peer_name": multiroom_master_peer.name if multiroom_master_peer else None,
            },
            # A plain sysfs read (see system_info.get_cpu_temperature_celsius),
            # not a subprocess call like the WiFi signal above - cheap enough
            # to do inline on every poll instead of needing the same
            # background-loop caching treatment.
            "system": {"cpu_temp_celsius": system_info.get_cpu_temperature_celsius()},
        }
