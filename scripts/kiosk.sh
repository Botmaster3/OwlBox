#!/usr/bin/env bash
# The X "client" started by `startx` from owlbox-kiosk.service - this is the only
# thing that ever runs in the X session, there is no desktop environment around
# it (see systemd/owlbox-kiosk.service for why). Launches Chromium in kiosk mode
# directly against the real OwlBox web server - by the time this script runs,
# owlbox-kiosk.service's own ExecStartPre has already waited for that server
# to actually respond and only then handed off from the OS-level Plymouth boot
# splash (see scripts/install.sh's "Boot-Fortschrittsbalken" section), so
# there's nothing left to wait for here and no need for a second, kiosk-side
# loading page - one boot progress bar, not two.
set -euo pipefail

URL="http://localhost:5000/"

# No desktop environment means nothing else turns off the screensaver/DPMS -
# the display is meant to always show the now-playing screen.
command -v xset >/dev/null 2>&1 && { xset s off; xset s noblank; xset -dpms; } || true

# No software rotation here: the current 5" Waveshare display's orientation
# is handled by how it's physically mounted, not a video flip. (The earlier
# 7" display needed a 180° flip - see git history of this file/install.sh
# for that - because xrandr's --rotate request never actually took effect
# on real hardware for a DSI panel under the KMS driver, only a
# cmdline.txt "video=DSI-1:<mode>,rotate=<deg>" parameter did. If this
# display ever needs a software rotation after all, that's the mechanism
# to reach for, not xrandr.)

# Minimal window manager: not strictly required for a single fullscreen kiosk
# window, but negligible overhead and keeps things well-behaved if a stray JS
# alert()/confirm() (or similar transient window) ever pops up in Chromium.
command -v matchbox-window-manager >/dev/null 2>&1 && matchbox-window-manager -use_titlebar no &

CHROMIUM_BIN="$(command -v chromium-browser || command -v chromium || true)"
if [ -z "$CHROMIUM_BIN" ]; then
  echo "No chromium-browser/chromium binary found" >&2
  exit 1
fi

# Hide the mouse cursor if unclutter is installed (nice on a touchscreen-only kiosk).
command -v unclutter >/dev/null 2>&1 && unclutter -idle 0.5 -root &

exec "$CHROMIUM_BIN" \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --check-for-update-interval=31536000 \
  --disable-features=Translate \
  --lang=de \
  --app="$URL"
