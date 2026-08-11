import subprocess
import time
from datetime import datetime

import pytest

from owlbox import engine as engine_module
from owlbox import feedback, network, repository, system_info, themes
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


def test_chime_plays_on_known_unknown_and_function_tag_scans(config):
    config.rfid.poll_interval = 0.01
    _make_story_with_file(config, "AABBCC")
    repository.set_function_tag("VOLUPCARD", "volume_up")

    calls = []
    original = feedback.play_chime
    feedback.play_chime = lambda name, alsa_device: calls.append(name)

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        engine.simulate_remove()
        time.sleep(0.15)

        engine.simulate_scan("DEADBEEF")
        time.sleep(0.15)
        engine.simulate_remove()
        time.sleep(0.15)

        engine.simulate_scan("VOLUPCARD")
        time.sleep(0.15)

        assert calls == ["startup", "known", "unknown", "function"]
    finally:
        engine.stop()
        feedback.play_chime = original


def test_chime_plays_at_fixed_fraction_of_max_volume_then_restores(config):
    config.audio.chime_volume_ratio = 0.15
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.set_max_volume(80)
    engine.manual_set_volume(50)

    observed_during_chime = []
    original = feedback.play_chime

    def fake_play_chime(name, alsa_device):
        observed_during_chime.append(engine.get_state()["player"]["volume"])

    feedback.play_chime = fake_play_chime
    try:
        engine._play_chime("known")
        assert observed_during_chime == [12]  # round(80 * 0.15)
        assert engine.get_state()["player"]["volume"] == 50  # restored afterwards
    finally:
        feedback.play_chime = original


def test_chime_volume_restores_even_if_playback_raises(config):
    # Confirmed on real hardware: the hardware ALSA mixer was found stuck at
    # the quiet chime level after a staged bring-up's rapid-fire systemctl
    # restart/stop cycles - a SIGTERM arriving while _play_chime_at() was
    # still blocked inside feedback.play_chime() skipped the restore that
    # used to be a bare statement after it. This simulates the same "the
    # chime call never returns normally" shape with an exception (can't
    # send a real SIGTERM to this test process safely) and checks the
    # try/finally actually restores the volume anyway - the reason this
    # test would have failed before the fix.
    _make_story_with_file(config, "AABBCC")
    engine = Engine(config)
    engine.set_max_volume(80)
    engine.manual_set_volume(50)

    original = feedback.play_chime
    feedback.play_chime = lambda name, alsa_device: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        try:
            engine._play_chime("known")
        except RuntimeError:
            pass
        assert engine.get_state()["player"]["volume"] == 50  # restored despite the exception
    finally:
        feedback.play_chime = original


def test_chime_plays_on_startup(config):
    calls = []
    original = feedback.play_chime
    feedback.play_chime = lambda name, alsa_device: calls.append(name)

    engine = Engine(config)
    engine.start()
    try:
        assert calls == ["startup"]
    finally:
        engine.stop()
        feedback.play_chime = original


def test_chime_plays_on_shutdown_and_restart_requests(config):
    calls = []
    original = feedback.play_chime
    feedback.play_chime = lambda name, alsa_device: calls.append(name)

    engine = Engine(config)
    engine.start()
    try:
        calls.clear()  # drop the startup chime, only interested in shutdown/restart here

        original_run = subprocess.run
        subprocess.run = lambda *a, **k: None
        try:
            engine.request_shutdown()
            engine.request_restart()
        finally:
            subprocess.run = original_run

        assert calls == ["shutdown", "shutdown"]
    finally:
        engine.stop()
        feedback.play_chime = original


def test_chime_type_disabled_suppresses_only_that_type(config):
    config.rfid.poll_interval = 0.01
    repository.set_function_tag("VOLUPCARD", "volume_up")
    _make_story_with_file(config, "AABBCC")

    calls = []
    original = feedback.play_chime
    feedback.play_chime = lambda name, alsa_device: calls.append(name)

    engine = Engine(config)
    engine.set_chime_type_enabled("known", False)
    assert engine.get_state()["settings"]["chime_enabled"]["known"] is False
    assert engine.get_state()["settings"]["chime_enabled"]["function"] is True
    engine.start()
    try:
        calls.clear()  # drop the startup chime, only interested in scan behaviour here
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert calls == []  # "known" muted

        engine.simulate_remove()
        time.sleep(0.15)
        engine.simulate_scan("VOLUPCARD")
        time.sleep(0.15)
        assert calls == ["function"]  # other types unaffected
    finally:
        engine.stop()
        feedback.play_chime = original
    assert repository.get_int_setting("chime_enabled_known", -1) == 0


