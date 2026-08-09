#!/usr/bin/env bash
# Staged bring-up for isolating an audio problem (crackling/noise during
# playback). Each stage switches on exactly ONE more hardware component than
# the previous one, so the first stage that starts crackling names the culprit
# directly instead of leaving it to guesswork.
#
#   sudo owlbox-audio-stage 0    # nothing but audio - the baseline
#   sudo owlbox-audio-stage 1    # + OwlBox app, all hardware still off
#   sudo owlbox-audio-stage 2    # + kiosk display (Chromium)
#   sudo owlbox-audio-stage 3    # + backlight PWM
#   sudo owlbox-audio-stage 4    # + buttons/rotary encoders
#   sudo owlbox-audio-stage 5    # + RFID reader (= normal operation)
#   sudo owlbox-audio-stage status
#
# Listen for 1-2 minutes at each stage before moving on. Config edits are done
# in place and preserve the file's comments, so the box stays fully usable -
# stage 5 restores exactly the normal configuration.
set -euo pipefail

CONFIG="${OWLBOX_CONFIG:-/opt/owlbox/config/config.yaml}"
# Set OWLBOX_STAGE_DRYRUN=1 to skip all systemctl calls (used by the tests).
DRYRUN="${OWLBOX_STAGE_DRYRUN:-0}"

if [ ! -f "$CONFIG" ]; then
  echo "Config not found: $CONFIG" >&2
  echo "Run the installer first (sudo owlbox-install)." >&2
  exit 1
fi

