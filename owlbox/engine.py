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

from . import feedback, network, repository
from .backlight import create_backlight
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
            on_brightness_delta=self._handle_brightness_delta,
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
        self._chime_enabled = {
            name: bool(repository.get_int_setting(f"chime_enabled_{name}", 1 if config.audio.chime_enabled else 0))
            for name in feedback.CHIMES
        }
        self._chime_volume_percent = repository.get_int_setting(
            "chime_volume_percent", round(config.audio.chime_volume_ratio * 100)
        )
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

        self._backlight = create_backlight(config)
        self._min_brightness = repository.get_int_setting("min_brightness", 0)
        self._max_brightness = repository.get_int_setting("max_brightness", 100)
        self._brightness_step = repository.get_int_setting("brightness_step", config.gpio.brightness_step)
        self._brightness = max(
            self._min_brightness, min(self._max_brightness, repository.get_int_setting("brightness", 100))
        )

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
        self._player.start()
        self._player.set_volume(self._volume)
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
                self._check_wifi_status(now)
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
                repository.increment_play_count(story.id)
                self._last_stat_time = time.monotonic()
                self._play_chime("known")

                if story.stream_url:
                    # A livestream has no tracks/position to resume - always join live.
                    self._player.load_playlist([story.stream_url])
                    self._player.set_volume(self._volume)
                    logger.info("streaming '%s' (uid=%s) from %s", story.title, uid, story.stream_url)
                    return

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

    def manual_set_volume(self, percent: int) -> None:
        with self._lock:
            self._set_volume_locked(percent)

    def _handle_volume_delta(self, direction: int) -> None:
        with self._lock:
            self._set_volume_locked(self._volume + direction * self._volume_step)

    def _set_volume_locked(self, percent: int) -> None:
        previous = self._volume
        self._volume = max(0, min(self._max_volume, percent))
        self._player.set_volume(self._volume)
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
                self._player.set_volume(self._volume)

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
            self._player.set_volume(chime_volume)
            feedback.play_chime(name, self._config.audio.alsa_device)
            self._player.set_volume(restore_to)

    # -- display brightness -----------------------------------------------------

    def manual_set_brightness(self, percent: int) -> None:
        with self._lock:
            self._brightness = max(self._min_brightness, min(self._max_brightness, percent))
            repository.set_setting("brightness", self._brightness)
            self._backlight.set_brightness(self._brightness)

    def _handle_brightness_delta(self, direction: int) -> None:
        with self._lock:
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
            self._player.set_volume(self._volume)

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
                self._player.set_volume(self._volume)
                return
            if self._sleep_fade_seconds > 0 and remaining <= self._sleep_fade_seconds:
                self._sleep_timer_fading = True
                faded = round(self._volume * (remaining / self._sleep_fade_seconds))
                self._player.set_volume(faded)
            else:
                self._restore_volume_after_fade_locked()

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
            max_volume = self._max_volume
            volume_step = self._volume_step
            chime_enabled = dict(self._chime_enabled)
            chime_volume_percent = self._chime_volume_percent
            sleep_timer_end = self._sleep_timer_end
            sleep_timer_minutes = self._sleep_timer_minutes
            auto_sleep_minutes = self._auto_sleep_minutes
            sleep_mode_active = self._sleep_mode_active
            brightness = self._brightness
            min_brightness = self._min_brightness
            max_brightness = self._max_brightness
            brightness_step = self._brightness_step
            wifi_enabled = self._wifi_enabled
            wifi_signal = self._wifi_signal
            hotspot_active = self._hotspot_active
            hotspot_ip = self._hotspot_ip
        status = self._player.get_status()

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
                "auto_sleep_minutes": auto_sleep_minutes,
                "chime_enabled": chime_enabled,
                "chime_volume_percent": chime_volume_percent,
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
        }
