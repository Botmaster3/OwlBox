#!/usr/bin/env bash
# Runs as root via owlbox-kiosk.service's ExecStartPre (the '+' prefix there
# overrides that unit's own User=owlbox for just this one line - needed
# because `plymouth quit` below requires root, or at least more than the
# unprivileged kiosk user has). Executes *before* X/Chromium ever start -
# the OS-level Plymouth boot splash (see install.sh's "Boot-Fortschrittsbalken"
# section) is still covering the screen this whole time, so there's no need
# for a second, kiosk-side loading indicator: by the time Chromium takes
# over, the app is already there for it to show.
#
# Why this script exists at all instead of just letting Plymouth quit on its
# own: the stock plymouth-quit(-wait).service - masked by install.sh
# specifically so it can't race this - quits Plymouth once the general boot
# sequence considers itself done, which has nothing to do with whether
# owlbox.service's Flask app is actually answering HTTP requests yet.
# owlbox.service is Type=simple, so systemd itself already considers it
# "started" the instant the process forks, well before the DB/RFID
# reader/web server inside are actually up - that gap used to leave the
# display dead/backlit with zero feedback (or, in an earlier version of this
# project, papered over with a *second* loading bar drawn by Chromium
# itself - removed again since one OS-level bar covering the whole wait is
# simpler than two bars covering two different halves of it).
set -uo pipefail

for _ in $(seq 1 120); do  # up to ~60s
  curl -fs -o /dev/null -m 1 "http://localhost:5000/api/state" && break
  sleep 0.5
done
# Falls through and quits Plymouth even on a timeout (e.g. owlbox.service
# stuck restart-looping) - better a kiosk showing Chromium's own "can't
# connect" than a boot splash frozen forever. owlbox.service's own
# Restart=on-failure keeps retrying in the background either way.

command -v plymouth >/dev/null 2>&1 && plymouth quit || true
