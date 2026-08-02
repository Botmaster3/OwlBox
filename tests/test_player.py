from owlbox.player import StubPlayer, create_player


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


def test_create_player_uses_stub_when_simulating(config):
    assert isinstance(create_player(config), StubPlayer)


def test_stub_player_relative_seek_clamps_at_zero(config):
    player = StubPlayer(config)
    player.load_playlist(["a.mp3"], start_index=0, start_seconds=5.0)

    player.seek(10, absolute=False)
    assert player.get_status()["time_pos"] == 15.0

    player.seek(-100, absolute=False)
    assert player.get_status()["time_pos"] == 0.0
