#!/usr/bin/env bash
# Fully unattended install: one command, from an empty SD card (well, a
# freshly flashed Raspberry Pi OS Lite + this repo cloned) to a finished,
# already-logged-in-ready OwlBox - no SSHing back in after the reboot
# scripts/install.sh triggers, no browser-based Ersteinrichtung, no
# `owlbox-stage <name>` typed by hand. Run as root, from inside a checkout:
#
#   sudo ./scripts/autoinstall.sh
#
# For the project's standard hardware (see docs/hardware.md) fully wired
# BEFORE running this - unlike the guided scripts/stage.sh flow, there's no
# pause between stages to plug in the next component, since nobody's
# expected to be watching.
#
# What "unattended" means concretely, and why each piece was safe to
# automate (see docs/staged-setup.md for the guided, one-component-at-a-time
# alternative this replaces):
#
#   1. scripts/install.sh already never blocks on input - it only ever
#      reboots itself once (config.txt/cmdline.txt changes for all four
#      stages are coalesced into a single write, see install.sh's own
#      comment on that). This script survives that reboot itself, see the
#      resume mechanism below.
#   2. scripts/stage.sh's rfid/controls test tools already run
#      non-interactively too - they wait up to a few seconds for a
#      scan/button press to print in the terminal, then continue regardless
#      (`|| true`), same as if a human had watched and moved on. Nothing
#      here actually needed a person confirming anything.
#   3. The one genuinely manual step left was the browser-based
#      Ersteinrichtung (admin username/password) - replaced here by
#      scripts/create_admin.py, run non-interactively. See CREDENTIALS
#      below for how to control what account it creates.
#
# CREDENTIALS: to set a specific username/password instead of a random
# generated one, drop a file named exactly "owlbox-admin.txt" onto the
# boot partition (same place config.txt lives - /boot/firmware/ on current
# Raspberry Pi OS, plain /boot/ on older ones) BEFORE running this script:
#
#   username=eltern
#   password=dein-eigenes-passwort
#
# Without that file, create_admin.py generates a random password and this
# script writes it to /root/owlbox-admin-credentials.txt (root-only) - see
# the final summary this script prints for exactly where.
#
# RESUME ACROSS THE REBOOT: install_resume_unit() below installs a oneshot
# systemd unit (systemd/owlbox-autoinstall.service) that re-runs this exact
# script on the next boot, gated on a small state file
# (/var/lib/owlbox/.autoinstall-state) that only exists while a run is
# actually in progress - so a completed install's next, perfectly normal
# reboot doesn't re-trigger anything. The state machine below
# (install -> stage -> admin -> done) is idempotent at every step, the same
# design principle scripts/install.sh and scripts/stage.sh already both
# rely on - re-entering any step after an interruption just repeats cheap,
# already-safe work instead of needing to know exactly where it left off.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo ./scripts/autoinstall.sh" >&2
  exit 1
fi

# Resolves correctly whichever copy of this script is running - the user's
# own checkout on the very first invocation, or the rsynced copy under
# /opt/owlbox once BASE has run and the resume unit takes over after a
# reboot (see scripts/install.sh's BASE stage, which rsyncs the whole repo
# there early, well before the reboot at the very end).
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
# Unlike SCRIPT_DIR above, this is deliberately always the same fixed path
# regardless of which copy of this script is running - it's where the app
# actually lives/runs from once installed (venv, config.yaml, the database),
# matching scripts/install.sh's/scripts/stage.sh's own OWLBOX_INSTALL_DIR.
INSTALL_DIR="${OWLBOX_INSTALL_DIR:-/opt/owlbox}"
STATE_DIR="/var/lib/owlbox"
STATE_FILE="$STATE_DIR/.autoinstall-state"
UNIT_NAME="owlbox-autoinstall.service"
UNIT_PATH="/etc/systemd/system/$UNIT_NAME"

install_resume_unit() {
  mkdir -p "$STATE_DIR"
  # Copies from $SCRIPT_DIR (not a hardcoded /opt/owlbox source) so this
  # works even on the very first call, before BASE has rsynced anything -
  # systemd/ sits right next to scripts/ in both the checkout and, later,
  # in /opt/owlbox.
  cp "$SCRIPT_DIR/../systemd/owlbox-autoinstall.service" "$UNIT_PATH"
  systemctl daemon-reload
  systemctl enable "$UNIT_NAME" >/dev/null 2>&1 || true
}