def test_set_chime_volume_percent_is_persisted(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.set_chime_volume_percent(42)
        assert engine.get_state()["settings"]["chime_volume_percent"] == 42
    finally:
        engine.stop()
    assert repository.get_int_setting("chime_volume_percent", -1) == 42


def test_test_chime_plays_even_when_type_disabled(config):
    calls = []
    original = feedback.play_chime
    feedback.play_chime = lambda name, alsa_device: calls.append(name)

    engine = Engine(config)
    engine.set_chime_type_enabled("known", False)
    try:
        engine.test_chime("known")
        assert calls == ["known"]
    finally:
        feedback.play_chime = original


def test_test_chime_uses_override_percent_not_saved_setting(config):
    engine = Engine(config)
    engine.set_max_volume(80)
    engine.set_chime_volume_percent(15)
    engine.manual_set_volume(50)

    observed_during_chime = []
    original = feedback.play_chime

    def fake_play_chime(name, alsa_device):
        observed_during_chime.append(engine.get_state()["player"]["volume"])

    feedback.play_chime = fake_play_chime
    try:
        engine.test_chime("known", volume_percent=25)
        assert observed_during_chime == [20]  # round(80 * 0.25), not the saved 15%
        assert engine.get_state()["player"]["volume"] == 50  # restored afterwards
    finally:
        feedback.play_chime = original


def test_test_chime_falls_back_to_saved_percent_when_no_override(config):
    engine = Engine(config)
    engine.set_max_volume(80)
    engine.set_chime_volume_percent(15)

    observed_during_chime = []
    original = feedback.play_chime

    def fake_play_chime(name, alsa_device):
        observed_during_chime.append(engine.get_state()["player"]["volume"])

    feedback.play_chime = fake_play_chime
    try:
        engine.test_chime("known")
        assert observed_during_chime == [12]  # round(80 * 0.15)
    finally:
        feedback.play_chime = original


def test_test_chime_ignores_unknown_name(config):
    calls = []
    original = feedback.play_chime
    feedback.play_chime = lambda name, alsa_device: calls.append(name)

    engine = Engine(config)
    try:
        engine.test_chime("not-a-real-chime")
        assert calls == []
    finally:
        feedback.play_chime = original


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


def test_scanning_a_story_applies_its_saved_repeat_mode(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")
    repository.update_story_flags(story.id, repeat="track")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine._player._repeat_mode == "track"
    finally:
        engine.stop()


def test_scanning_a_story_with_no_repeat_set_leaves_playback_unlooped(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine._player._repeat_mode == "off"
    finally:
        engine.stop()


def test_set_story_repeat_applies_live_to_the_currently_playing_story(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine._player._repeat_mode == "off"

        assert engine.set_story_repeat(story.id, "folder") is True
        assert engine._player._repeat_mode == "folder"
        assert repository.get_story(story.id).repeat == "folder"
    finally:
        engine.stop()


def test_set_story_repeat_does_not_disturb_a_different_playing_story(config):
    config.rfid.poll_interval = 0.01
    story_a = _make_story_with_file(config, "AAAA", title="Story A")
    story_b = _make_story_with_file(config, "BBBB", title="Story B")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AAAA")
        time.sleep(0.15)

        assert engine.set_story_repeat(story_b.id, "track") is True
        # Story A is the one actually loaded in the player right now - its
        # live repeat mode must stay untouched by a change aimed at B.
        assert engine._player._repeat_mode == "off"
        assert repository.get_story(story_b.id).repeat == "track"
        assert repository.get_story(story_a.id).repeat == "off"
    finally:
        engine.stop()


def test_set_story_repeat_rejects_invalid_mode(config):
    story = repository.create_story(title="Story")
    engine = Engine(config)
    assert engine.set_story_repeat(story.id, "loop-forever") is False
    assert repository.get_story(story.id).repeat == "off"


def test_scanning_a_shuffled_story_applies_shuffle_and_skips_saved_position(config):
    config.rfid.poll_interval = 0.01
    story = repository.create_story(title="Story")
    story_dir = config.media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        (story_dir / f"track{i}.mp3").write_bytes(b"fake audio")
        repository.add_track(story.id, i, f"track{i}.mp3", None, None)
    repository.assign_uid(story.id, "AABBCC")
    repository.update_story_flags(story.id, shuffle=True)
    # A valid, in-bounds resume position - not merely out of range, which
    # would already reset to 0 regardless of shuffle (see the existing
    # bounds check in Engine._handle_tag_present) and so wouldn't actually
    # prove the shuffle-specific behavior this test is for.
    repository.save_playback_state("AABBCC", 2, 42.0)

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine._player._shuffle_enabled is True
        # A resume position saved under the old (unshuffled) track order is
        # meaningless once shuffle reorders things - starts fresh instead.
        state = engine.get_state()
        assert state["player"]["playlist_pos"] == 0
        assert state["player"]["time_pos"] == 0.0
    finally:
        engine.stop()


def test_set_story_shuffle_applies_live_to_the_currently_playing_story(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine._player._shuffle_enabled is False

        engine.set_story_shuffle(story.id, True)
        assert engine._player._shuffle_enabled is True
        assert repository.get_story(story.id).shuffle is True
        assert engine.get_state()["story"]["shuffle"] is True
    finally:
        engine.stop()


def test_set_story_shuffle_does_not_disturb_a_different_playing_story(config):
    config.rfid.poll_interval = 0.01
    story_a = _make_story_with_file(config, "AAAA", title="Story A")
    story_b = _make_story_with_file(config, "BBBB", title="Story B")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AAAA")
        time.sleep(0.15)

        engine.set_story_shuffle(story_b.id, True)
        assert engine._player._shuffle_enabled is False
        assert repository.get_story(story_b.id).shuffle is True
        assert repository.get_story(story_a.id).shuffle is False
    finally:
        engine.stop()


def test_state_exposes_repeat_and_shuffle_for_the_current_story(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")
    repository.update_story_flags(story.id, shuffle=True, repeat="folder")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["shuffle"] is True
        assert state["story"]["repeat"] == "folder"
    finally:
        engine.stop()


def test_shuffle_function_tag_toggles_on_then_off_across_two_placements(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    story = _make_story_with_file(config, "AABBCC")
    repository.set_function_tag("SHUFFLECARD", "shuffle_toggle")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine._player._shuffle_enabled is False

        # Swap the story chip for the function card, as you would physically -
        # only one chip fits on the reader at a time.
        engine.simulate_scan("SHUFFLECARD")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"] is None
        assert state["function_tag"] == "shuffle_toggle"
        assert engine._player._shuffle_enabled is True
        assert repository.get_story(story.id).shuffle is True

        # Lifting and placing the same card again is a second, independent
        # scan (uid goes back to None in between) - it should flip shuffle
        # back off rather than leaving it stuck on.
        engine.simulate_remove()
        time.sleep(0.15)
        engine.simulate_scan("SHUFFLECARD")
        time.sleep(0.15)
        assert engine._player._shuffle_enabled is False
        assert repository.get_story(story.id).shuffle is False
    finally:
        engine.stop()


def test_repeat_function_tag_toggles_on_then_off_across_two_placements(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    story = _make_story_with_file(config, "AABBCC")
    repository.set_function_tag("REPEATTRACKCARD", "repeat_track_toggle")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)

        engine.simulate_scan("REPEATTRACKCARD")
        time.sleep(0.15)
        assert engine._player._repeat_mode == "track"
        assert repository.get_story(story.id).repeat == "track"

        engine.simulate_remove()
        time.sleep(0.15)
        engine.simulate_scan("REPEATTRACKCARD")
        time.sleep(0.15)
        assert engine._player._repeat_mode == "off"
        assert repository.get_story(story.id).repeat == "off"
    finally:
        engine.stop()


def test_repeat_function_tag_switches_modes_instead_of_turning_off_a_different_active_mode(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    story = _make_story_with_file(config, "AABBCC")
    repository.set_function_tag("REPEATFOLDERCARD", "repeat_folder_toggle")
    repository.update_story_flags(story.id, repeat="track")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine._player._repeat_mode == "track"

        # Placing the "Ordner" card while "Track" is active should switch to
        # folder mode outright, not turn repeat off.
        engine.simulate_scan("REPEATFOLDERCARD")
        time.sleep(0.15)
        assert engine._player._repeat_mode == "folder"
        assert repository.get_story(story.id).repeat == "folder"
    finally:
        engine.stop()


def test_shuffle_function_tag_is_a_no_op_when_no_story_has_ever_been_loaded(config):
    config.rfid.poll_interval = 0.01
    repository.set_function_tag("SHUFFLECARD", "shuffle_toggle")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("SHUFFLECARD")
        time.sleep(0.15)
        assert engine._player._shuffle_enabled is False
    finally:
        engine.stop()


def test_shuffle_and_repeat_function_tags_do_not_affect_a_livestream(config):
    config.rfid.poll_interval = 0.01
    story = repository.create_story(title="Radio", stream_url="http://example.com/stream")
    repository.assign_uid(story.id, "STREAMCARD")
    repository.set_function_tag("SHUFFLECARD", "shuffle_toggle")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("STREAMCARD")
        time.sleep(0.15)

        engine.simulate_scan("SHUFFLECARD")
        time.sleep(0.15)
        assert engine._player._shuffle_enabled is False
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


def test_manual_seek_to_jumps_to_an_absolute_position(config):
    config.rfid.poll_interval = 0.01
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)

        # This is what clicking the progress bar drives (see admin_dashboard.js) -
        # an absolute position, unlike the relative manual_seek used by holding
        # next/prev.
        engine.manual_seek_to(42)
        assert engine.get_state()["player"]["time_pos"] == 42.0

        engine.manual_seek_to(5)
        assert engine.get_state()["player"]["time_pos"] == 5.0

        engine.manual_seek_to(-10)
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


def test_state_lists_full_tracklist_with_current_index(config):
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
        assert state["story"]["tracks"] == ["Erstes Kapitel", "Zweites Kapitel", "Drittes Kapitel"]
        assert state["story"]["current_track_index"] == 0

        engine.manual_next()
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["track_title"] == "Zweites Kapitel"
        assert state["story"]["tracks"] == ["Erstes Kapitel", "Zweites Kapitel", "Drittes Kapitel"]
        assert state["story"]["current_track_index"] == 1

        # Still lists everything on the last track too, not just "what's left".
        engine.manual_next()
        time.sleep(0.15)
        state = engine.get_state()
        assert state["story"]["current_track_index"] == 2
        assert state["story"]["tracks"] == ["Erstes Kapitel", "Zweites Kapitel", "Drittes Kapitel"]
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


def test_volume_zero_pauses_and_raising_it_again_resumes(config):
    config.rfid.poll_interval = 0.01
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.1)
        engine.manual_set_volume(50)
        assert engine.get_state()["player"]["playing"] is True

        engine.manual_set_volume(0)
        assert engine.get_state()["player"]["playing"] is False

        # Volume already at 0 - no-op, must not un-pause on its own.
        engine._handle_volume_delta(-1)
        assert engine.get_state()["player"]["playing"] is False

        engine.manual_set_volume(30)
        assert engine.get_state()["player"]["playing"] is True

        # Same again, but driven by the encoder delta instead of an absolute set.
        engine.manual_set_volume(0)
        assert engine.get_state()["player"]["playing"] is False
        engine._handle_volume_delta(1)
        assert engine.get_state()["player"]["playing"] is True
    finally:
        engine.stop()


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


def test_volume_survives_a_service_restart(config):
    # Confirmed on real hardware: every restart of owlbox.service (e.g. each
    # `owlbox-stage <name>` step during the staged bring-up, or just a normal
    # reboot) used to silently reset playback volume back to
    # config.audio.default_volume, discarding whatever had actually been set
    # - a manually-set 80% dropped to the 60% config default the moment the
    # service next started. Constructing a second Engine against the same
    # database (same tmp_path-backed config, same pattern as
    # test_max_volume_clamps_current_and_future_changes/
    # test_volume_step_setting_is_persisted_and_used above) simulates exactly
    # that restart.
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_volume(80)
        assert engine.get_state()["player"]["volume"] == 80
    finally:
        engine.stop()
    assert repository.get_int_setting("volume", -1) == 80

    restarted = Engine(config)
    assert restarted._volume == 80
    restarted.start()
    try:
        assert restarted.get_state()["player"]["volume"] == 80
    finally:
        restarted.stop()


def test_fresh_install_with_no_saved_volume_falls_back_to_config_default(config):
    config.audio.default_volume = 42
    engine = Engine(config)
    assert engine._volume == 42


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


def test_sleep_timer_fades_volume_before_pausing(config):
    config.rfid.poll_interval = 0.05
    config.playback.sleep_fade_seconds = 0.3
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        engine.manual_set_volume(80)

        engine.start_sleep_timer(0.02)  # ~1.2 seconds total, 0.3s fade window

        time.sleep(0.3)
        state = engine.get_state()
        assert state["player"]["playing"] is True
        assert state["player"]["volume"] >= 70  # still outside the fade window

        time.sleep(0.7)  # now ~1.0s elapsed, inside the fade window
        state = engine.get_state()
        assert state["player"]["playing"] is True
        assert state["player"]["volume"] < 70

        time.sleep(0.6)  # past the ~1.2s expiry
        state = engine.get_state()
        assert state["player"]["playing"] is False
        assert state["player"]["volume"] == 80  # restored, not stuck faded
    finally:
        engine.stop()


def test_cancelling_sleep_timer_mid_fade_restores_volume(config):
    config.rfid.poll_interval = 0.05
    config.playback.sleep_fade_seconds = 5
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        engine.manual_set_volume(80)

        engine.start_sleep_timer(0.02)  # ~1.2 seconds, entirely inside the 5s fade window
        time.sleep(0.3)
        assert engine.get_state()["player"]["volume"] < 80

        engine.cancel_sleep_timer()
        assert engine.get_state()["player"]["volume"] == 80
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


def test_auto_sleep_activates_when_paused_and_wakes_on_toggle_pause(config):
    config.rfid.poll_interval = 0.05
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine._auto_sleep_minutes = 0.01  # ~0.6 seconds, for a fast test
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["player"]["playing"] is True

        engine.manual_pause()
        assert engine.get_state()["auto_sleep"]["active"] is False

        time.sleep(1.0)
        assert engine.get_state()["auto_sleep"]["active"] is True

        engine.manual_toggle_pause()
        state = engine.get_state()
        assert state["auto_sleep"]["active"] is False
        assert state["player"]["playing"] is True
    finally:
        engine.stop()


def test_auto_sleep_wakes_on_volume_increase_even_without_mute(config):
    config.rfid.poll_interval = 0.05
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine._auto_sleep_minutes = 0.01
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        engine.manual_set_volume(50)
        engine.manual_pause()
        time.sleep(1.0)
        assert engine.get_state()["auto_sleep"]["active"] is True

        # Wakes even though it never hit 0/mute - any increase while asleep counts.
        engine.manual_set_volume(60)
        state = engine.get_state()
        assert state["auto_sleep"]["active"] is False
        assert state["player"]["playing"] is True
    finally:
        engine.stop()


def test_auto_sleep_wakes_on_tag_rescan(config):
    config.rfid.poll_interval = 0.05
    config.rfid.missing_reads_to_remove = 1
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine._auto_sleep_minutes = 0.01
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        engine.manual_pause()
        time.sleep(1.0)
        assert engine.get_state()["auto_sleep"]["active"] is True

        engine.simulate_remove()
        time.sleep(0.15)
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)

        state = engine.get_state()
        assert state["auto_sleep"]["active"] is False
        assert state["player"]["playing"] is True
    finally:
        engine.stop()


def test_auto_sleep_disabled_when_minutes_is_zero(config):
    config.rfid.poll_interval = 0.05
    _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine._auto_sleep_minutes = 0
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        engine.manual_pause()
        time.sleep(1.0)
        assert engine.get_state()["auto_sleep"]["active"] is False
    finally:
        engine.stop()


def test_set_auto_sleep_minutes_is_persisted(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.set_auto_sleep_minutes(15)
        assert engine.get_state()["settings"]["auto_sleep_minutes"] == 15
    finally:
        engine.stop()
    assert repository.get_int_setting("auto_sleep_minutes", -1) == 15


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
        assert state["story"]["tracks"] == []
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


def test_manual_set_brightness_is_persisted_and_reflected_in_state(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_brightness(42)
        assert engine.get_state()["settings"]["brightness"] == 42
        assert repository.get_int_setting("brightness", -1) == 42
    finally:
        engine.stop()


def test_brightness_encoder_delta_adjusts_and_clamps_brightness(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_brightness(50)
        engine._handle_brightness_delta(1)
        assert engine.get_state()["settings"]["brightness"] == 50 + config.gpio.brightness_step
        assert repository.get_int_setting("brightness", -1) == 50 + config.gpio.brightness_step

        engine.manual_set_brightness(0)
        engine._handle_brightness_delta(-1)
        assert engine.get_state()["settings"]["brightness"] == 0

        engine.manual_set_brightness(100)
        engine._handle_brightness_delta(1)
        assert engine.get_state()["settings"]["brightness"] == 100
    finally:
        engine.stop()


def test_brightness_step_setting_is_persisted_and_used(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.set_brightness_step(15)
        assert engine.get_state()["settings"]["brightness_step"] == 15

        engine.manual_set_brightness(50)
        engine._handle_brightness_delta(1)
        assert engine.get_state()["settings"]["brightness"] == 65
    finally:
        engine.stop()
    assert repository.get_int_setting("brightness_step", -1) == 15


def test_brightness_range_clamps_current_and_future_changes(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_brightness(90)
        assert engine.get_state()["settings"]["brightness"] == 90

        engine.set_max_brightness(60)
        state = engine.get_state()
        assert state["settings"]["brightness"] == 60
        assert state["settings"]["max_brightness"] == 60

        engine.manual_set_brightness(100)
        assert engine.get_state()["settings"]["brightness"] == 60

        engine.set_min_brightness(20)
        engine.manual_set_brightness(0)
        state = engine.get_state()
        assert state["settings"]["brightness"] == 20
        assert state["settings"]["min_brightness"] == 20

        # min/max can't cross - each setter pushes the other out of the way.
        engine.set_min_brightness(90)
        assert engine.get_state()["settings"]["max_brightness"] == 91
    finally:
        engine.stop()
    assert repository.get_int_setting("max_brightness", -1) == 91
    assert repository.get_int_setting("min_brightness", -1) == 90


def test_toggle_night_mode_dims_and_restores_brightness(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.set_night_brightness(7)
        engine.manual_set_brightness(80)

        engine.toggle_night_mode()
        state = engine.get_state()["settings"]
        assert state["night_mode_active"] is True
        assert state["brightness"] == 7

        engine.toggle_night_mode()
        state = engine.get_state()["settings"]
        assert state["night_mode_active"] is False
        assert state["brightness"] == 80
    finally:
        engine.stop()
    # The live brightness (back to day level) is what's persisted, not the
    # night level - a restart should come back up showing what it looked
    # like before night mode, not still dimmed.
    assert repository.get_int_setting("brightness", -1) == 80


def test_night_mode_bypasses_min_max_brightness_bounds(config):
    # Night mode is a deliberate override, independent of the day-time
    # min/max_brightness range - it must be able to go dimmer than the
    # configured daytime minimum, that's the whole point.
    engine = Engine(config)
    engine.start()
    try:
        engine.set_min_brightness(30)
        engine.set_night_brightness(5)
        engine.manual_set_brightness(50)

        engine.toggle_night_mode()
        assert engine.get_state()["settings"]["brightness"] == 5
    finally:
        engine.stop()


def test_set_night_mode_active_is_idempotent_and_explicit(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_brightness(80)
        engine.set_night_brightness(10)

        engine.set_night_mode_active(True)
        assert engine.get_state()["settings"]["night_mode_active"] is True
        assert engine.get_state()["settings"]["brightness"] == 10

        # Setting it to the same state again must be a no-op, not a second
        # "remember current brightness as day brightness" - the point of
        # set_night_mode_active (vs. toggle_night_mode) is landing on an
        # exact requested state safely from something like a web checkbox.
        engine.set_night_mode_active(True)
        assert engine.get_state()["settings"]["brightness"] == 10

        engine.set_night_mode_active(False)
        assert engine.get_state()["settings"]["night_mode_active"] is False
        assert engine.get_state()["settings"]["brightness"] == 80
    finally:
        engine.stop()


def test_set_night_brightness_applies_live_while_night_mode_is_active(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.set_night_brightness(5)
        engine.toggle_night_mode()
        assert engine.get_state()["settings"]["brightness"] == 5

        # Changing the configured night level while already dimmed should
        # take effect immediately, not just the next time night mode starts.
        engine.set_night_brightness(15)
        assert engine.get_state()["settings"]["night_brightness"] == 15
        assert engine.get_state()["settings"]["brightness"] == 15
    finally:
        engine.stop()
    assert repository.get_int_setting("night_brightness", -1) == 15


def test_night_mode_does_not_survive_a_restart(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.toggle_night_mode()
        assert engine.get_state()["settings"]["night_mode_active"] is True
    finally:
        engine.stop()

    engine2 = Engine(config)
    engine2.start()
    try:
        assert engine2.get_state()["settings"]["night_mode_active"] is False
    finally:
        engine2.stop()


def test_manual_brightness_change_while_in_night_mode_exits_it_cleanly(config):
    # A direct brightness set (slider, or turning the same encoder night mode's
    # switch lives on) while dimmed must mean "I want exactly this now" - not
    # silently stay flagged as night mode underneath it, which would make the
    # next button press throw the just-picked value away and jump back to the
    # stale remembered "day" brightness instead.
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_brightness(80)
        engine.toggle_night_mode()
        assert engine.get_state()["settings"]["night_mode_active"] is True

        engine.manual_set_brightness(45)
        state = engine.get_state()["settings"]
        assert state["night_mode_active"] is False
        assert state["brightness"] == 45

        # The remembered day brightness must be gone too - toggling back on
        # now starts a fresh night/day cycle from this new brightness, not
        # from the 80 set before the first toggle.
        engine.toggle_night_mode()
        assert engine.get_state()["settings"]["brightness"] == engine.get_state()["settings"]["night_brightness"]
        engine.toggle_night_mode()
        assert engine.get_state()["settings"]["brightness"] == 45
    finally:
        engine.stop()


def test_brightness_delta_while_in_night_mode_exits_it_cleanly(config):
    engine = Engine(config)
    engine.start()
    try:
        engine.manual_set_brightness(80)
        engine.toggle_night_mode()
        assert engine.get_state()["settings"]["night_mode_active"] is True

        engine._handle_brightness_delta(1)
        assert engine.get_state()["settings"]["night_mode_active"] is False
    finally:
        engine.stop()


def test_state_includes_cached_wifi_status(config):
    config.rfid.poll_interval = 0.01
    engine = Engine(config)
    engine.start()
    try:
        time.sleep(0.1)
        wifi = engine.get_state()["wifi"]
        assert "enabled" in wifi
        assert "signal" in wifi
    finally:
        engine.stop()


def test_wifi_status_check_is_throttled(config):
    engine = Engine(config)
    calls = []
    original = network.get_status
    network.get_status = lambda: calls.append(1) or original()
    try:
        engine._check_wifi_status(100.0, interval=5.0)
        engine._check_wifi_status(101.0, interval=5.0)
        engine._check_wifi_status(104.9, interval=5.0)
        assert len(calls) == 1

        engine._check_wifi_status(105.1, interval=5.0)
        assert len(calls) == 2
    finally:
        network.get_status = original


def test_hotspot_starts_after_prolonged_disconnection(config):
    config.network.hotspot_after_seconds = 30
    engine = Engine(config)

    start_calls = []
    original_start = network.start_hotspot
    original_get_ip = network.get_hotspot_ip
    network.start_hotspot = lambda ssid, password: start_calls.append((ssid, password)) or True
    network.get_hotspot_ip = lambda: "10.42.0.1"
    try:
        disconnected = {"enabled": True, "connected_ssid": None, "ip_address": None, "signal": None}

        engine._check_wifi_fallback(0.0, disconnected)
        assert start_calls == []
        assert engine.get_state()["wifi"]["hotspot_active"] is False

        engine._check_wifi_fallback(29.0, disconnected)
        assert start_calls == []

        engine._check_wifi_fallback(30.1, disconnected)
        assert start_calls == [(config.network.hotspot_ssid, config.network.hotspot_password)]
        state = engine.get_state()["wifi"]
        assert state["hotspot_active"] is True
        assert state["hotspot_ssid"] == config.network.hotspot_ssid
        assert state["hotspot_password"] == config.network.hotspot_password
        assert state["hotspot_ip"] == "10.42.0.1"

        # Already active - must not call start_hotspot again.
        engine._check_wifi_fallback(31.0, disconnected)
        assert len(start_calls) == 1
    finally:
        network.start_hotspot = original_start
        network.get_hotspot_ip = original_get_ip


def test_hotspot_stops_once_wifi_reconnects(config):
    config.network.hotspot_after_seconds = 10
    engine = Engine(config)

    stop_calls = []
    original_start = network.start_hotspot
    original_stop = network.stop_hotspot
    original_get_ip = network.get_hotspot_ip
    network.start_hotspot = lambda ssid, password: True
    network.stop_hotspot = lambda: stop_calls.append(1)
    network.get_hotspot_ip = lambda: "10.42.0.1"
    try:
        disconnected = {"enabled": True, "connected_ssid": None, "ip_address": None, "signal": None}
        engine._check_wifi_fallback(0.0, disconnected)
        engine._check_wifi_fallback(11.0, disconnected)
        assert engine.get_state()["wifi"]["hotspot_active"] is True

        connected = {"enabled": True, "connected_ssid": "HomeWifi", "ip_address": "192.168.1.5", "signal": 80}
        engine._check_wifi_fallback(12.0, connected)
        assert stop_calls == [1]
        assert engine.get_state()["wifi"]["hotspot_active"] is False
    finally:
        network.start_hotspot = original_start
        network.stop_hotspot = original_stop
        network.get_hotspot_ip = original_get_ip


def test_hotspot_periodic_retry_reconnects_and_stops(config):
    config.network.hotspot_after_seconds = 10
    config.network.hotspot_retry_interval_seconds = 20
    engine = Engine(config)

    stop_calls = []
    retry_calls = []
    original_start = network.start_hotspot
    original_stop = network.stop_hotspot
    original_get_ip = network.get_hotspot_ip
    original_retry = network.try_reconnect_known_networks
    network.start_hotspot = lambda ssid, password: True
    network.stop_hotspot = lambda: stop_calls.append(1)
    network.get_hotspot_ip = lambda: "10.42.0.1"
    network.try_reconnect_known_networks = lambda: retry_calls.append(1) or True
    try:
        disconnected = {"enabled": True, "connected_ssid": None, "ip_address": None, "signal": None}
        engine._check_wifi_fallback(0.0, disconnected)
        engine._check_wifi_fallback(11.0, disconnected)
        assert engine.get_state()["wifi"]["hotspot_active"] is True

        # Too soon for a retry - must not call try_reconnect_known_networks yet.
        engine._check_wifi_fallback(20.0, disconnected)
        assert retry_calls == []

        engine._check_wifi_fallback(31.5, disconnected)
        assert retry_calls == [1]
        assert stop_calls == [1]
        assert engine.get_state()["wifi"]["hotspot_active"] is False
    finally:
        network.start_hotspot = original_start
        network.stop_hotspot = original_stop
        network.get_hotspot_ip = original_get_ip
        network.try_reconnect_known_networks = original_retry


def test_hotspot_stops_if_wifi_explicitly_disabled(config):
    config.network.hotspot_after_seconds = 10
    engine = Engine(config)

    stop_calls = []
    original_start = network.start_hotspot
    original_stop = network.stop_hotspot
    original_get_ip = network.get_hotspot_ip
    network.start_hotspot = lambda ssid, password: True
    network.stop_hotspot = lambda: stop_calls.append(1)
    network.get_hotspot_ip = lambda: "10.42.0.1"
    try:
        disconnected = {"enabled": True, "connected_ssid": None, "ip_address": None, "signal": None}
        engine._check_wifi_fallback(0.0, disconnected)
        engine._check_wifi_fallback(11.0, disconnected)
        assert engine.get_state()["wifi"]["hotspot_active"] is True

        radio_off = {"enabled": False, "connected_ssid": None, "ip_address": None, "signal": None}
        engine._check_wifi_fallback(12.0, radio_off)
        assert stop_calls == [1]
        assert engine.get_state()["wifi"]["hotspot_active"] is False
    finally:
        network.start_hotspot = original_start
        network.stop_hotspot = original_stop
        network.get_hotspot_ip = original_get_ip


def test_theme_defaults_to_waldnacht(config):
    # Auto-theme is on by default (see below) - pin "no auto theme active" so
    # this test's result doesn't depend on which day it happens to run on.
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: None
    try:
        engine = Engine(config)
        assert engine.get_theme() == "waldnacht"
        assert engine.get_state()["settings"]["theme"] == "waldnacht"
    finally:
        themes.get_auto_theme = original


def test_set_theme_is_persisted(config):
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: None
    try:
        engine = Engine(config)
        assert engine.set_theme("mondschein") is True
        assert engine.get_theme() == "mondschein"
        assert engine.get_state()["settings"]["theme"] == "mondschein"
        assert repository.get_setting("theme") == "mondschein"

        # A freshly constructed engine reads the persisted choice back on boot.
        engine2 = Engine(config)
        assert engine2.get_theme() == "mondschein"
    finally:
        themes.get_auto_theme = original


def test_set_theme_rejects_unknown_name(config):
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: None
    try:
        engine = Engine(config)
        assert engine.set_theme("not-a-real-theme") is False
        assert engine.get_theme() == themes.DEFAULT_THEME
    finally:
        themes.get_auto_theme = original


def test_set_theme_falls_back_to_default_for_corrupted_setting(config):
    repository.set_setting("theme", "not-a-real-theme")
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: None
    try:
        engine = Engine(config)
        assert engine.get_theme() == themes.DEFAULT_THEME
    finally:
        themes.get_auto_theme = original


def test_auto_theme_enabled_defaults_to_on_for_every_auto_themeable_theme(config):
    engine = Engine(config)
    enabled = engine.get_state()["settings"]["auto_theme_enabled"]
    assert set(enabled.keys()) == set(themes.auto_themeable_ids())
    assert all(enabled.values())


def test_get_theme_prefers_auto_theme_when_in_season(config):
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: "weihnachten"
    try:
        engine = Engine(config)
        assert engine.get_theme() == "weihnachten"
        assert engine.get_manual_theme() == "waldnacht"
        state = engine.get_state()["settings"]
        assert state["theme"] == "weihnachten"
        assert state["manual_theme"] == "waldnacht"
        assert state["seasonal_theme_active"] == "weihnachten"
    finally:
        themes.get_auto_theme = original


def test_get_theme_falls_back_to_manual_theme_outside_any_season(config):
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: None
    try:
        engine = Engine(config)
        assert engine.get_theme() == "waldnacht"
        assert engine.get_state()["settings"]["seasonal_theme_active"] is None
    finally:
        themes.get_auto_theme = original


def test_get_theme_ignores_a_theme_once_its_own_toggle_is_off(config):
    # A fake that actually consults the enabled-map passed in, so this test
    # exercises the real wiring (Engine passing its own _auto_theme_enabled
    # through) rather than just asserting on a canned return value.
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: ("winter" if enabled.get("winter", True) else None)
    try:
        engine = Engine(config)
        assert engine.get_theme() == "winter"
        assert engine.set_auto_theme_enabled("winter", False) is True
        assert engine.get_theme() == "waldnacht"
        assert engine.get_seasonal_theme_active() is None
    finally:
        themes.get_auto_theme = original


def test_set_theme_disables_only_the_currently_active_auto_theme(config):
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: ("winter" if enabled.get("winter", True) else None)
    try:
        engine = Engine(config)
        assert engine.get_state()["settings"]["auto_theme_enabled"]["winter"] is True
        engine.set_theme("herbstwald")
        state = engine.get_state()["settings"]
        assert state["auto_theme_enabled"]["winter"] is False
        # Every other theme's toggle is left alone - unlike the old single
        # global switch, picking a theme doesn't disable unrelated ones.
        assert state["auto_theme_enabled"]["weihnachten"] is True
        assert engine.get_theme() == "herbstwald"
    finally:
        themes.get_auto_theme = original


def test_set_theme_does_not_touch_toggles_when_no_auto_theme_is_active(config):
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: None
    try:
        engine = Engine(config)
        engine.set_theme("herbstwald")
        state = engine.get_state()["settings"]
        assert all(state["auto_theme_enabled"].values())
    finally:
        themes.get_auto_theme = original


def test_set_auto_theme_enabled_is_persisted(config):
    engine = Engine(config)
    assert engine.set_auto_theme_enabled("weihnachten", False) is True
    assert engine.get_state()["settings"]["auto_theme_enabled"]["weihnachten"] is False

    engine2 = Engine(config)
    assert engine2.get_state()["settings"]["auto_theme_enabled"]["weihnachten"] is False


def test_set_auto_theme_enabled_rejects_theme_without_a_calendar_window(config):
    engine = Engine(config)
    assert engine.set_auto_theme_enabled("mondschein", False) is False
    assert engine.set_auto_theme_enabled("not-a-real-theme", False) is False


def test_custom_theme_colors_default_to_the_module_defaults(config):
    engine = Engine(config)
    assert engine.get_custom_theme_colors() == themes.DEFAULT_CUSTOM_THEME_COLORS


def test_set_custom_theme_colors_validates_before_applying_anything(config):
    engine = Engine(config)
    assert engine.set_custom_theme_colors({"bg": "#111111", "accent": "not-a-color"}) is False
    # A rejected call must not partially apply - "bg" should still be unchanged.
    assert engine.get_custom_theme_colors()["bg"] == themes.DEFAULT_CUSTOM_THEME_COLORS["bg"]


def test_set_custom_theme_colors_merges_a_partial_update(config):
    engine = Engine(config)
    assert engine.set_custom_theme_colors({"bg": "#111111"}) is True
    colors = engine.get_custom_theme_colors()
    assert colors["bg"] == "#111111"
    assert colors["accent"] == themes.DEFAULT_CUSTOM_THEME_COLORS["accent"]
    assert engine.get_theme() == themes.CUSTOM_THEME_ID


def test_set_custom_theme_colors_rejects_unknown_keys(config):
    engine = Engine(config)
    assert engine.set_custom_theme_colors({"not_a_real_var": "#111111"}) is False


def test_set_custom_theme_colors_validates_bar_radius_against_the_preset_list(config):
    engine = Engine(config)
    assert engine.set_custom_theme_colors({"bar_radius": "13px"}) is False
    assert engine.set_custom_theme_colors({"bar_radius": "999px"}) is True


def test_set_custom_theme_colors_turns_off_the_currently_active_auto_theme(config):
    original = themes.get_auto_theme
    themes.get_auto_theme = lambda enabled, today=None: ("winter" if enabled.get("winter", True) else None)
    try:
        engine = Engine(config)
        engine.set_custom_theme_colors({"bg": "#111111"})
        assert engine.get_state()["settings"]["auto_theme_enabled"]["winter"] is False
        assert engine.get_theme() == themes.CUSTOM_THEME_ID
    finally:
        themes.get_auto_theme = original


def test_custom_theme_colors_are_persisted(config):
    engine = Engine(config)
    engine.set_custom_theme_colors({"accent": "#abcdef"})

    engine2 = Engine(config)
    assert engine2.get_custom_theme_colors()["accent"] == "#abcdef"
    assert engine2.get_theme() == themes.CUSTOM_THEME_ID


def test_get_state_exposes_advent_candle_count(config):
    original = themes.get_advent_candle_count
    themes.get_advent_candle_count = lambda: 3
    try:
        engine = Engine(config)
        assert engine.get_state()["settings"]["advent_candles"] == 3
    finally:
        themes.get_advent_candle_count = original


def test_get_state_exposes_cpu_temperature(config):
    original = system_info.get_cpu_temperature_celsius
    system_info.get_cpu_temperature_celsius = lambda: 54.2
    try:
        engine = Engine(config)
        assert engine.get_state()["system"]["cpu_temp_celsius"] == 54.2
    finally:
        system_info.get_cpu_temperature_celsius = original


def test_get_state_cpu_temperature_none_when_unavailable(config):
    # Best-effort like everywhere else system_info is used (e.g. no
    # /sys/class/thermal/thermal_zone0/temp on non-Pi hardware) - the kiosk
    # badge just shows "-" rather than the request failing outright.
    original = system_info.get_cpu_temperature_celsius
    system_info.get_cpu_temperature_celsius = lambda: None
    try:
        engine = Engine(config)
        assert engine.get_state()["system"]["cpu_temp_celsius"] is None
    finally:
        system_info.get_cpu_temperature_celsius = original


# -- starting/stopping a story from the web UI ("play"/"stop" endpoints) ------


def test_play_story_starts_playback_like_a_chip_scan(config):
    story = _make_story_with_file(config, "AABBCC", title="Story")

    engine = Engine(config)
    engine.start()
    try:
        assert engine.play_story(story.id) is True
        state = engine.get_state()
        assert state["story"]["id"] == story.id
        assert state["player"]["playing"] is True
    finally:
        engine.stop()


def test_play_story_works_without_an_assigned_chip(config):
    story = repository.create_story(title="No chip yet")
    story_dir = config.media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)
    (story_dir / "track1.mp3").write_bytes(b"fake audio")
    repository.add_track(story.id, 0, "track1.mp3", None, None)
    assert story.uid is None

    engine = Engine(config)
    engine.start()
    try:
        assert engine.play_story(story.id) is True
        state = engine.get_state()
        assert state["story"]["id"] == story.id
        assert state["player"]["playing"] is True
    finally:
        engine.stop()


def test_play_story_returns_false_for_unknown_story_id(config):
    engine = Engine(config)
    engine.start()
    try:
        assert engine.play_story(999999) is False
        assert engine.get_state()["story"] is None
    finally:
        engine.stop()


def test_play_story_resumes_saved_position_for_a_story_without_a_chip(config):
    story = repository.create_story(title="No chip yet")
    story_dir = config.media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)
    for i in range(3):
        (story_dir / f"track{i}.mp3").write_bytes(b"fake audio")
        repository.add_track(story.id, i, f"track{i}.mp3", None, None)
    key = f"web:{story.id}"
    repository.save_playback_state(key, 2, 42.0)

    engine = Engine(config)
    engine.start()
    try:
        engine.play_story(story.id)
        state = engine.get_state()
        assert state["player"]["playlist_pos"] == 2
        assert state["player"]["time_pos"] == 42.0
    finally:
        engine.stop()


def test_stop_playback_clears_current_story_and_pauses(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["story"]["id"] == story.id

        engine.stop_playback()
        state = engine.get_state()
        assert state["story"] is None
        assert state["uid"] is None
        assert state["player"]["playing"] is False
    finally:
        engine.stop()


def test_stop_playback_then_play_story_resumes_where_it_left_off(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        engine.manual_seek_to(17.0)

        engine.stop_playback()
        assert repository.get_playback_state("AABBCC")[1] == 17.0

        engine.play_story(story.id)
        assert engine.get_state()["player"]["time_pos"] == 17.0
    finally:
        engine.stop()


def test_toggle_game_mode_flips_state_and_is_reflected_in_get_state(config):
    engine = Engine(config)
    engine.start()
    try:
        assert engine.get_state()["game_mode"]["active"] is False

        engine.toggle_game_mode()
        assert engine.get_state()["game_mode"]["active"] is True

        engine.toggle_game_mode()
        assert engine.get_state()["game_mode"]["active"] is False
    finally:
        engine.stop()


def test_game_toggle_function_tag_toggles_on_then_off_across_two_placements(config):
    config.rfid.poll_interval = 0.01
    config.rfid.missing_reads_to_remove = 2
    repository.set_function_tag("GAMECARD", "game_toggle")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("GAMECARD")
        time.sleep(0.15)
        state = engine.get_state()
        assert state["function_tag"] == "game_toggle"
        assert state["game_mode"]["active"] is True

        # Lifting the chip must not undo the toggle - game mode is a display
        # state independent of whether the triggering chip is still present,
        # same as shuffle/night mode.
        engine.simulate_remove()
        time.sleep(0.15)
        assert engine.get_state()["game_mode"]["active"] is True

        engine.simulate_scan("GAMECARD")
        time.sleep(0.15)
        assert engine.get_state()["game_mode"]["active"] is False
    finally:
        engine.stop()


def test_game_mode_does_not_pause_a_story_playing_in_the_background(config):
    config.rfid.poll_interval = 0.01
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["player"]["playing"] is True

        engine.toggle_game_mode()
        state = engine.get_state()
        assert state["game_mode"]["active"] is True
        assert state["player"]["playing"] is True
        assert state["story"]["id"] == story.id
    finally:
        engine.stop()


def test_set_alarm_validates_time_format(config):
    # Deliberately not started (no background loop) - same pattern as
    # test_wifi_status_check_is_throttled above: set_alarm/_check_alarm don't
    # need the player or RFID reader running, and skipping start()/stop()
    # sidesteps any race between the background loop's own _check_alarm
    # ticks (driven by the real wall clock) and this test's explicit calls.
    engine = Engine(config)
    with pytest.raises(ValueError):
        engine.set_alarm(True, "not-a-time", None, 60)
    with pytest.raises(ValueError):
        engine.set_alarm(True, "25:00", None, 60)


def test_set_alarm_persists_across_restart(config):
    story = _make_story_with_file(config, "ALARMCARD", title="Wake Story")

    engine = Engine(config)
    engine.set_alarm(True, "07:30", story.id, 45)
    alarm = engine.get_state()["alarm"]
    assert alarm == {
        "enabled": True,
        "time": "07:30",
        "story_id": story.id,
        "story_title": "Wake Story",
        "fade_seconds": 45,
    }

    engine2 = Engine(config)
    alarm = engine2.get_state()["alarm"]
    assert alarm["enabled"] is True
    assert alarm["time"] == "07:30"
    assert alarm["story_id"] == story.id
    assert alarm["fade_seconds"] == 45


def test_alarm_triggers_configured_story_at_wake_time(config, monkeypatch):
    story = _make_story_with_file(config, "ALARMCARD", title="Wake Story")
    monkeypatch.setattr(engine_module, "_wall_clock_now", lambda: datetime(2026, 8, 10, 7, 0))

    engine = Engine(config)
    engine.set_alarm(True, "07:00", story.id, 0)
    engine._check_alarm(time.monotonic())
    state = engine.get_state()
    assert state["story"]["id"] == story.id
    assert state["player"]["playing"] is True


def test_alarm_does_not_trigger_outside_configured_minute(config, monkeypatch):
    story = _make_story_with_file(config, "ALARMCARD", title="Wake Story")
    monkeypatch.setattr(engine_module, "_wall_clock_now", lambda: datetime(2026, 8, 10, 6, 59))

    engine = Engine(config)
    engine.set_alarm(True, "07:00", story.id, 0)
    engine._check_alarm(time.monotonic())
    assert engine.get_state()["story"] is None


def test_alarm_does_not_retrigger_same_day(config, monkeypatch):
    story = _make_story_with_file(config, "ALARMCARD", title="Wake Story")
    monkeypatch.setattr(engine_module, "_wall_clock_now", lambda: datetime(2026, 8, 10, 7, 0))

    engine = Engine(config)
    engine.set_alarm(True, "07:00", story.id, 0)
    engine._check_alarm(time.monotonic())
    assert engine.get_state()["player"]["playing"] is True

    # Paused, still "today" - a second check in the same trigger minute must
    # not restart it from the beginning.
    engine.manual_pause()
    engine._check_alarm(time.monotonic())
    assert engine.get_state()["player"]["playing"] is False


def test_alarm_does_not_interrupt_a_story_already_playing(config, monkeypatch):
    # This one genuinely needs the background loop (simulate_scan only takes
    # effect via _loop's RFID polling), so start()/stop() stay - but the
    # scenario is race-safe either way: any extra background _check_alarm
    # tick would independently reach the same "already playing, skip"
    # conclusion this test asserts.
    story = _make_story_with_file(config, "AABBCC", title="Already Playing")
    wake_story = _make_story_with_file(config, "ALARMCARD", title="Wake Story")
    monkeypatch.setattr(engine_module, "_wall_clock_now", lambda: datetime(2026, 8, 10, 7, 0))

    config.rfid.poll_interval = 0.01
    engine = Engine(config)
    engine.start()
    try:
        engine.simulate_scan("AABBCC")
        time.sleep(0.15)
        assert engine.get_state()["story"]["id"] == story.id

        engine.set_alarm(True, "07:00", wake_story.id, 0)
        engine._check_alarm(time.monotonic())
        # Still the manually-started story, not the alarm's.
        assert engine.get_state()["story"]["id"] == story.id
    finally:
        engine.stop()


def test_alarm_fades_volume_in_gradually(config, monkeypatch):
    story = _make_story_with_file(config, "ALARMCARD", title="Wake Story")
    monkeypatch.setattr(engine_module, "_wall_clock_now", lambda: datetime(2026, 8, 10, 7, 0))

    engine = Engine(config)
    engine.set_alarm(True, "07:00", story.id, 60)
    trigger_time = time.monotonic()
    engine._check_alarm(trigger_time)
    # Fade just started - volume should be at (or very near) 0, not the full
    # configured target.
    assert engine.get_state()["player"]["volume"] <= 1

    # Halfway through the fade window.
    engine._check_alarm(trigger_time + 30)
    halfway_volume = engine.get_state()["player"]["volume"]
    assert 0 < halfway_volume < engine._volume

    # Past the fade window - back to the real target volume.
    engine._check_alarm(trigger_time + 61)
    assert engine.get_state()["player"]["volume"] == engine._volume


def test_airplay_session_pauses_and_resumes_a_playing_story(config):
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    assert engine.play_story(story.id) is True
    assert engine.get_state()["player"]["playing"] is True

    engine.airplay_session_started()
    state = engine.get_state()
    assert state["airplay"]["active"] is True
    assert state["player"]["playing"] is False

    engine.airplay_session_ended()
    state = engine.get_state()
    assert state["airplay"]["active"] is False
    assert state["player"]["playing"] is True


def test_airplay_session_on_an_idle_box_does_not_start_playback(config):
    engine = Engine(config)
    assert engine.get_state()["player"]["playing"] is False

    engine.airplay_session_started()
    assert engine.get_state()["player"]["playing"] is False

    engine.airplay_session_ended()
    # Nothing was ever playing - ending the session must not suddenly start
    # something that wasn't running before.
    assert engine.get_state()["player"]["playing"] is False


def test_airplay_session_does_not_resume_a_story_that_was_already_paused(config):
    story = _make_story_with_file(config, "AABBCC")

    engine = Engine(config)
    engine.play_story(story.id)
    engine.manual_pause()
    assert engine.get_state()["player"]["playing"] is False

    engine.airplay_session_started()
    engine.airplay_session_ended()
    # AirPlay didn't cause the pause, so it must not cause a resume either.
    assert engine.get_state()["player"]["playing"] is False