if [ "$DRYRUN" != "1" ] && [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo owlbox-audio-stage $*" >&2
  exit 1
fi

# set_key <section> <key> <value>
# Replaces "key: ..." inside the given top-level YAML section, keeping the
# file's comments and indentation intact. Inserts the key directly under the
# section header if it isn't there yet (older config.yaml files predate
# gpio.enabled). Deliberately regex-based rather than a YAML round-trip: a
# PyYAML load/dump would silently strip every explanatory comment in the file.
set_key() {
  python3 - "$CONFIG" "$1" "$2" "$3" <<'PY'
import re, sys
path, section, key, value = sys.argv[1:5]
lines = open(path).read().splitlines(keepends=True)
out, in_section, done = [], False, False

def insert_at_section_end():
    # Park the new key on the last non-blank line of the section, so it doesn't
    # end up stranded after the blank line that separates two sections.
    trailing = []
    while out and out[-1].strip() == "":
        trailing.append(out.pop())
    out.append(f"  {key}: {value}\n")
    out.extend(reversed(trailing))

for line in lines:
    if re.match(r'^[A-Za-z_]\w*:', line):          # a top-level section header
        if in_section and not done:                # section ended without the key
            insert_at_section_end()
            done = True
        in_section = line.split(':', 1)[0] == section
        out.append(line)
        continue
    if in_section and not done:
        # Keep any trailing "# ..." comment on the line being rewritten - those
        # document the allowed values (e.g. "# mfrc522 | simulated").
        m = re.match(rf'^(\s+){re.escape(key)}\s*:[^#\n]*?\s*(#.*?)?\s*$', line)
        if m:
            indent, comment = m.group(1), m.group(2)
            out.append(f"{indent}{key}: {value}" + (f"   {comment}" if comment else "") + "\n")
            done = True
            continue
    out.append(line)
if in_section and not done:                        # section ran to end of file
    insert_at_section_end()
    done = True
if not done:
    sys.exit(f"section '{section}' not found in {path}")
open(path, 'w').writelines(out)
PY
}

get_key() {
  python3 - "$CONFIG" "$1" "$2" <<'PY'
import re, sys
path, section, key = sys.argv[1:4]
in_section = False
for line in open(path):
    if re.match(r'^[A-Za-z_]\w*:', line):
        in_section = line.split(':', 1)[0] == section
        continue
    if in_section:
        m = re.match(rf'^\s+{re.escape(key)}\s*:\s*(.*?)\s*(?:#.*)?$', line)
        if m:
            print(m.group(1) or "(empty)")
            break
else:
    print("(not set)")
PY
}

svc() {
  if [ "$DRYRUN" = "1" ]; then
    echo "   [dry-run] systemctl $*"
  else
    systemctl "$@"
  fi
}

apply() {  # apply <rfid> <gpio_enabled> <backlight_pin>
  set_key rfid reader "$1"
  set_key gpio enabled "$2"
  set_key gpio backlight_pin "$3"
}

show_status() {
  echo
  echo "Aktive Komponenten laut $CONFIG:"
  printf '   %-22s %s\n' "RFID-Leser:"   "$(get_key rfid reader)"
  local gpio_enabled
  gpio_enabled="$(get_key gpio enabled)"
  # config.yaml files created before gpio.enabled existed simply lack the
  # key - the app defaults it to true (see GpioConfig.enabled), so say that
  # plainly instead of the confusing raw "(not set)".
  [ "$gpio_enabled" = "(not set)" ] && gpio_enabled="true (Standardwert, Zeile fehlt noch in config.yaml)"
  printf '   %-22s %s\n' "Taster/Encoder:" "$gpio_enabled"
  printf '   %-22s %s\n' "Backlight-PWM:" "$(get_key gpio backlight_pin)"
  if [ "$DRYRUN" != "1" ]; then
    # systemctl is-active prints the state to stdout even when it exits
    # non-zero (any state other than "active") - a "|| echo inactive"
    # fallback would run *in addition* to that, doubling the output, since
    # a command substitution captures everything written inside it, not just
    # the last command's. The state itself is always non-empty text, so an
    # empty capture (e.g. systemctl missing) is the only real fallback case.
    # "|| true" (not "|| echo ...") only to keep `set -e` from treating the
    # assignment's exit status - which is is-active's own, e.g. 3 for
    # "inactive" - as a script-ending failure.
    local owlbox_state kiosk_state
    owlbox_state="$(systemctl is-active owlbox.service 2>/dev/null || true)"
    kiosk_state="$(systemctl is-active owlbox-kiosk.service 2>/dev/null || true)"
    printf '   %-22s %s\n' "owlbox.service:" "${owlbox_state:-inactive}"
    printf '   %-22s %s\n' "Kiosk/Display:" "${kiosk_state:-inactive}"
  fi
  echo
}

# Stage 0 is the baseline the whole procedure rests on, so it doesn't just
# print a command to try - it checks the things that make "no sound at all"
# far more likely than a crackle: missing/extra sound cards and a muted or
# zeroed ALSA mixer. A muted mixer produces silence that looks exactly like a
# broken driver, and OwlBox drives that same hardware mixer for its own volume
# control, so it can genuinely be left at 0 when the service is stopped.
baseline_check() {
  echo
  if ! command -v aplay >/dev/null 2>&1; then
    echo "   aplay nicht gefunden - bitte 'sudo apt install alsa-utils' nachholen." >&2
    return
  fi

  echo "-- Soundkarten (aplay -l) --"
  aplay -l 2>/dev/null | grep '^card' || echo "   KEINE Soundkarte gefunden!"
  echo

  local card
  card="$(aplay -l 2>/dev/null | sed -n 's/^card \([0-9]\+\):.*hifiberry.*/\1/Ip' | head -1 || true)"
  if [ -z "$card" ]; then
    cat <<'EOF'
   !! Keine HiFiBerry-Karte gefunden.
      Damit kann es keinen Ton geben - das ist die Ursache, nicht das Knistern.
      Pruefen: dtoverlay=hifiberry-dacplus in der config.txt vorhanden,
      dtparam=audio=on auskommentiert, vc4-kms-v3d mit ",noaudio".
      Siehe docs/hardware.md. Danach neu starten.
EOF
    return
  fi
  echo "   HiFiBerry ist Karte $card."
  echo

  echo "-- Mixer --"
  local ctl=""
  for candidate in Digital PCM Master Playback; do
    if amixer -c "$card" sget "$candidate" >/dev/null 2>&1; then ctl="$candidate"; break; fi
  done
  if [ -z "$ctl" ]; then
    echo "   Kein bekannter Regler gefunden. Vorhanden:"
    amixer -c "$card" scontrols 2>/dev/null | sed 's/^/     /'
  else
    amixer -c "$card" sget "$ctl" 2>/dev/null | grep -E '^\s+(Mono|Front)' | sed 's/^/   /'
    local state
    state="$(amixer -c "$card" sget "$ctl" 2>/dev/null | grep -oE '\[[0-9]+%\]|\[off\]' | head -2 | tr '\n' ' ' || true)"
    case "$state" in
      *"[off]"*|*"[0%]"*)
        echo
        echo "   !! Der Regler '$ctl' ist stummgeschaltet oder steht auf 0%."
        echo "      DAS ist der Grund fuer 'kein Ton'. Beheben mit:"
        echo
        echo "        sudo amixer -c $card sset $ctl 80% unmute"
        echo
        ;;
      *)
        echo "   Regler '$ctl' ist aktiv - Lautstaerke sieht in Ordnung aus."
        ;;
    esac
  fi
  echo

  echo "-- Testbefehle (alles gestoppt, nichts stoert) --"
  echo
  echo "   1) Reiner Testton, braucht keine Datei:"
  echo
  echo "        speaker-test -D hw:$card,0 -c 2 -t sine -l 1"
  echo
  local track
  track="$(find /opt/owlbox/media -type f \( -iname '*.mp3' -o -iname '*.m4a' \
           -o -iname '*.ogg' -o -iname '*.wav' -o -iname '*.flac' \) 2>/dev/null | head -1 || true)"
  if [ -n "$track" ]; then
    echo "   2) Echte Datei aus deiner Bibliothek:"
    echo
    echo "        mpv --no-video --audio-device=alsa/hw:$card,0 \"$track\""
  else
    echo "   2) (keine Mediendatei unter /opt/owlbox/media gefunden -"
    echo "       dann reicht der Testton oben)"
  fi
  cat <<'EOF'

   1-2 Minuten hoeren. Das ist die Referenz:
   Knistert es SCHON HIER, liegt es nicht an der OwlBox-Software, sondern an
   Hardware/Verkabelung/Netzteil/config.txt - siehe docs/audio-troubleshooting.md.
