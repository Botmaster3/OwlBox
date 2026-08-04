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


def test_new_story_has_zeroed_out_listening_stats(config):
    story = repository.create_story(title="Story")
    assert story.play_count == 0
    assert story.total_seconds == 0
    assert story.last_played_at is None


def test_increment_play_count_and_add_listening_seconds(config):
    story = repository.create_story(title="Story")

    repository.increment_play_count(story.id)
    repository.add_listening_seconds(story.id, 30.5)
    repository.add_listening_seconds(story.id, 10.0)
    repository.increment_play_count(story.id)

    fetched = repository.get_story(story.id)
    assert fetched.play_count == 2
    assert fetched.total_seconds == 40.5
    assert fetched.last_played_at is not None

    # Negative/zero durations are ignored rather than silently corrupting the total.
    repository.add_listening_seconds(story.id, -5)
    assert repository.get_story(story.id).total_seconds == 40.5


def test_get_listening_stats_aggregates_and_ranks_by_total_seconds(config):
    assert repository.get_listening_stats() == {"total_plays": 0, "total_seconds": 0, "top_stories": []}

    quiet = repository.create_story(title="Never Played")
    loud = repository.create_story(title="Most Played")
    medium = repository.create_story(title="Some Plays")
    stream = repository.create_story(title="Radio", stream_url="https://stream.example.com/radio.mp3")

    repository.increment_play_count(loud.id)
    repository.add_listening_seconds(loud.id, 300)
    repository.increment_play_count(medium.id)
    repository.add_listening_seconds(medium.id, 60)
    repository.increment_play_count(stream.id)
    repository.add_listening_seconds(stream.id, 120)

    stats = repository.get_listening_stats()
    assert stats["total_plays"] == 3
    assert stats["total_seconds"] == 480
    # Ranked by total_seconds descending; the never-played story is excluded.
    assert [s["title"] for s in stats["top_stories"]] == ["Most Played", "Radio", "Some Plays"]
    assert stats["top_stories"][1]["is_stream"] is True
    assert quiet.title == "Never Played"  # sanity check the fixture itself


def test_get_weekly_review_aggregates_todays_listening(config):
    assert repository.get_weekly_review() == {"days": 7, "total_seconds": 0, "total_plays": 0, "top_stories": []}

    favorite = repository.create_story(title="Favorite")
    other = repository.create_story(title="Other")

    repository.increment_play_count(favorite.id)
    repository.add_listening_seconds(favorite.id, 200)
    repository.add_listening_seconds(favorite.id, 100)
    repository.increment_play_count(other.id)
    repository.add_listening_seconds(other.id, 50)

    review = repository.get_weekly_review()
    assert review["days"] == 7
    assert review["total_seconds"] == 350
    assert review["total_plays"] == 2
    assert [s["title"] for s in review["top_stories"]] == ["Favorite", "Other"]
    assert review["top_stories"][0]["seconds"] == 300
    assert review["top_stories"][0]["plays"] == 1


def test_get_weekly_review_excludes_older_days(config):
    from owlbox.db import write_cursor

    story = repository.create_story(title="Old Story")
    repository.add_listening_seconds(story.id, 90)
    assert repository.get_weekly_review()["total_seconds"] == 90

    # Backdate the only daily_listening row past the 7-day window.
    with write_cursor() as cur:
        cur.execute("UPDATE daily_listening SET date = date('now', '-30 days') WHERE story_id = ?", (story.id,))

    review = repository.get_weekly_review()
    assert review["total_seconds"] == 0
    assert review["top_stories"] == []
    # All-time total on the story itself is unaffected by the backdate.
    assert repository.get_story(story.id).total_seconds == 90
