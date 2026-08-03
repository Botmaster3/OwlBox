import time

from owlbox import repository
from owlbox.engine import Engine


def _make_story_with_file(config, uid, title="Story"):
    story = repository.create_story(title=title)
    story_dir = config.media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "track1.mp3").write_bytes(b"fake audio")
    repository.add_track(story.id, 0, "track1.mp3", None, None)
    repository.assign_uid(story.id, uid)
    return story


def test_scan_known_tag_starts_playback(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["id"] == story.id
        assert state["player"]["playing"] is True
    finally:
        engine.stop()


def test_scan_unknown_tag_is_logged_and_not_playing(config):
    config.rfid.poll_interval = 0.01

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("DEADBEEF")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"] is None
        assert state["unknown_tag"] == "DEADBEEF"
        assert repository.get_last_unknown_scan() == "DEADBEEF"
    finally:
        engine.stop()


def test_removing_tag_keeps_story_playing_and_saves_position(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    story = _make_story_with_file(config, "112233")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("112233")
        time.sleep(0.15)
        engine.simulate_remove()
        time.sleep(0.2)
        state = engine.get_state()
        # Lifting the figure off the reader no longer pauses playback - it keeps
        # going, and the kiosk keeps showing what's playing instead of reverting
        # to "no chip".
        assert state["uid"] == "112233"
        assert state["story"]["id"] == story.id
        assert state["player"]["playing"] is True

        # Placing the very same chip back is a no-op, not a reload/rewind.
        engine.simulate_scan("112233")
        time.sleep(0.15)
        assert engine.get_state()["player"]["time_pos"] == 0.0
    finally:
        engine.stop()


def test_removing_tag_then_scanning_a_different_story_switches(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    story_a = _make_story_with_file(config, "AAAA", title="Story A")
    story_b = _make_story_with_file(config, "BBBB", title="Story B")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AAAA")
        time.sleep(0.15)
        assert engine.get_state()["story"]["id"] == story_a.id

        engine.simulate_remove()
        time.sleep(0.2)
        assert engine.get_state()["story"]["id"] == story_a.id  # still playing

        engine.simulate_scan("BBBB")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["id"] == story_b.id
        assert state["uid"] == "BBBB"
    finally:
        engine.stop()


def test_parent_tag_activates_parent_mode_without_being_treated_as_unknown(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    repository.add_parent_tag("PARENTCARD", "Vater")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("PARENTCARD")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["parent_mode"] == {"active": True, "label": "Vater"}
        assert state["unknown_tag"] is None
        assert state["story"] is None
        assert state["function_tag"] is None

        engine.simulate_remove()
        time.sleep(0.15)
        assert engine.get_state()["parent_mode"] == {"active": False, "label": None}
    finally:
        engine.stop()


def test_manual_volume_change(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_volume(42)
        assert engine.get_state()["player"]["volume"] == 42
    finally:
        engine.stop()


def test_manual_seek_is_relative_and_does_not_change_track(config):
    config.rfid.poll_interval = 0.01
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["player"]["time_pos"] == 0.0

        # This is what holding the next/prev button drives (see GpioControls) -
        # a short tap still calls manual_next/manual_prev to change track, but
        # holding repeatedly calls this with a fixed step instead.
        engine.manual_seek(10)
        state = engine.get_state()
        assert state["player"]["time_pos"] == 10.0
        assert state["player"]["playlist_pos"] == 0

        engine.manual_seek(-100)
        assert engine.get_state()["player"]["time_pos"] == 0.0
    finally:
        engine.stop()


def test_function_tag_toggles_pause_without_being_treated_as_unknown(config):
    config.rfid.poll_interval = 0.01
    repository.set_function_tag("PAUSECARD", "toggle_pause")
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["player"]["playing"] is True

        engine.simulate_scan("PAUSECARD")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["player"]["playing"] is False
        assert state["function_tag"] == "toggle_pause"
        assert state["unknown_tag"] is None
        assert state["story"] is None
    finally:
        engine.stop()


def test_function_tag_next_advances_playlist(config):
    config.rfid.poll_interval = 0.01
    repository.set_function_tag("NEXTCARD", "next")
    story = repository.create_story(title="Multi")
    story_dir = config.media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "a.mp3").write_bytes(b"x")
    (story_dir / "b.mp3").write_bytes(b"x")
    repository.add_track(story.id, 0, "a.mp3", None, None)
    repository.add_track(story.id, 1, "b.mp3", None, None)
    repository.assign_uid(story.id, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["player"]["playlist_pos"] == 0

        engine.simulate_scan("NEXTCARD")
        time.sleep(0.15)
        assert engine.get_state()["player"]["playlist_pos"] == 1
    finally:
        engine.stop()


def test_state_lists_upcoming_tracks_after_current_one(config):
    config.rfid.poll_interval = 0.01
    story = repository.create_story(title="Multi")
    story_dir = config.media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("a.mp3", "b.mp3", "c.mp3"):
        (story_dir / filename).write_bytes(b"x")
    repository.add_track(story.id, 0, "a.mp3", "Erstes Kapitel", None)
    repository.add_track(story.id, 1, "b.mp3", "Zweites Kapitel", None)
    repository.add_track(story.id, 2, "c.mp3", "Drittes Kapitel", None)
    repository.assign_uid(story.id, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["track_title"] == "Erstes Kapitel"
        assert state["story"]["upcoming_tracks"] == ["Zweites Kapitel", "Drittes Kapitel"]

        engine.manual_next()
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["track_title"] == "Zweites Kapitel"
        assert state["story"]["upcoming_tracks"] == ["Drittes Kapitel"]
    finally:
        engine.stop()


def test_stop_persists_exact_position_even_before_next_autosave(config):
    # A large interval means the periodic autosave in the loop won't fire during
    # this test - stop() must still save the exact position on its own so a
    # clean shutdown/reboot doesn't lose progress made since the last autosave.
    config.rfid.poll_interval = 0.01
    config.playback.position_save_interval = 999
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.1)
        engine._player.seek(42.0)
    finally:
        engine.stop()

    _track_position, seek_seconds = repository.get_playback_state("AABBCC")
    assert seek_seconds == 42.0


def test_max_volume_clamps_current_and_future_changes(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_volume(90)
        assert engine.get_state()["player"]["volume"] == 90

        engine.set_max_volume(60)
        state = engine.get_state()
        assert state["player"]["volume"] == 60
        assert state["settings"]["max_volume"] == 60

        engine.manual_set_volume(100)
        assert engine.get_state()["player"]["volume"] == 60
    finally:
        engine.stop()
    assert repository.get_int_setting("max_volume", -1) == 60


def test_volume_step_setting_is_persisted_and_used(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.set_volume_step(10)
        assert engine.get_state()["settings"]["volume_step"] == 10

        engine.manual_set_volume(50)
        engine._handle_volume_delta(1)
        assert engine.get_state()["player"]["volume"] == 60
    finally:
        engine.stop()
    assert repository.get_int_setting("volume_step", -1) == 10


def test_sleep_timer_pauses_playback_when_it_expires(config):
    config.rfid.poll_interval = 0.05
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["player"]["playing"] is True

        engine.start_sleep_timer(0.01)  # ~0.6 seconds
        state = engine.get_state()
        assert state["sleep_timer"]["active"] is True

        time.sleep(1.0)
        state = engine.get_state()
        assert state["player"]["playing"] is False
        assert state["sleep_timer"]["active"] is False
    finally:
        engine.stop()


def test_cancel_sleep_timer(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.start_sleep_timer(5)
        assert engine.get_state()["sleep_timer"]["active"] is True
        engine.cancel_sleep_timer()
        assert engine.get_state()["sleep_timer"]["active"] is False
    finally:
        engine.stop()


def test_sleep_timer_function_tags_start_and_cancel(config):
    config.rfid.poll_interval = 0.01
    repository.set_function_tag("SLEEP30CARD", "sleep_timer_30")
    repository.set_function_tag("SLEEPCANCELCARD", "sleep_timer_cancel")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("SLEEP30CARD")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["sleep_timer"]["active"] is True
        assert state["sleep_timer"]["minutes"] == 30
        assert state["function_tag"] == "sleep_timer_30"

        engine.simulate_scan("SLEEPCANCELCARD")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["sleep_timer"]["active"] is False
        assert state["function_tag"] == "sleep_timer_cancel"
    finally:
        engine.stop()


def test_stream_tag_plays_url_without_track_resume(config):
    config.rfid.poll_interval = 0.01
    stream_story = repository.create_story(title="Radio Owl", stream_url="https://stream.example.com/radio.mp3")
    repository.assign_uid(stream_story.id, "RADIOCARD")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("RADIOCARD")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["id"] == stream_story.id
        assert state["story"]["is_stream"] is True
        assert state["story"]["track_title"] is None
        assert state["story"]["upcoming_tracks"] == []
        assert state["player"]["playing"] is True

        # Holding next/prev or seeking is a no-op while streaming, not a track
        # change/rewind - there's nothing to switch to or resume within a stream.
        engine.manual_next()
        engine.manual_prev()
        engine.manual_seek(30)
        assert engine.get_state()["player"]["playlist_pos"] == 0

        # Removing the chip shouldn't try to save/resume a position for a stream.
        engine.simulate_remove()
        time.sleep(0.2)
        assert repository.get_playback_state("RADIOCARD") == (0, 0.0)
    finally:
        engine.stop()


def test_playing_a_story_accumulates_listening_stats(config):
    config.rfid.poll_interval = 0.01
    config.playback.position_save_interval = 0.05
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.3)
        fetched = repository.get_story(story.id)
        assert fetched.play_count == 1
        assert fetched.total_seconds > 0
        assert fetched.last_played_at is not None

        # Pausing should stop the clock - total_seconds shouldn't keep climbing.
        engine.manual_pause()
        time.sleep(0.2)
        seconds_while_paused = repository.get_story(story.id).total_seconds
        time.sleep(0.2)
        assert repository.get_story(story.id).total_seconds == seconds_while_paused
    finally:
        engine.stop()


def test_switching_back_to_a_story_increments_play_count_again(config):
    config.rfid.poll_interval = 0.01
    story_a = _make_story_with_file(config, "AAAA", title="Story A")
    story_b = _make_story_with_file(config, "BBBB", title="Story B")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AAAA")
        time.sleep(0.1)
        assert repository.get_story(story_a.id).play_count == 1

        # A genuinely different chip counts as a new play...
        engine.simulate_scan("BBBB")
        time.sleep(0.1)
        assert repository.get_story(story_b.id).play_count == 1

        # ...and switching back to A again is a second play for A.
        engine.simulate_scan("AAAA")
        time.sleep(0.1)
        assert repository.get_story(story_a.id).play_count == 2
    finally:
        engine.stop()


def test_replacing_the_same_still_playing_chip_does_not_recount_as_a_new_play(config):
    # The chip-removed-keeps-playing feature makes the uid "sticky", so placing
    # the *same* chip back without ever registering a different one in between
    # is a no-op - it must not look like a second play.
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.1)
        engine.simulate_remove()
        time.sleep(0.2)
        engine.simulate_scan("AABBCC")
        time.sleep(0.1)
        assert repository.get_story(story.id).play_count == 1
    finally:
        engine.stop()


def test_livestream_play_counts_and_accumulates_listening_time_too(config):
    config.rfid.poll_interval = 0.01
    config.playback.position_save_interval = 0.05
    stream_story = repository.create_story(title="Radio Owl", stream_url="https://stream.example.com/radio.mp3")
    repository.assign_uid(stream_story.id, "RADIOCARD")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("RADIOCARD")
        time.sleep(0.3)
        fetched = repository.get_story(stream_story.id)
        assert fetched.play_count == 1
        assert fetched.total_seconds > 0
    finally:
        engine.stop()
