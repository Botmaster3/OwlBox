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
  printf '   %-22s %s\n' "Taster/Encoder:" "$(get_key gpio enabled)"
  printf '   %-22s %s\n' "Backlight-PWM:" "$(get_key gpio backlight_pin)"
  if [ "$DRYRUN" != "1" ]; then
    printf '   %-22s %s\n' "owlbox.service:" "$(systemctl is-active owlbox.service 2>/dev/null || echo inactive)"
    printf '   %-22s %s\n' "Kiosk/Display:" "$(systemctl is-active owlbox-kiosk.service 2>/dev/null || echo inactive)"
  fi
  echo
}

STAGE="${1:-}"

case "$STAGE" in
  0)
    echo "== Stufe 0: nur Audio, OwlBox komplett aus =="
    svc stop owlbox.service owlbox-kiosk.service || true
    cat <<'EOF'

   Alles gestoppt. Jetzt direkt im Terminal abspielen, z.B.:

     mpv --no-video --audio-device=alsa/hw:0,0 /opt/owlbox/media/<irgendeine>.mp3

   1-2 Minuten hoeren. Das ist die Referenz: knistert es SCHON HIER,
   liegt es nicht an der OwlBox-Software, sondern an Hardware/Verkabelung/
   config.txt - dann bei Stufe 0 bleiben und dort weitersuchen.
EOF
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
