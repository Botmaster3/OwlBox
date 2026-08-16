"""API-level tests - most behavior is covered end-to-end via the engine tests
plus this session's manual curl/browser verification passes, but a couple of
things (like the AirPlay endpoints' loopback restriction) only actually live
in Flask's request handling and are worth pinning down with a real WSGI
request instead of just trusting the code by inspection."""
import io

from owlbox import repository
from owlbox.engine import Engine
from owlbox.web import create_app


def _make_client(config):
    engine = Engine(config)
    app = create_app(engine, config)
    app.config["TESTING"] = True
    return app.test_client(), engine


def test_airplay_session_endpoints_reject_non_loopback_callers(config):
    # shairport-sync's hook scripts always call these from the same Pi (see
    # docs/hardware.md) - environ_base lets the test drive Flask's actual
    # request.remote_addr check directly, rather than trusting
    # _is_loopback_request()'s logic by inspection alone.
    client, engine = _make_client(config)

    resp = client.post("/api/airplay/session-start", environ_base={"REMOTE_ADDR": "203.0.113.5"})
    assert resp.status_code == 403
    assert engine.get_state()["airplay"]["active"] is False

    resp = client.post("/api/airplay/session-start", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert resp.status_code == 200
    assert engine.get_state()["airplay"]["active"] is True

    # Rejected end-session call must not affect state either.
    resp = client.post("/api/airplay/session-end", environ_base={"REMOTE_ADDR": "203.0.113.5"})
    assert resp.status_code == 403
    assert engine.get_state()["airplay"]["active"] is True

    resp = client.post("/api/airplay/session-end", environ_base={"REMOTE_ADDR": "127.0.0.1"})
    assert resp.status_code == 200
    assert engine.get_state()["airplay"]["active"] is False


def test_airplay_session_endpoints_accept_ipv6_loopback(config):
    client, engine = _make_client(config)
    resp = client.post("/api/airplay/session-start", environ_base={"REMOTE_ADDR": "::1"})
    assert resp.status_code == 200
    assert engine.get_state()["airplay"]["active"] is True


def _login(client):
    with client.session_transaction() as sess:
        sess["authed"] = True


def test_peers_endpoints_require_admin_login(config):
    client, engine = _make_client(config)
    assert client.get("/api/peers").status_code == 401
    assert client.post("/api/peers", json={"name": "x", "host": "y"}).status_code == 401
    assert client.delete("/api/peers/1").status_code == 401


def test_peers_crud_over_http(config):
    # GET /api/peers also always runs a live mDNS discovery pass
    # (multiroom.discover_peers) - unmocked here on purpose, to also cover
    # its real fallback behavior: no avahi-browse in this test environment,
    # which must degrade to "found nothing" (see discover_peers' own
    # OSError handling) rather than erroring the whole listing out.
    client, engine = _make_client(config)
    _login(client)

    assert client.get("/api/peers").get_json() == []

    resp = client.post("/api/peers", json={"name": "Kinderzimmer", "host": "owlbox-kinderzimmer.local"})
    assert resp.status_code == 200
    peer_id = resp.get_json()["id"]

    # Unreachable in this test environment (no such host actually answers) -
    # checks that the reachability check degrades to False rather than
    # erroring the whole listing out.
    listed = client.get("/api/peers").get_json()
    assert len(listed) == 1
    assert listed[0]["name"] == "Kinderzimmer"
    assert listed[0]["reachable"] is False
    assert listed[0]["master_enabled"] is False
    assert listed[0]["discovered"] is False

    resp = client.post("/api/peers", json={"name": "", "host": ""})
    assert resp.status_code == 400

    assert client.delete(f"/api/peers/{peer_id}").status_code == 200
    assert client.delete(f"/api/peers/{peer_id}").status_code == 404
    assert client.get("/api/peers").get_json() == []


def test_peers_endpoint_merges_discovered_boxes(config, monkeypatch):
    from owlbox import multiroom

    monkeypatch.setattr(
        multiroom, "discover_peers", lambda **k: [{"name": "owlbox-kueche", "host": "192.168.1.43"}]
    )
    client, engine = _make_client(config)
    _login(client)

    listed = client.get("/api/peers").get_json()
    assert len(listed) == 1
    assert listed[0]["name"] == "owlbox-kueche"
    assert listed[0]["discovered"] is True
    assert listed[0]["id"] is None  # nothing to delete - it's not a DB row


def test_multiroom_endpoint_requires_admin_login(config):
    client, engine = _make_client(config)
    assert client.post("/api/multiroom", json={"feature_enabled": True, "master_enabled": True}).status_code == 401


def test_multiroom_endpoint_success_reflects_in_state(config, monkeypatch):
    from owlbox import multiroom

    monkeypatch.setattr(multiroom, "set_role", lambda role, host: (True, "ok"))
    client, engine = _make_client(config)
    _login(client)

    resp = client.post("/api/multiroom", json={"feature_enabled": True, "master_enabled": True})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["multiroom"]["feature_enabled"] is True
    assert body["multiroom"]["master_enabled"] is True
    assert body["multiroom"]["effective_role"] == "master"
    assert engine.get_state()["multiroom"]["master_enabled"] is True


def test_multiroom_endpoint_surfaces_os_level_failure(config, monkeypatch):
    from owlbox import multiroom

    monkeypatch.setattr(multiroom, "set_role", lambda role, host: (False, "systemctl fehlgeschlagen"))
    client, engine = _make_client(config)
    _login(client)

    resp = client.post("/api/multiroom", json={"feature_enabled": True, "master_enabled": True})
    assert resp.status_code == 400
    assert "systemctl fehlgeschlagen" in resp.get_json()["error"]


def test_multiroom_endpoint_feature_disabled_forces_master_off(config, monkeypatch):
    from owlbox import multiroom

    monkeypatch.setattr(multiroom, "set_role", lambda role, host: (True, "ok"))
    client, engine = _make_client(config)
    _login(client)

    resp = client.post("/api/multiroom", json={"feature_enabled": False, "master_enabled": True})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["multiroom"]["feature_enabled"] is False
    assert body["multiroom"]["master_enabled"] is False
    assert body["multiroom"]["effective_role"] == "off"


def _png_bytes():
    # Smallest possible valid PNG (1x1, transparent) - is_allowed_image()
    # only looks at the filename extension, not the actual bytes, but real
    # image content makes this fixture reusable if that ever changes.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c6360000002000155a2415d0000000049454e44ae42"
        "6082"
    )


