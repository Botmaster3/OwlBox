"""Ties RFID, buttons/encoder and the player together into the box's actual behaviour:
placing a known chip resumes its story, taking it off pauses and remembers where you were,
an unknown chip gets logged so the admin UI can offer to assign it right away."""
from __future__ import annotations

import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from . import network, repository
from .controls import create_controls
from .player import create_player
from .rfid import create_reader

logger = logging.getLogger("owlbox.engine")

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
    ("sleep_timer_15", "Einschlaf-Timer 15 Min"),
    ("sleep_timer_30", "Einschlaf-Timer 30 Min"),
    ("sleep_timer_45", "Einschlaf-Timer 45 Min"),
    ("sleep_timer_60", "Einschlaf-Timer 60 Min"),
    ("sleep_timer_cancel", "Einschlaf-Timer abbrechen"),
    ("restart", "Pi neu starten"),
    ("shutdown", "Pi herunterfahren"),
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
            on_shutdown=self._handle_shutdown if config.gpio.shutdown_hold_seconds else None,
        )

        self._lock = threading.RLock()
        self._current_uid: Optional[str] = None
        self._current_story: Optional[repository.Story] = None
        self._current_function_action: Optional[str] = None
        self._current_parent_label: Optional[str] = None
        self._last_unknown_uid: Optional[str] = None
        self._max_volume = repository.get_int_setting("max_volume", 100)
        self._volume_step = repository.get_int_setting("volume_step", config.audio.volume_step)
        self._volume = min(config.audio.default_volume, self._max_volume)
        self._missing_reads = 0
        self._sleep_timer_end: Optional[float] = None
        self._sleep_timer_minutes: Optional[float] = None

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._player.start()
        self._player.set_volume(self._volume)
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
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
                    if uid != self._current_uid:
                        self._handle_tag_present(uid)
                else:
                    if self._current_uid is not None:
                        self._missing_reads += 1
                        if self._missing_reads >= threshold:
                            self._handle_tag_removed()

                now = time.monotonic()
                if now - last_save >= save_interval:
                    self._persist_current_position()
                    last_save = now

                self._check_sleep_timer(now)
            except Exception:
                logger.exception("engine loop iteration failed")

            self._stop_event.wait(poll_interval)

    # -- RFID transitions --------------------------------------------------

    def _media_path(self, story: repository.Story, track: repository.Track) -> Path:
        return self._config.media_dir / str(story.id) / track.filename

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
                tracks = repository.get_tracks(story.id)
                filepaths = [str(self._media_path(story, t)) for t in tracks]
                track_pos, seek_seconds = repository.get_playback_state(uid)
                if track_pos >= len(filepaths):
                    track_pos, seek_seconds = 0, 0.0
                self._player.load_playlist(filepaths, start_index=track_pos, start_seconds=seek_seconds)
                self._player.set_volume(self._volume)
                logger.info("playing '%s' (uid=%s) from track %s @ %.1fs", story.title, uid, track_pos, seek_seconds)
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
                self._execute_function_action(action)
                return

            self._last_unknown_uid = uid
            logger.info("unknown RFID tag scanned: %s", uid)

    def _handle_tag_removed(self) -> None:
        with self._lock:
            if self._current_uid is None:
                return
            if self._current_story is not None:
                self._persist_position_locked()
                logger.info("tag removed (uid=%s), pausing", self._current_uid)
                self._player.pause()
            self._current_uid = None
            self._current_story = None
            self._current_function_action = None
            self._current_parent_label = None
            self._missing_reads = 0

    def _execute_function_action(self, action: str) -> None:
        logger.info("executing RFID function tag action: %s", action)
        if action == "play":
            self._player.play()
        elif action == "pause":
            self._player.pause()
        elif action == "toggle_pause":
            self._player.toggle_pause()
        elif action == "next":
            self._player.next()
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
        else:
            logger.warning("unknown function tag action: %s", action)

    def _set_wifi(self, enabled: bool) -> None:
        network.set_wifi_enabled(enabled)

    def _persist_position_locked(self) -> None:
        if self._current_uid is None or self._current_story is None:
            return
        status = self._player.get_status()
        repository.save_playback_state(self._current_uid, status["playlist_pos"], status["time_pos"])

    def _persist_current_position(self) -> None:
        with self._lock:
            self._persist_position_locked()

    # -- manual controls (buttons, encoder, web API) ------------------------

    def manual_next(self) -> None:
        self._player.next()

    def manual_prev(self) -> None:
        status = self._player.get_status()
        if status["time_pos"] > self._config.playback.restart_track_after_seconds:
            self._player.seek(0)
        else:
            self._player.previous()

    def manual_seek(self, delta_seconds: float) -> None:
        self._player.seek(delta_seconds, absolute=False)

    def manual_play(self) -> None:
        self._player.play()

    def manual_pause(self) -> None:
        self._player.pause()

    def manual_toggle_pause(self) -> None:
        self._player.toggle_pause()

    def manual_set_volume(self, percent: int) -> None:
        with self._lock:
            self._volume = max(0, min(self._max_volume, percent))
            self._player.set_volume(self._volume)

    def _handle_volume_delta(self, direction: int) -> None:
        with self._lock:
            self._volume = max(0, min(self._max_volume, self._volume + direction * self._volume_step))
            self._player.set_volume(self._volume)

    def set_max_volume(self, percent: int) -> None:
        with self._lock:
            self._max_volume = max(1, min(100, percent))
            repository.set_setting("max_volume", self._max_volume)
            if self._volume > self._max_volume:
                self._volume = self._max_volume
                self._player.set_volume(self._volume)

    def set_volume_step(self, percent: int) -> None:
        with self._lock:
            self._volume_step = max(1, min(50, percent))
            repository.set_setting("volume_step", self._volume_step)

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

    def _check_sleep_timer(self, now: float) -> None:
        with self._lock:
            if self._sleep_timer_end is None or now < self._sleep_timer_end:
                return
            self._sleep_timer_end = None
            self._sleep_timer_minutes = None
            logger.info("sleep timer expired, pausing playback")
            self._persist_position_locked()
            self._player.pause()

    def _handle_shutdown(self) -> None:
        logger.warning("shutdown requested via encoder long-press")
        self.request_shutdown()

    def request_shutdown(self) -> None:
        self._persist_current_position()
        try:
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
        except Exception:
            logger.exception("failed to invoke shutdown")

    def request_restart(self) -> None:
        self._persist_current_position()
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
            max_volume = self._max_volume
            volume_step = self._volume_step
            sleep_timer_end = self._sleep_timer_end
            sleep_timer_minutes = self._sleep_timer_minutes
        status = self._player.get_status()

        sleep_timer_remaining = None
        if sleep_timer_end is not None:
            sleep_timer_remaining = max(0, round(sleep_timer_end - time.monotonic()))

        track_title = None
        upcoming_tracks: list[str] = []
        if story is not None:
            tracks = repository.get_tracks(story.id)
            index = status.get("playlist_pos", 0)
            if 0 <= index < len(tracks):
                track = tracks[index]
                track_title = track.title or Path(track.filename).stem
            upcoming_tracks = [t.title or Path(t.filename).stem for t in tracks[index + 1 :]]

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
                "upcoming_tracks": upcoming_tracks,
            },
            "function_tag": function_action,
            "unknown_tag": current_uid if is_unknown else None,
            "last_unknown_uid": last_unknown,
            "player": status,
            "settings": {"max_volume": max_volume, "volume_step": volume_step},
            "sleep_timer": {
                "active": sleep_timer_end is not None,
                "minutes": sleep_timer_minutes,
                "remaining_seconds": sleep_timer_remaining,
            },
            "parent_mode": {"active": parent_label is not None, "label": parent_label},
        }
