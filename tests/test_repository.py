from owlbox import repository


def test_create_and_fetch_story(config):
    story = repository.create_story(title="Die drei ???")
    assert story.id is not None
    assert repository.get_story(story.id).title == "Die drei ???"


def test_assign_and_lookup_by_uid(config):
    story = repository.create_story(title="Peter Pan")
    repository.assign_uid(story.id, "AABBCCDD")
    found = repository.get_story_by_uid("AABBCCDD")
    assert found is not None
    assert found.id == story.id


def test_assign_reassigns_uid_away_from_other_story(config):
    story_a = repository.create_story(title="A")
    story_b = repository.create_story(title="B")
    repository.assign_uid(story_a.id, "1234")
    repository.assign_uid(story_b.id, "1234")
    assert repository.get_story(story_a.id).uid is None
    assert repository.get_story(story_b.id).uid == "1234"


def test_tracks_ordering_and_reorder(config):
    story = repository.create_story(title="Story")
    t1 = repository.add_track(story.id, 0, "a.mp3", None, 10.0)
    t2 = repository.add_track(story.id, 1, "b.mp3", None, 20.0)

    tracks = repository.get_tracks(story.id)
    assert [t.filename for t in tracks] == ["a.mp3", "b.mp3"]

    repository.reorder_tracks(story.id, [t2.id, t1.id])
    tracks = repository.get_tracks(story.id)
    assert [t.filename for t in tracks] == ["b.mp3", "a.mp3"]


def test_playback_state_roundtrip(config):
    assert repository.get_playback_state("XYZ") == (0, 0.0)
    repository.save_playback_state("XYZ", 2, 12.5)
    assert repository.get_playback_state("XYZ") == (2, 12.5)
    repository.save_playback_state("XYZ", 3, 1.0)
    assert repository.get_playback_state("XYZ") == (3, 1.0)


def test_scan_log_and_last_unknown(config):
    repository.log_scan("NEW1")
    assert repository.get_last_scan()["uid"] == "NEW1"
    assert repository.get_last_unknown_scan() == "NEW1"

    story = repository.create_story(title="Known")
    repository.assign_uid(story.id, "NEW1")
    assert repository.get_last_unknown_scan() is None


def test_delete_story_cascades_tracks(config):
    story = repository.create_story(title="ToDelete")
    repository.add_track(story.id, 0, "a.mp3", None, None)
    repository.delete_story(story.id)
    assert repository.get_story(story.id) is None
    assert repository.get_tracks(story.id) == []
