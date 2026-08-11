#!/usr/bin/env bash
# Guided, staged bring-up: wire and verify ONE hardware component at a time,
# in the order you actually connect it, instead of everything at once and
# then hunting for what's wrong. Each stage only turns on what it needs,
# leaving everything not yet wired switched off in config.yaml so it can't
# interfere - see docs/staged-setup.md for the reasoning and what each
# failure mode looks like.
#
#   sudo owlbox-stage sound      # 1) nur der HiFiBerry Amp2 angeschlossen
#   sudo owlbox-stage display    # 2) + 7"-Display (DSI-Kabel + Stromjumper)
#   sudo owlbox-stage rfid       # 3) + RC522-Leser
#   sudo owlbox-stage controls   # 4) + Taster und Dreh-Encoder (= Normalbetrieb)
#   sudo owlbox-stage status     # zeigt den aktuellen Stand, ändert nichts
#
# Wiring order matches how the standard build is assembled (see
# docs/hardware.md) - HiFiBerry sits directly on the header, everything else
# is added on top of/around it. Each stage prints exactly what to test next
# before you move on; the rfid/controls stages additionally run a small
# standalone tool (no browser needed) so wiring can be confirmed directly.
set -euo pipefail

INSTALL_DIR="${OWLBOX_INSTALL_DIR:-/opt/owlbox}"
CONFIG="${OWLBOX_CONFIG:-$INSTALL_DIR/config/config.yaml}"
PYTHON="$INSTALL_DIR/.venv/bin/python3"
# Presence marks "install.sh has not seen a completed staged bring-up yet" -
# see install.sh's own STAGED_MARKER comment. Only the "controls" stage
# (the last one, equivalent to normal operation) removes it.
STAGED_MARKER="$INSTALL_DIR/config/.staged_setup"
# Set OWLBOX_STAGE_DRYRUN=1 to skip all systemctl calls and the interactive
# hardware test tools (used by the tests - they can't drive real GPIO/SPI).
DRYRUN="${OWLBOX_STAGE_DRYRUN:-0}"

if [ ! -f "$CONFIG" ]; then
  echo "Config not found: $CONFIG" >&2
  echo "Run the installer first (sudo owlbox-install)." >&2
  exit 1
fi

