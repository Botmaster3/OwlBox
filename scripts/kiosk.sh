#!/usr/bin/env bash
# The X "client" started by `startx` from owlbox-kiosk.service - this is the only
# thing that ever runs in the X session, there is no desktop environment around
# it (see systemd/owlbox-kiosk.service for why). Launches Chromium in kiosk mode
# against the local OwlBox now-playing page. Waits for the web server to be
# reachable first since it's started separately.
set -euo pipefail

URL="http://localhost:5000/"

# No desktop environment means nothing else turns off the screensaver/DPMS -
# the display is meant to always show the now-playing screen.
command -v xset >/dev/null 2>&1 && { xset s off; xset s noblank; xset -dpms; } || true

# Minimal window manager: not strictly required for a single fullscreen kiosk
# window, but negligible overhead and keeps things well-behaved if a stray JS
# alert()/confirm() (or similar transient window) ever pops up in Chromium.
command -v matchbox-window-manager >/dev/null 2>&1 && matchbox-window-manager -use_titlebar no &

CHROMIUM_BIN="$(command -v chromium-browser || command -v chromium || true)"
if [ -z "$CHROMIUM_BIN" ]; then
  echo "No chromium-browser/chromium binary found" >&2
  exit 1
fi

for _ in $(seq 1 60); do
  if curl -fsS "$URL" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

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
