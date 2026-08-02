#!/usr/bin/env bash
# Launches Chromium in kiosk mode against the local OwlBox now-playing page.
# Waits for the web server to be reachable first since it's started separately.
set -euo pipefail

URL="http://localhost:5000/"

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
  --app="$URL"
