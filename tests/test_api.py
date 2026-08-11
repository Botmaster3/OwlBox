"""API-level tests - most behavior is covered end-to-end via the engine tests
plus this session's manual curl/browser verification passes, but a couple of
things (like the AirPlay endpoints' loopback restriction) only actually live
in Flask's request handling and are worth pinning down with a real WSGI
request instead of just trusting the code by inspection."""
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
