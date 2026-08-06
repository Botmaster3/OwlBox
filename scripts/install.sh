#!/usr/bin/env bash
# Installs OwlBox onto a Raspberry Pi (tested against Raspberry Pi OS Bookworm/Legacy Lite).
# Run as root (sudo ./scripts/install.sh) from inside a checkout of this repo.
#
# Targets the project's standard hardware (see docs/hardware.md): Pi 3B+, HiFiBerry
# Amp2 (TAS5756M chip - the PCM512x family, same codec as the DAC+ Pro; NOT the
# older Amp/Amp+'s TAS5713, a different chip needing a different overlay), 3.5"
# SPI display (tft35a/MHS-35 family), RC522 on software SPI (GPIOs
# 4/14/15/16 - both hardware SPI buses are already taken by the display+touch and by
# the HiFiBerry's I2S audio), buttons/encoders on the documented default pins. On
# that combination this script alone gets you from a
# freshly-flashed SD card to a fully working box - no manual config.txt editing, no
# manually running aplay/amixer and copying values by hand, no manually compiling fbcp
# or wiring up systemd units. Two things stay manual on purpose:
#   - physically wiring the RC522/buttons/encoders/display (this is hardware, not software)
#   - the one-time admin login setup in the browser (no auto-generated default password)
#
# Deliberately targets "Legacy Lite" (no desktop environment at all) rather than the
# full "Legacy" desktop image: Chromium is the only thing that ever needs to appear on
# screen, so this script brings up just enough X (no display manager, no window manager
# desktop, no panel/file manager/screensaver a full desktop would otherwise start) via
# its own systemd service instead of lightdm+LXDE - that alone skips several seconds of
# boot time that would otherwise go into starting a desktop nothing ever looks at. A few
# more small, safe boot-time trims are applied for the same reason (see the "boot speed"
# section below): unneeded services disabled, network-wait-at-boot off, splash off.
#
# Idempotent and meant to be run TWICE with a reboot in between:
#   1st run: installs everything, edits config.txt (HiFiBerry + display + GL driver +
#            boot-speed tweaks), builds fbcp, installs the display's own driver/overlay
#            files, then reboots.
#   2nd run (after the reboot): the HiFiBerry sound card and display overlay are now
#            live, so this run auto-detects the ALSA device/mixer, writes them into
#            config.yaml, strips the display driver's touch overlay back out, and
#            finally starts owlbox.service and the kiosk display.
# Every step below checks what's already in place first, so running it more than
# twice (or after manually tweaking something) is always safe.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo ./scripts/install.sh" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/owlbox"
SERVICE_USER="owlbox"

MARKER_BEGIN="# --- OwlBox: begin (managed by scripts/install.sh - re-running the script"
MARKER_BEGIN="$MARKER_BEGIN replaces everything between these two markers) ---"
MARKER_END="# --- OwlBox: end ---"

CONFIG_TXT=""
for candidate in /boot/firmware/config.txt /boot/config.txt; do
  [ -f "$candidate" ] && { CONFIG_TXT="$candidate"; break; }
done

# -- helpers --------------------------------------------------------------

# Replaces the whole OwlBox-managed block (deleting any previous one first) so
# re-running the script always converges to exactly this set of lines, instead
# of accumulating duplicates or fighting a hand-edited version of an old block.
write_config_block() {
  local file="$1"; shift
  local tmp
  tmp="$(mktemp)"
  awk -v b="$MARKER_BEGIN" -v e="$MARKER_END" '
    $0==b {skip=1}
    !skip {print}
    $0==e {skip=0}
  ' "$file" | awk '
    # Trims trailing blank lines left over from the previous blocks
    # separator - without this a re-run would grow one more blank line
    # before the block every time instead of converging to a fixed point.
    {lines[NR]=$0}
    END {
      n=NR
      while (n>0 && lines[n]=="") n--
      for (i=1;i<=n;i++) print lines[i]
    }
  ' > "$tmp"
  {
    cat "$tmp"
    echo ""
    echo "$MARKER_BEGIN"
    printf '%s\n' "$@"
    echo "$MARKER_END"
  } > "$file"
  rm -f "$tmp"
}

echo "==> Installing system packages"
apt-get update
apt-get install -y \
  python3-venv python3-pip python3-dev build-essential \
  mpv alsa-utils \
  git curl cmake \
  unclutter \
  fonts-noto-color-emoji \
  || true
# fonts-noto-color-emoji above: "Legacy Lite" has no emoji-capable font at all
# out of the box, so every 🦉/😴/▶️/etc. in the kiosk UI renders as an empty
# box ("tofu") instead - confirmed on real hardware.
# Debian's chromium package name varies by release; try both.
apt-get install -y chromium-browser || apt-get install -y chromium || true