if [ "$DRYRUN" != "1" ] && [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo owlbox-stage $*" >&2
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

# Fixed volume every listening test forces the hardware mixer to, regardless
# of whatever the app/database currently has saved. Confirmed on real
# hardware to matter: comparing stages by ear while relying on whatever
# volume the app happened to be at (default_volume, a previously-saved
# value, a mid-fade dip, ...) confounds "does this stage's hardware affect
# audio quality" with "what does the app's persisted volume happen to be
# right now" - two completely different questions. Forcing a known,
# consistent, clearly-audible level via `amixer` directly (bypassing the app
# entirely) makes every stage's listening test apples-to-apples.
TEST_VOLUME_PERCENT=75

# find_mixer_control <card>
# Echoes the first working control name, or nothing if none respond.
find_mixer_control() {
  local card="$1" candidate
  for candidate in Digital PCM Master Playback; do
    if amixer -c "$card" sget "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return
    fi
  done
}

# force_test_volume <card>
# Sets the hardware mixer to TEST_VOLUME_PERCENT directly via amixer - not
# through the app, so it works regardless of whether owlbox.service is
# running, paused mid-fade, or has some old/unexpected value saved in its
# database. Silently does nothing if no known control responds (sound_check
# already reports that case in detail).
force_test_volume() {
  local card="$1" ctl
  ctl="$(find_mixer_control "$card")"
  [ -n "$ctl" ] && amixer -c "$card" sset "$ctl" "${TEST_VOLUME_PERCENT}%" unmute >/dev/null 2>&1
}

# run_test_tool <script.py> <freundlicher Name>
# Runs one of scripts/test_rfid.py / scripts/test_controls.py in the
# foreground, capped at TEST_TOOL_TIMEOUT_SECONDS - so "wire it, test it,
# THEN commit the config" happens in one command instead of three separate
# steps to keep track of, but without forcing a manual Ctrl+C every single
# time the stage runs (e.g. while retesting something unrelated with the
# hardware not even attached yet - a real, common case during a staged
# bring-up). Ctrl+C still works to end it early if you're actually testing
# a scan/button press and don't want to wait out the timeout.
TEST_TOOL_TIMEOUT_SECONDS=8

run_test_tool() {
  local script="$1" label="$2"
  if [ "$DRYRUN" = "1" ]; then
    echo "   [dry-run] timeout ${TEST_TOOL_TIMEOUT_SECONDS}s $PYTHON $INSTALL_DIR/scripts/$script"
    return
  fi
  if [ ! -x "$PYTHON" ]; then
    echo "   $PYTHON nicht gefunden - lief 'sudo owlbox-install' schon durch?" >&2
    return 1
  fi
  echo
  echo "-- $label-Test (${TEST_TOOL_TIMEOUT_SECONDS}s, oder frueher mit Strg+C beenden) --"
  echo
  # -s INT (not the default SIGTERM): test_rfid.py/test_controls.py only
  # catch KeyboardInterrupt (SIGINT) to run their `finally: reader.close()`/
  # `controls.close()` cleanup - a bare SIGTERM would skip that entirely and
  # could leave the RC522/GPIO chip handle claimed, making the *next* open
  # (owlbox.service's own, moments later in this same stage) fail with
  # "GPIO busy" - confirmed real behavior for that exact error elsewhere in
  # this script's history, just from a different cause. -k 3 as a backstop
  # in case cleanup itself ever hangs.
  timeout -s INT -k 3 "${TEST_TOOL_TIMEOUT_SECONDS}s" "$PYTHON" "$INSTALL_DIR/scripts/$script" || true
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
    # the last command's. "|| true" (not "|| echo ...") only to keep set -e
    # from treating the assignment's exit status - which is is-active's own,
    # e.g. 3 for "inactive" - as a script-ending failure.
    local owlbox_state kiosk_state
    owlbox_state="$(systemctl is-active owlbox.service 2>/dev/null || true)"
    kiosk_state="$(systemctl is-active owlbox-kiosk.service 2>/dev/null || true)"
    printf '   %-22s %s\n' "owlbox.service:" "${owlbox_state:-inactive}"
    printf '   %-22s %s\n' "Kiosk/Display:" "${kiosk_state:-inactive}"
  fi
  echo
}

# The "sound" stage is the baseline everything else rests on, so it doesn't
# just print a command to try - it checks the things that make "no sound at
# all" far more likely than a crackle: missing/extra sound cards and a muted
# or zeroed ALSA mixer. A muted mixer produces silence that looks exactly
# like a broken driver, and OwlBox drives that same hardware mixer for its
# own volume control, so it can genuinely be left at 0 from a previous run.
sound_check() {
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
  ctl="$(find_mixer_control "$card")"
  if [ -z "$ctl" ]; then
    echo "   Kein bekannter Regler gefunden. Vorhanden:"
    amixer -c "$card" scontrols 2>/dev/null | sed 's/^/     /'
    echo
    echo "-- Testbefehl --"
    echo
    echo "   Kein Regler zum automatischen Setzen gefunden, deshalb ohne feste"
    echo "   Lautstaerke:"
    echo
    echo "        speaker-test -D hw:$card,0 -c 2 -t sine -l 1"
    return
  fi
  if [ "$DRYRUN" = "1" ]; then
    echo "   [dry-run] amixer -c $card sset $ctl ${TEST_VOLUME_PERCENT}% unmute; speaker-test ..."
    return
  fi
  # Force a known, fixed volume directly on the hardware mixer - not through
  # the app - so this test is never confused by whatever value the app/
  # database happens to have (its own default, a previously-saved value from
  # an unrelated earlier session, a chime/fade mid-dip, ...). Confirmed on
  # real hardware this distinction matters: "kein Ton" during a staged
  # bring-up turned out twice to be exactly this - the hardware/wiring was
  # fine, only the app's persisted volume wasn't what was expected.
  force_test_volume "$card"
  echo "   Testlautstaerke fest auf ${TEST_VOLUME_PERCENT}% gesetzt (direkt am Mixer,"
  echo "   unabhaengig davon was die App/Datenbank gerade meint):"
  amixer -c "$card" sget "$ctl" 2>/dev/null | grep -E '^\s+(Mono|Front)' | sed 's/^/   /'
  echo

  echo "-- Testton (laeuft automatisch ein paar Sekunden) --"
  echo
  speaker-test -D "hw:$card,0" -c 2 -t sine -l 1 || true
  echo
  local track
  track="$(find "$INSTALL_DIR/media" -type f \( -iname '*.mp3' -o -iname '*.m4a' \
           -o -iname '*.ogg' -o -iname '*.wav' -o -iname '*.flac' \) 2>/dev/null | head -1 || true)"
  if [ -n "$track" ]; then
    echo "   Optional auch eine echte Datei aus der Bibliothek testen:"
    echo
    echo "        mpv --no-video --audio-device=alsa/hw:$card,0 \"$track\""
    echo
  fi
  echo "   War das eben zu hoeren - klar und ohne Knistern?"
}

# Short listening check used at every stage after "sound". Confirmed on real
# hardware: from here on owlbox.service is running, and its mpv instance
# holds the ALSA device open the whole time it's alive (--idle=yes) - a
# separate `speaker-test` process trying to open the same hw:X,Y device at
# the same time fails outright with "Device or resource busy" (see
# owlbox/feedback.py's own docstring, which already documents this same
# constraint for chime playback). So testing here can't just run
# speaker-test alongside the running service like the "sound" stage does -
# it stops owlbox.service first (freeing the device), runs the test, then
# starts it again automatically, the same stop-test-resume pattern
# run_test_tool already uses for the rfid/controls test tools.
listen_reminder() {
  local card="${1:-0}"
  echo
  echo "   Zur Kontrolle nochmal hoeren, ob der Ton noch genauso sauber ist"
  echo "   wie bei der vorherigen Stufe. owlbox.service haelt die Soundkarte"
  echo "   offen (mpv laeuft im Hintergrund) - wird dafuer kurz angehalten:"
  echo
  if [ "$DRYRUN" = "1" ]; then
    echo "   [dry-run] systemctl stop owlbox.service; speaker-test ...; systemctl start owlbox.service"
    return
  fi
  svc stop owlbox.service || true
  # Same fixed test volume as sound_check, set directly on the hardware
  # mixer - not through the app, and only possible now that owlbox.service
  # is stopped and no longer holds the ALSA device. Keeps every stage's
  # listening test comparable to the others regardless of what volume the
  # app/database happens to have (see sound_check's comment on why this
  # matters - confirmed on real hardware more than once).
  force_test_volume "$card"
  speaker-test -D "hw:$card,0" -c 2 -t sine -l 1 || true
  svc start owlbox.service
  echo
  echo "   Klang es anders/schlechter als bei der vorherigen Stufe -> die"
  echo "   gerade neu zugeschaltete Komponente ist die Ursache."
}

STAGE="${1:-}"

case "$STAGE" in
  sound)
    echo "== 1) Sound: nur der HiFiBerry Amp2 angeschlossen =="
    echo "   (noch kein Display, kein RC522, keine Taster/Encoder verkabelt)"
    apply simulated false null
    svc stop owlbox.service owlbox-kiosk.service || true
    sound_check
    echo
    echo "   Sauber? Dann Display anschliessen (DSI-Kabel + 4 Stromjumper,"
    echo "   siehe docs/hardware.md), danach: sudo owlbox-stage display"
    ;;
  display)
    echo "== 2) Display: + 7\"-Touch-Display (DSI) =="
    apply simulated false 13
    svc restart owlbox.service
    svc restart owlbox-kiosk.service
    echo
    echo "   Bildschirm sollte jetzt die Now-Playing-Anzeige zeigen."
    echo "   Helligkeit dabei einmal verstellen (Regler unter Einstellungen"
    echo "   im Web-UI, oder der zweite Dreh-Encoder sobald der verkabelt ist)"
    echo "   - wenn sich der Ton dabei aendert, ist die Backlight-PWM (GPIO 13)"
    echo "   die Ursache."
    listen_reminder
    echo
    echo "   Sauber? Dann RC522 anschliessen (siehe docs/hardware.md),"
    echo "   danach: sudo owlbox-stage rfid"
    ;;
  rfid)
    echo "== 3) RFID: + RC522-Leser =="
    apply mfrc522 false 13
    svc stop owlbox.service || true   # sonst kaempfen App und Testtool um dieselben GPIOs
    run_test_tool test_rfid.py "RFID"
    svc restart owlbox.service
    svc restart owlbox-kiosk.service
    listen_reminder
    echo
    echo "   Sauber und Chip wurde beim Test erkannt? Dann Taster/Encoder"
    echo "   anschliessen (siehe docs/hardware.md), danach:"
    echo "   sudo owlbox-stage controls"
    ;;
  controls)
    echo "== 4) Taster/Encoder: + Bedienelemente (= normaler Betrieb) =="
    apply mfrc522 false 13
    svc stop owlbox.service || true   # sonst kaempfen App und Testtool um dieselben GPIOs
    run_test_tool test_controls.py "Taster/Encoder"
    apply mfrc522 true 13
    svc enable owlbox.service || true
    # owlbox-kiosk.service was only ever `svc restart`ed by every stage
    # above, never enabled - install.sh deliberately copies the unit file
    # but leaves enabling it to this guided tool (see its comment next to
    # `cp .../owlbox-kiosk.service`), and until now nothing here actually
    # did that. Result: the kiosk display ran fine right after staging but
    # never came back on its own after the next reboot, since its
    # `WantedBy=multi-user.target` was never activated. Confirmed as the
    # real-world symptom, not just a theoretical gap.
    svc enable owlbox-kiosk.service || true
    svc restart owlbox.service
    svc restart owlbox-kiosk.service
    if [ "$DRYRUN" != "1" ] && [ -f "$STAGED_MARKER" ]; then
      rm -f "$STAGED_MARKER"
      echo "   Gestaffelte Einrichtung abgeschlossen - owlbox.service ist ab jetzt normal aktiviert."
    fi
    listen_reminder
    echo
    echo "   Vollstaendige normale Konfiguration aktiv. Fertig! Noch zu erledigen:"
    echo "   http://<pi-ip>:5000/admin oeffnen, Ersteinrichtung (Benutzername/"
    echo "   Passwort) durchlaufen, erste Geschichte hochladen und einem Chip zuweisen."
    ;;
  status|"")
    echo "== Aktueller Stand =="
    ;;
  *)
    echo "Unbekannte Stufe: $STAGE (erlaubt: sound display rfid controls status)" >&2
    exit 1
    ;;
esac

show_status
