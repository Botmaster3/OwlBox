from owlbox.player import MpvPlayer, StubPlayer, create_player


def test_stub_player_basic_playlist_flow(config):
    player = StubPlayer(config)
    player.load_playlist(["a.mp3", "b.mp3"], start_index=0, start_seconds=5.0)

    status = player.get_status()
    assert status["playing"] is True
    assert status["playlist_pos"] == 0

    player.next()
    assert player.get_status()["playlist_pos"] == 1

    player.previous()
    assert player.get_status()["playlist_pos"] == 0

    player.pause()
    assert player.get_status()["paused"] is True


def test_stub_player_does_not_step_past_playlist_bounds(config):
    player = StubPlayer(config)
    player.load_playlist(["only.mp3"])
    player.next()
    assert player.get_status()["playlist_pos"] == 0
    player.previous()
    assert player.get_status()["playlist_pos"] == 0


def test_stub_player_clamps_a_negative_saved_start_index_to_zero(config):
    # Confirmed on real hardware: a poisoned saved resume position of -1
    # (mpv's own idle-state playlist-pos reading, saved as-is by an earlier
    # bug in save_playback_state) must not leave playback stuck at a
    # negative index - it should just start from track 0 like "never
    # played before" does.
    player = StubPlayer(config)
    player.load_playlist(["a.mp3", "b.mp3"], start_index=-1)
    assert player.get_status()["playlist_pos"] == 0


def test_create_player_uses_stub_when_simulating(config):
    assert isinstance(create_player(config), StubPlayer)


def test_stub_player_relative_seek_clamps_at_zero(config):
    player = StubPlayer(config)
    player.load_playlist(["a.mp3"], start_index=0, start_seconds=5.0)

    player.seek(10, absolute=False)
    assert player.get_status()["time_pos"] == 15.0

    player.seek(-100, absolute=False)
    assert player.get_status()["time_pos"] == 0.0


def test_stub_player_defaults_to_no_repeat(config):
    player = StubPlayer(config)
    assert player._repeat_mode == "off"


def test_stub_player_defaults_to_no_shuffle(config):
    player = StubPlayer(config)
    assert player._shuffle_enabled is False


def test_stub_player_records_the_requested_shuffle_state(config):
    player = StubPlayer(config)
    player.set_shuffle(True)
    assert player._shuffle_enabled is True
    player.set_shuffle(False)
    assert player._shuffle_enabled is False


def test_stub_player_records_the_requested_repeat_mode(config):
    player = StubPlayer(config)
    player.set_repeat_mode("folder")
    assert player._repeat_mode == "folder"
    player.set_repeat_mode("track")
    assert player._repeat_mode == "track"


def test_mpv_player_disables_auto_mute_on_the_configured_card(config, monkeypatch):
    # HiFiBerry Amp2/DAC+ boards ship an "Auto Mute" mixer control that
    # mutes after digital silence and ramps back up gradually - confirmed on
    # real hardware to survive a plain `amixer sset ... off` only until the
    # next reboot (that only changes live kernel state, not persisted
    # state), so MpvPlayer re-applies it on every start. Just check it shells
    # out to the right amixer invocation, without needing a real amixer/mpv.
    config.audio.mixer_card = "2"
    calls = []
    monkeypatch.setattr(
        "owlbox.player.subprocess.run",
        lambda args, **kwargs: calls.append(args),
    )

    player = MpvPlayer(config)
    player._disable_auto_mute()

    assert calls == [["amixer", "-c", "2", "sset", "Auto Mute", "off"]]