# Belt-and-suspenders against the "German/English" translate bar Chromium
# shows on first load: kiosk.sh's --disable-features=Translate command-line
# flag alone did NOT actually suppress it on real hardware (confirmed) - this
# managed policy is the mechanism Chromium itself documents for kiosk/
# enterprise deployments, and covers both possible package/policy directory
# names depending on which of the two chromium packages above got installed.
mkdir -p /etc/chromium/policies/managed /etc/chromium-browser/policies/managed
for policy_dir in /etc/chromium/policies/managed /etc/chromium-browser/policies/managed; do
  cat > "$policy_dir/owlbox.json" <<'EOF'
{
  "TranslateEnabled": false
}
EOF
done

# Needed to build fbcp against the legacy VideoCore firmware interface.
apt-get install -y libraspberrypi-dev || true
# Minimal X stack for the kiosk display - deliberately no desktop environment
# (no lightdm, no LXDE) on top of the "Legacy Lite" base image. xserver-xorg-legacy
# provides the Xwrapper.config mechanism needed to start X without a display
# manager; matchbox-window-manager is tiny but keeps things well-behaved if a
# stray JS alert()/confirm() window ever pops up in Chromium. xserver-xorg-video-fbdev
# is required because of the Legacy GL driver this project needs for fbcp (see
# below): with the modern KMS driver commented out of config.txt, there is no
# /dev/dri/card0 for X's default "modesetting" driver to use at all, so X would
# otherwise fail immediately with "no screens found" - it needs to be told to
# draw straight to the framebuffer instead (see the Xorg config written further
# down).
apt-get install -y \
  xserver-xorg xserver-xorg-legacy xserver-xorg-video-fbdev xinit x11-xserver-utils \
  matchbox-window-manager \
  || true

echo "==> Enabling SPI (needed for the RC522 RFID reader and the display)"
if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_spi 0 || true
else
  echo "raspi-config not found, enable SPI manually: add 'dtparam=spi=on' to $CONFIG_TXT" >&2
fi

echo "==> Boot-speed trims (disabling services this box never uses)"
for svc in bluetooth hciuart triggerhappy ModemManager dphys-swapfile; do
  systemctl disable --now "$svc" >/dev/null 2>&1 || true
done
# The kiosk takes over tty1 directly (see the "kiosk autostart" section below),
# so the text-login getty on it would just be wasted work/RAM, never actually usable.
systemctl disable getty@tty1.service >/dev/null 2>&1 || true
if command -v raspi-config >/dev/null 2>&1; then
  # Don't block the rest of boot waiting for the network to come up - OwlBox
  # and the kiosk start independently of whether WLAN has associated yet.
  raspi-config nonint do_boot_wait 1 || true
fi

echo "==> Creating service user '$SERVICE_USER'"
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
for grp in gpio spi audio video i2c; do
  groupadd -f "$grp"
  usermod -aG "$grp" "$SERVICE_USER" || true
done

echo "==> Granting passwordless sudo for shutdown/WLAN/service-restart"
# owlbox.service runs as this user with no terminal attached, so sudo can
# never prompt for a password here. The Update-Button (Info-Seite), WLAN
# Ein/Aus/Hotspot (Einstellungen), and "Pi neu starten"/"herunterfahren"
# (Einstellungen bzw. Funktions-Chip) all shell out to sudo from inside
# owlbox.service. sudo matches the *entire* command line it's given, not
# just the program name - these three rules must stay in exact sync with
# what owlbox/update.py, owlbox/network.py and owlbox/engine.py actually
# invoke (confirmed on real hardware: a stray extra flag like --no-block
# that isn't also in the sudoers rule makes sudo fall back to a password
# prompt, which then just fails outright). Written to a temp file and
# syntax-checked with visudo before being installed - a broken file in
# sudoers.d can lock out sudo entirely, so it's never written to
# /etc/sudoers.d directly.
SUDOERS_TMP="$(mktemp)"
cat > "$SUDOERS_TMP" <<EOF
$SERVICE_USER ALL=(ALL) NOPASSWD: /sbin/shutdown, /usr/bin/nmcli, /usr/bin/systemctl restart --no-block owlbox
EOF
if visudo -c -f "$SUDOERS_TMP" >/dev/null 2>&1; then
  install -m 0440 -o root -g root "$SUDOERS_TMP" /etc/sudoers.d/owlbox
else
  echo "WARNUNG: sudoers-Regel ungültig, wurde NICHT installiert - siehe docs/hardware.md." >&2
