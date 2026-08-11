#!/usr/bin/env bash
# Called by shairport-sync (sessioncontrol.run_this_after_play_ends in
# /etc/shairport-sync.conf, written by `sudo ./scripts/install.sh airplay` -
# see docs/hardware.md) right after an AirPlay session ends. Tells OwlBox to
# resume its own playback, but only if this same AirPlay session was the one
# that paused it - see owlbox/web/api.py's /api/airplay/session-end and
# Engine.airplay_session_ended().
curl -fsS -m 5 -X POST http://127.0.0.1:5000/api/airplay/session-end >/dev/null 2>&1 || true
