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


def test_removing_tag_pauses_and_saves_position(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    _make_story_with_file(config, "112233")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("112233")
        time.sleep(0.15)
        engine.simulate_remove()
        time.sleep(0.2)
        state = engine.get_state()
        assert state["uid"] is None
        assert state["player"]["playing"] is False
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