fi
rm -f "$SUDOERS_TMP"

echo "==> Copying application to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude ".venv" --exclude "data" --exclude "__pycache__" "$REPO_DIR"/ "$INSTALL_DIR"/

echo "==> Creating Python virtualenv"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

if [ ! -f "$INSTALL_DIR/config/config.yaml" ]; then
  cp "$INSTALL_DIR/config/config.example.yaml" "$INSTALL_DIR/config/config.yaml"
  echo "==> Wrote default config/config.yaml"
fi

mkdir -p "$INSTALL_DIR/media" "$INSTALL_DIR/data"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/kiosk.sh"

# -- HiFiBerry Amp2 + display + GL driver (config.txt) ---------------------

NEEDS_REBOOT=0
DISPLAY_DRIVER_INSTALLED=0

if [ -n "$CONFIG_TXT" ]; then
  echo "==> Configuring audio (HiFiBerry Amp2) and display in $CONFIG_TXT"
  BEFORE_HASH="$(sha256sum "$CONFIG_TXT" | cut -d' ' -f1)"

  # Onboard audio off in favour of the HiFiBerry: no separate sed pass needed
  # for a pre-existing "dtparam=audio=on" line - the managed block below
  # already appends its own "dtparam=audio=off" at the *end* of the file, and
  # the Pi's config.txt parser takes the last occurrence of a given dtparam
  # as authoritative, so it wins regardless of what an earlier line said.
  # (A previous version of this script also sed'd the original line in place
  # AND relied on the managed block, so a stock image's "dtparam=audio=on"
  # line ended up converted to "off" twice - harmless duplication, but
  # confusing to find in config.txt; fixed by just not doing that redundant
  # pass anymore.)

  # "Legacy" GL driver: fbcp needs /dev/fb0, which the modern KMS/Fake-KMS
  # driver doesn't expose in a usable form - comment out whichever is active.
  sed -i -E 's/^(dtoverlay=vc4-f?kms-v3d.*)/#\1/' "$CONFIG_TXT"

  # HiFiBerry Amp2's TAS5756M chip is PCM512x-family (same codec as the DAC+
  # Pro) - confirmed on real hardware via a failed I2C probe on the
  # TAS5713-specific "hifiberry-amp" overlay (wrong chip entirely) followed
  # by an i2cdetect scan showing a live device at 0x4d, the PCM512x family's
  # address. "hifiberry-amp" is for the older Amp/Amp+'s TAS5713 instead -
  # different chip, different overlay, even though the products are easy to
  # confuse by name.
  write_config_block "$CONFIG_TXT" \
    "dtparam=audio=off" \
    "dtoverlay=hifiberry-dacplus" \
    "disable_splash=1" \
    "boot_delay=0"

  AFTER_HASH="$(sha256sum "$CONFIG_TXT" | cut -d' ' -f1)"
  [ "$BEFORE_HASH" != "$AFTER_HASH" ] && NEEDS_REBOOT=1

  # 3.5" SPI display driver (tft35a/MHS-35 family, see docs/hardware.md) - this
  # is the one piece delegated to the display's own installer rather than
  # reimplemented here, because it ships a device-tree overlay *binary* this
  # script has no reliable way to reproduce on its own. Only run it once: it
  # edits config.txt itself and reboots at the end, and running it again on
  # top of an already-patched config.txt is the installer's problem to be
  # idempotent about, not guaranteed.
  # NOTE: MHS35-show (the installer actually invoked below) writes
  # "dtoverlay=mhs35:..." to config.txt, not "tft35a" - checking for the
  # wrong string here meant this "already installed?" gate never matched,
  # so the driver installer (which reboots the Pi on its own at the end)
  # ran on *every* install.sh invocation, killing the script before it ever
  # reached the later kiosk-autostart section - confirmed on real hardware.
  if ! grep -q "dtoverlay=mhs35" "$CONFIG_TXT" 2>/dev/null; then
    echo "==> Installing the 3.5\" SPI display driver (goodtft/LCD-show)"
    if git clone --depth 1 https://github.com/goodtft/LCD-show.git /tmp/LCD-show; then
      chmod +x /tmp/LCD-show/MHS35-show
      # The installer reboots on its own once done; NEEDS_REBOOT is moot after
      # this point but kept accurate in case the clone/install fails instead.
      DISPLAY_DRIVER_INSTALLED=1
    else
      echo "WARNUNG: Display-Treiber-Repo konnte nicht geladen werden (kein Internet?)." >&2
      echo "         Manuell nachholen, siehe OwlBox-Verkabelung.pdf Kapitel 8." >&2
    fi
  fi