remove_resume_unit() {
  systemctl disable "$UNIT_NAME" >/dev/null 2>&1 || true
  rm -f "$UNIT_PATH"
  systemctl daemon-reload
}

create_admin_account() {
  local cred_file="" username="" password=""
  for candidate in /boot/firmware/owlbox-admin.txt /boot/owlbox-admin.txt; do
    if [ -f "$candidate" ]; then
      cred_file="$candidate"
      break
    fi
  done
  if [ -n "$cred_file" ]; then
    username="$(sed -n 's/^username=//p' "$cred_file" | head -1)"
    password="$(sed -n 's/^password=//p' "$cred_file" | head -1)"
    echo "   Zugangsdaten aus $cred_file uebernommen."
  fi

  local out
  out="$(OWLBOX_ADMIN_USER="$username" OWLBOX_ADMIN_PASSWORD="$password" \
    "$INSTALL_DIR/.venv/bin/python3" "$INSTALL_DIR/scripts/create_admin.py")"

  if echo "$out" | grep -q '^SKIP'; then
    echo "   Verwaltungs-Zugang existiert bereits, nichts geaendert."
    return
  fi

  # root-only - this is a plaintext password at rest, same tradeoff every
  # "flash and forget" unattended-install tool (cloud-init etc.) makes; the
  # guided scripts/stage.sh flow (README.md's default recommendation)
  # avoids this entirely by never writing the password down anywhere.
  ( umask 077 && printf '%s\n' "$out" > /root/owlbox-admin-credentials.txt )
  echo "   Neuer Verwaltungs-Zugang angelegt. Zugangsdaten stehen in"
  echo "   /root/owlbox-admin-credentials.txt (nur root lesbar):"
  echo "$out" | sed 's/^/     /'
}

STATE="install"
[ -f "$STATE_FILE" ] && STATE="$(cat "$STATE_FILE")"

echo "==> [Autoinstall] Unbeaufsichtigte Installation - Fortschritt: $STATE"
install_resume_unit

while true; do
  case "$STATE" in
    install)
      echo
      echo "==> [Autoinstall] Schritt 1/3: OS-Vorbereitung (alle vier Stufen)"
      # If this changed config.txt/cmdline.txt it reboots the box itself and
      # this script's process ends right here, involuntarily - the resume
      # unit installed above re-runs this exact script on the next boot,
      # STATE is still "install" (never got the chance to advance below),
      # so it repeats this same call - which this time finds config.txt
      # already correct and returns normally instead of rebooting again.
      "$SCRIPT_DIR/install.sh" all
      STATE="stage"
      echo "$STATE" > "$STATE_FILE"
      ;;
    stage)
      echo
      echo "==> [Autoinstall] Schritt 2/3: Hardware scharf schalten (sound, display, rfid, controls)"
      for s in sound display rfid controls; do
        "$SCRIPT_DIR/stage.sh" "$s"
      done
      STATE="admin"
      echo "$STATE" > "$STATE_FILE"
      ;;
    admin)
      echo
      echo "==> [Autoinstall] Schritt 3/3: Verwaltungs-Zugang anlegen (ohne Browser)"
      create_admin_account
      STATE="done"
      echo "$STATE" > "$STATE_FILE"
      ;;
    done)
      break
      ;;
    *)
      echo "Unbekannter Zustand '$STATE' in $STATE_FILE - breche ab. Zum" >&2
      echo "manuellen Neustart die Datei loeschen und erneut versuchen." >&2
      exit 1
      ;;
  esac
done

remove_resume_unit
rm -f "$STATE_FILE"

IP="$("$INSTALL_DIR/.venv/bin/python3" -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); from owlbox.network import get_lan_ip; print(get_lan_ip())" 2>/dev/null || echo "<pi-ip>")"

cat <<EOF

==> Fertig - OwlBox ist vollstaendig eingerichtet und einsatzbereit.

    Verwaltung: http://$IP:5000/admin
    Zugangsdaten: siehe oben, bzw. jederzeit erneut in
      /root/owlbox-admin-credentials.txt (falls ein Zugang neu angelegt wurde)

    Noch zu erledigen (kein Skript kann das fuer dich tun): eine erste
    Geschichte in der Bibliothek hochladen und einem RFID-Chip zuweisen.
EOF
