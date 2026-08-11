#!/usr/bin/env bash
# Called by shairport-sync (sessioncontrol.run_this_before_play_begins in
# /etc/shairport-sync.conf, written by `sudo ./scripts/install.sh airplay` -
# see docs/hardware.md) right before AirPlay audio starts flowing. Tells
# OwlBox to pause its own playback for the duration, if it was actually
# playing - see owlbox/web/api.py's /api/airplay/session-start and
# Engine.airplay_session_started().
#
# -m 5: never let a slow/unreachable OwlBox process hang the AirPlay session
# start. -f: don't treat an HTTP error as fatal to this script either way -
# a failed duck attempt shouldn't block AirPlay from playing at all, worst
# case the two audio sources briefly overlap instead.
curl -fsS -m 5 -X POST http://127.0.0.1:5000/api/airplay/session-start >/dev/null 2>&1 || true