else
  echo "WARNUNG: config.txt nicht gefunden (weder /boot/firmware/config.txt noch /boot/config.txt)." >&2
  echo "         HiFiBerry-/Display-Overlays konnten nicht automatisch gesetzt werden - siehe docs/hardware.md." >&2
fi

# -- fbcp (mirrors the framebuffer onto the SPI display) --------------------

if ! command -v fbcp >/dev/null 2>&1; then
  echo "==> Building fbcp"
  if [ -d /tmp/rpi-fbcp ]; then rm -rf /tmp/rpi-fbcp; fi
  if git clone --depth 1 https://github.com/tasanakorn/rpi-fbcp.git /tmp/rpi-fbcp; then
    mkdir -p /tmp/rpi-fbcp/build
    (cd /tmp/rpi-fbcp/build && cmake .. && make)
    install -m 0755 /tmp/rpi-fbcp/build/fbcp /usr/local/bin/fbcp
    rm -rf /tmp/rpi-fbcp
  else
    echo "WARNUNG: fbcp konnte nicht gebaut werden (kein Internet? fehlende Build-Header?)." >&2
    echo "         Manuell nachholen, siehe OwlBox-Verkabelung.pdf Kapitel 8." >&2
  fi
fi
if command -v fbcp >/dev/null 2>&1; then
  cp "$INSTALL_DIR/systemd/owlbox-fbcp.service" /etc/systemd/system/owlbox-fbcp.service
  systemctl daemon-reload
  systemctl enable owlbox-fbcp.service
  # Not started yet on a first run - the display overlay only becomes active
  # after the reboot triggered below/by the display installer.
fi

# -- kiosk autostart (minimal X + Chromium, no desktop environment) --------
# Runs as its own system-level systemd service (owlbox-kiosk.service), which
# takes tty1 over directly (PAMName=login/TTYPath) and starts X itself via
# `startx` - there is no display manager and no desktop session to hook into
# on this deliberately minimal "Legacy Lite" base image.

echo "==> Setting up kiosk autostart (minimal X, no desktop environment)"
cat > /etc/X11/Xwrapper.config <<'EOF'
allowed_users=anybody
needs_root_rights=yes
EOF

# With the Legacy GL driver (no /dev/dri/card0, see above), X's default
# auto-probed "modesetting" driver finds no usable device at all and fails
# outright with "no screens found" - tell it explicitly to draw straight to
# the framebuffer fbcp already mirrors the display onto instead.
mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/99-owlbox-fbdev.conf <<'EOF'
Section "Device"
    Identifier "OwlBoxFramebuffer"
    Driver "fbdev"
    Option "fbdev" "/dev/fb0"
EndSection

Section "Screen"
    Identifier "OwlBoxScreen"
    Device "OwlBoxFramebuffer"
EndSection
EOF

cp "$INSTALL_DIR/systemd/owlbox-kiosk.service" /etc/systemd/system/owlbox-kiosk.service
systemctl daemon-reload
systemctl enable owlbox-kiosk.service
# Not started with --now here: the display overlay/GL driver only become
# live after the reboot this script asks for below, so a first-run start
# attempt would just fail against a framebuffer that isn't ready yet. It's
# started (best-effort) at the very end once that reboot has happened - see
# the owlbox-fbcp.service start line further down for the same pattern.

# -- audio auto-detection (only meaningful once the HiFiBerry is live) ------

