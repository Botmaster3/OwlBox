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


def test_admin_user_starts_absent(config):
    assert repository.get_admin_user() is None


def test_admin_user_create_and_update(config):
    repository.create_admin_user("marco", "hashed-pw-1")
    user = repository.get_admin_user()
    assert user is not None
    assert user.username == "marco"
    assert user.password_hash == "hashed-pw-1"

    repository.update_admin_user("marco2", "hashed-pw-2")
    updated = repository.get_admin_user()
    assert updated.username == "marco2"
    assert updated.password_hash == "hashed-pw-2"


def test_parent_tags_crud_and_collisions(config):
    assert repository.list_parent_tags() == []
    assert repository.is_parent_tag("PARENT1") is False

    repository.add_parent_tag("PARENT1", "Vater")
    repository.add_parent_tag("PARENT2", "Mutter")
    assert repository.is_parent_tag("PARENT1") is True
    assert repository.get_parent_tag_label("PARENT1") == "Vater"
    assert repository.get_parent_tag_label("PARENT2") == "Mutter"
    assert len(repository.list_parent_tags()) == 2

    repository.add_parent_tag("PARENT1", "Papa")
    assert repository.get_parent_tag_label("PARENT1") == "Papa"
    assert len(repository.list_parent_tags()) == 2

    story = repository.create_story(title="Story")
    repository.assign_uid(story.id, "PARENT2")
    assert repository.get_parent_tag_label("PARENT2") is None
    assert repository.get_story_by_uid("PARENT2").id == story.id

    repository.set_function_tag("PARENT1", "next")
    assert repository.get_parent_tag_label("PARENT1") is None
    assert repository.get_function_tag("PARENT1") == "next"

    repository.add_parent_tag("FUNC1", "Oma")
    assert repository.get_function_tag("FUNC1") is None

    repository.delete_parent_tag("FUNC1")
    assert repository.list_parent_tags() == []


def test_function_tags_crud_and_story_uid_collision(config):
    assert repository.list_function_tags() == []

    repository.set_function_tag("FUNC1", "next")
    assert repository.get_function_tag("FUNC1") == "next"
    assert len(repository.list_function_tags()) == 1

    repository.set_function_tag("FUNC1", "previous")
    assert repository.get_function_tag("FUNC1") == "previous"
    assert len(repository.list_function_tags()) == 1

    story = repository.create_story(title="Story")
    repository.assign_uid(story.id, "FUNC1")
    assert repository.get_function_tag("FUNC1") is None
    assert repository.get_story_by_uid("FUNC1").id == story.id

    repository.set_function_tag("FUNC1", "next")
    assert repository.get_story_by_uid("FUNC1") is None

    repository.delete_function_tag("FUNC1")
    assert repository.list_function_tags() == []


def test_int_setting_roundtrip_and_default(config):
    assert repository.get_int_setting("max_volume", 100) == 100
    repository.set_setting("max_volume", 77)
    assert repository.get_int_setting("max_volume", 100) == 77


def test_library_stats(config):
    stats = repository.get_library_stats()
    assert stats == {"story_count": 0, "track_count": 0, "assigned_count": 0}

    story = repository.create_story(title="Story")
    repository.add_track(story.id, 0, "a.mp3", None, None)
    repository.add_track(story.id, 1, "b.mp3", None, None)
    repository.assign_uid(story.id, "ABC123")

    stats = repository.get_library_stats()
    assert stats == {"story_count": 1, "track_count": 2, "assigned_count": 1}


def test_create_story_with_stream_url(config):
    story = repository.create_story(title="Radio Owl", stream_url="https://stream.example.com/radio.mp3")
    assert story.stream_url == "https://stream.example.com/radio.mp3"
    assert repository.get_tracks(story.id) == []

    repository.assign_uid(story.id, "RADIO1")
    fetched = repository.get_story_by_uid("RADIO1")
    assert fetched.stream_url == "https://stream.example.com/radio.mp3"

    # A normal file-based story has no stream_url.
    file_story = repository.create_story(title="Normal")
    assert file_story.stream_url is None


def test_stream_story_can_have_a_custom_cover(config):
    story = repository.create_story(title="Radio Owl", stream_url="https://stream.example.com/radio.mp3")
    repository.set_cover_path(story.id, "cover.jpg")
    fetched = repository.get_story(story.id)
    assert fetched.stream_url == "https://stream.example.com/radio.mp3"
    assert fetched.cover_path == "cover.jpg"
