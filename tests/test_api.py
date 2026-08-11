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


def _login(client):
    with client.session_transaction() as sess:
        sess["authed"] = True


def test_peers_endpoints_require_admin_login(config):
    client, engine = _make_client(config)
    assert client.get("/api/peers").status_code == 401
    assert client.post("/api/peers", json={"name": "x", "host": "y"}).status_code == 401
    assert client.delete("/api/peers/1").status_code == 401


def test_peers_crud_over_http(config):
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

    resp = client.post("/api/peers", json={"name": "", "host": ""})
    assert resp.status_code == 400

    assert client.delete(f"/api/peers/{peer_id}").status_code == 200
    assert client.delete(f"/api/peers/{peer_id}").status_code == 404
    assert client.get("/api/peers").get_json() == []


def test_multiroom_endpoint_requires_admin_login(config):
    client, engine = _make_client(config)
    assert client.post("/api/multiroom", json={"role": "off"}).status_code == 401


def test_multiroom_endpoint_rejects_unknown_role(config):
    client, engine = _make_client(config)
    _login(client)
    resp = client.post("/api/multiroom", json={"role": "banana"})
    assert resp.status_code == 400


def test_multiroom_endpoint_slave_without_master_rejected(config):
    client, engine = _make_client(config)
    _login(client)
    resp = client.post("/api/multiroom", json={"role": "slave"})
    assert resp.status_code == 400
    assert "Hauptbox" in resp.get_json()["error"]


def test_multiroom_endpoint_success_reflects_in_state(config, monkeypatch):
    from owlbox import multiroom

    monkeypatch.setattr(multiroom, "set_role", lambda role, host: (True, "ok"))
    client, engine = _make_client(config)
    _login(client)

    resp = client.post("/api/multiroom", json={"role": "master"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["multiroom"]["role"] == "master"
    assert engine.get_state()["multiroom"]["role"] == "master"
