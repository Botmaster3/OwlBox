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