EOF
}

STAGE="${1:-}"

case "$STAGE" in
  0)
    echo "== Stufe 0: nur Audio, OwlBox komplett aus =="
    svc stop owlbox.service owlbox-kiosk.service || true
    baseline_check
    ;;
  1)
    echo "== Stufe 1: + OwlBox-App, alle Hardware aus, kein Display =="
    apply simulated false null
    svc stop owlbox-kiosk.service || true
    svc restart owlbox.service
    cat <<'EOF'

   Die App laeuft, aber ohne RFID, ohne Taster/Encoder, ohne Backlight-PWM
   und ohne Kiosk. Abspielen ueber die Weboberflaeche vom Handy/Laptop:
   http://<Pi-IP>:5000 -> Bibliothek -> Geschichte starten.
EOF
    ;;
  2)
    echo "== Stufe 2: + Kiosk/Display =="
    apply simulated false null
    svc restart owlbox.service
    svc restart owlbox-kiosk.service
    echo
    echo "   Chromium laeuft jetzt mit. Backlight-PWM weiterhin aus"
    echo "   (Display haengt an voller Helligkeit, das ist so gewollt)."
    ;;
  3)
    echo "== Stufe 3: + Backlight-PWM =="
    apply simulated false 13
    svc restart owlbox.service
    svc restart owlbox-kiosk.service
    cat <<'EOF'

   Jetzt zusaetzlich die Software-PWM auf GPIO 13.
   WICHTIG bei dieser Stufe: die Helligkeit einmal verstellen (Regler oder
   Einstellungen) - auf ~50% und auf 100%. Aendert sich das Knistern mit
   der Helligkeit, ist die PWM die Ursache.
EOF
    ;;
  4)
    echo "== Stufe 4: + Taster und Drehregler =="
    apply simulated true 13
    svc restart owlbox.service
    svc restart owlbox-kiosk.service
    echo
    echo "   GPIO-Bedienelemente aktiv. RFID weiterhin aus."
    ;;
  5)
    echo "== Stufe 5: + RFID-Leser (= normaler Betrieb) =="
    apply mfrc522 true 13
    svc restart owlbox.service
    svc restart owlbox-kiosk.service
    echo
    echo "   Vollstaendige normale Konfiguration wiederhergestellt."
    ;;
  status|"")
    echo "== Aktueller Stand =="
    ;;
  *)
    echo "Unbekannte Stufe: $STAGE (erlaubt: 0 1 2 3 4 5 status)" >&2
    exit 1
    ;;
esac

show_status

if [ "$STAGE" != "status" ] && [ -n "$STAGE" ]; then
  echo "1-2 Minuten hoeren. Sauber -> naechste Stufe."
  echo "Knistert es -> die zuletzt zugeschaltete Komponente ist die Ursache."
fi