AUDIO_CONFIGURED=0
if command -v aplay >/dev/null 2>&1 && aplay -l 2>/dev/null | grep -qi hifiberry; then
  CARD_NUM="$(aplay -l | grep -i hifiberry | head -n1 | sed -n 's/^card \([0-9]*\).*/\1/p')"
  if [ -n "$CARD_NUM" ]; then
    ALSA_DEVICE="hw:$CARD_NUM,0"
    MIXER_CONTROL="Digital"
    if amixer -c "$CARD_NUM" scontrols 2>/dev/null | grep -qi "'PCM'" \
       && ! amixer -c "$CARD_NUM" scontrols 2>/dev/null | grep -qi "'Digital'"; then
      MIXER_CONTROL="PCM"
    fi
    echo "==> HiFiBerry erkannt (Karte $CARD_NUM) - trage $ALSA_DEVICE / $MIXER_CONTROL / Karte $CARD_NUM in config.yaml ein"
    # Targeted line-replace instead of a full YAML parse/dump round-trip -
    # config.yaml's inline comments (the whole point of the shipped example
    # file) would otherwise get silently dropped by a re-serialize.
    sed -i -E "s/^(\s*alsa_device:).*/\1 \"$ALSA_DEVICE\"/" "$INSTALL_DIR/config/config.yaml"
    sed -i -E "s/^(\s*mixer_control:).*/\1 \"$MIXER_CONTROL\"/" "$INSTALL_DIR/config/config.yaml"
    # mixer_card used to be left at its config.example.yaml default ("0")
    # here - harmless if the HiFiBerry really is card 0, but on any Pi where
    # it isn't (confirmed on real hardware: alsa_device correctly ends up
    # "hw:2,0", mixer_card silently stays "0"), every amixer volume get/set
    # in player.py's AlsaMixer targets the wrong (or a non-existent) card.
    # get_percent() then finds no matching mixer line and falls back to 0 -
    # looks exactly like "the volume I set never sticks, always shows 0".
    sed -i -E "s/^(\s*mixer_card:).*/\1 \"$CARD_NUM\"/" "$INSTALL_DIR/config/config.yaml"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/config/config.yaml"
    AUDIO_CONFIGURED=1
  fi

  # Second run and the display driver installer has already run before: some
  # LCD-show variants write a separate ads7846 touch overlay line that can
  # now be safely removed (harmless to run repeatedly). Note: the mhs35
  # overlay this project actually installs bundles its touch node directly
  # inside "dtoverlay=mhs35:..." instead, with no parameter to disable it -
  # this doesn't free up SPI0 CE1, which is why the RC522 runs on software
  # SPI (see docs/hardware.md) rather than sharing SPI0 with the display.
  if [ -n "$CONFIG_TXT" ] && grep -q "^dtoverlay=ads7846" "$CONFIG_TXT" 2>/dev/null; then
    echo "==> Removing the touch overlay line (touch stays off on purpose)"
    sed -i '/^dtoverlay=ads7846/d' "$CONFIG_TXT"
  fi
fi

echo "==> Installing systemd service"
cp "$INSTALL_DIR/systemd/owlbox.service" /etc/systemd/system/owlbox.service
systemctl daemon-reload
systemctl enable --now owlbox.service
[ "$(systemctl is-active owlbox-fbcp.service 2>/dev/null || true)" != "active" ] \
  && systemctl start owlbox-fbcp.service 2>/dev/null || true
[ "$(systemctl is-active owlbox-kiosk.service 2>/dev/null || true)" != "active" ] \
  && systemctl start owlbox-kiosk.service 2>/dev/null || true

# -- summary -----------------------------------------------------------------

cat <<EOF

==> owlbox.service installiert und gestartet (systemctl status owlbox).
EOF

if [ "$DISPLAY_DRIVER_INSTALLED" -eq 1 ]; then
  cat <<'EOF'

==> Installiere Display-Treiber (Ausgabe des Installers folgt) ...
EOF
  # Not `exec`'d on purpose: goodtft/LCD-show usually reboots on its own once
  # done, but if it doesn't (or only prompts instead), falling straight
  # through to our own explicit "please reboot" message below still gets you
  # there instead of silently stopping short.
  ( cd /tmp/LCD-show && ./MHS35-show ) || true
  cat <<EOF

==> Display-Treiber-Installation abgeschlossen. Falls der Pi sich nicht schon
    von selbst neu gestartet hat, jetzt bitte manuell:
      sudo reboot
    Nach dem Neustart dieses Skript per SSH einmal erneut ausführen
    (sudo ./scripts/install.sh) - dann werden ALSA-Gerät/Mixer automatisch
    erkannt und eingetragen, die Touch-Overlay-Zeile wieder entfernt, und der
    Kiosk-Autostart aktiviert.
EOF
elif [ "$NEEDS_REBOOT" -eq 1 ] || [ "$AUDIO_CONFIGURED" -eq 0 ]; then
  cat <<EOF

==> config.txt wurde geändert - bitte jetzt neu starten:
      sudo reboot
    Danach dieses Skript einmal erneut ausführen, um die Audio-Erkennung und
    den Kiosk-Autostart abzuschließen:
      sudo ./scripts/install.sh
EOF
else
  cat <<EOF

==> Alles eingerichtet. Noch zu erledigen (kein Skript kann das für dich tun):
  1. RC522-RFID-Leser (an CE1, nicht CE0), beide Taster und beide Dreh-Encoder
     verkabeln - siehe OwlBox-Verkabelung.pdf.
  2. http://<pi-ip>:5000/admin öffnen, Ersteinrichtung (Benutzername/Passwort)
     durchlaufen, erste Geschichte hochladen und einem Chip zuweisen.
EOF
fi