def test_story_cover_requires_admin_login(config):
    story = repository.create_story(title="Ohne Cover")
    client, engine = _make_client(config)

    resp = client.post(
        f"/api/stories/{story.id}/cover",
        data={"cover": (io.BytesIO(_png_bytes()), "cover.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401
    assert client.delete(f"/api/stories/{story.id}/cover").status_code == 401


def test_story_cover_set_replace_and_remove(config):
    # Exercises exactly the flow the "Cover ändern"/"Cover entfernen"
    # buttons in admin_library.js drive - upload once (no cover existed
    # yet, the common case right after a Livestream-URL/Ganzer-Ordner
    # import), replace with a different image format (old file on disk
    # must not linger with the wrong extension), then remove entirely.
    story = repository.create_story(title="Der Karpatenhund")
    client, engine = _make_client(config)
    _login(client)

    assert repository.get_story(story.id).cover_path is None

    resp = client.post(
        f"/api/stories/{story.id}/cover",
        data={"cover": (io.BytesIO(_png_bytes()), "cover.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert resp.get_json()["cover_url"] == f"/media/{story.id}/cover.png"
    story_dir = config.media_dir / str(story.id)
    assert (story_dir / "cover.png").exists()

    # Replace with a different extension - the old cover.png must be gone,
    # not just shadowed by the new cover.jpg sitting alongside it.
    resp = client.post(
        f"/api/stories/{story.id}/cover",
        data={"cover": (io.BytesIO(_png_bytes()), "cover.jpg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    assert resp.get_json()["cover_url"] == f"/media/{story.id}/cover.jpg"
    assert (story_dir / "cover.jpg").exists()
    assert not (story_dir / "cover.png").exists()

    resp = client.delete(f"/api/stories/{story.id}/cover")
    assert resp.status_code == 200
    assert resp.get_json()["cover_url"] is None
    assert not (story_dir / "cover.jpg").exists()
    assert repository.get_story(story.id).cover_path is None

    # Removing again (no cover left) is a harmless no-op, not an error.
    resp = client.delete(f"/api/stories/{story.id}/cover")
    assert resp.status_code == 200
    assert resp.get_json()["cover_url"] is None


def test_story_cover_rejects_unsupported_file_and_missing_story(config):
    story = repository.create_story(title="Bibi Blocksberg")
    client, engine = _make_client(config)
    _login(client)

    resp = client.post(
        f"/api/stories/{story.id}/cover",
        data={"cover": (io.BytesIO(b"not an image"), "cover.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert repository.get_story(story.id).cover_path is None

    resp = client.post(f"/api/stories/{story.id}/cover", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400

    resp = client.post(
        "/api/stories/999999/cover",
        data={"cover": (io.BytesIO(_png_bytes()), "cover.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 404
    assert client.delete("/api/stories/999999/cover").status_code == 404


def test_game_mode_toggle_requires_admin_login(config):
    client, engine = _make_client(config)
    assert client.post("/api/game-mode/toggle").status_code == 401
    assert engine.get_state()["game_mode"]["active"] is False


def test_game_mode_toggle_flips_state(config):
    # The web-UI equivalent of scanning a "Spiele-Menü an/aus" function tag
    # (engine.py's toggle_game_mode(), reached here without any RFID chip
    # involved at all) - see admin_dashboard.js's "🎮 Spiele-Menü
    # öffnen/schließen" button.
    client, engine = _make_client(config)
    _login(client)

    assert engine.get_state()["game_mode"]["active"] is False

    resp = client.post("/api/game-mode/toggle")
    assert resp.status_code == 200
    assert resp.get_json() == {"active": True}
    assert engine.get_state()["game_mode"]["active"] is True

    resp = client.post("/api/game-mode/toggle")
    assert resp.status_code == 200
    assert resp.get_json() == {"active": False}
    assert engine.get_state()["game_mode"]["active"] is False
