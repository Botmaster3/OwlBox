#!/usr/bin/env bash
# Installs OwlBox onto a Raspberry Pi (tested against Raspberry Pi OS Bookworm/Legacy Lite).
# Run as root (sudo ./scripts/install.sh) from inside a checkout of this repo.
#
# Targets the project's standard hardware (see docs/hardware.md): Pi 3B+, HiFiBerry
# Amp2 (TAS5756M chip - the PCM512x family, same codec as the DAC+ Pro; NOT the
# older Amp/Amp+'s TAS5713, a different chip needing a different overlay), the
# official 7" Raspberry Pi Touch Display (DSI ribbon cable + 4 jumper wires for
# power/I2C touch - see docs/hardware.md), RC522 on software SPI (GPIOs
# 4/14/15/16 - SPI0 is free since the display no longer uses it, but the RC522
# stays on software SPI regardless, see docs/hardware.md for why), buttons/
# encoders on the documented default pins. On that combination this script
# alone gets you from a freshly-flashed SD card to a fully working box - no
# manual config.txt editing, no manually running aplay/amixer and copying
# values by hand, no wiring up systemd units. Two things stay manual on purpose:
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
#   1st run: installs everything, edits config.txt (HiFiBerry + boot-speed tweaks +
#            display_lcd_rotate for the physically upside-down display - the
#            DSI display itself is otherwise auto-detected, no overlay needed
#            for that part), then reboots.
#   2nd run (after the reboot): the HiFiBerry sound card is now live, so this run
#            auto-detects the ALSA device/mixer, writes it into config.yaml, and
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

CMDLINE_TXT=""
for candidate in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
  [ -f "$candidate" ] && { CMDLINE_TXT="$candidate"; break; }
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

# Minimal X stack for the kiosk display - deliberately no desktop environment
# (no lightdm, no LXDE) on top of the "Legacy Lite" base image. xserver-xorg-legacy
# provides the Xwrapper.config mechanism needed to start X without a display
# manager; matchbox-window-manager is tiny but keeps things well-behaved if a
# stray JS alert()/confirm() window ever pops up in Chromium. No fbdev/legacy GL
# driver package needed here: the official DSI touch display works with the
# modern KMS driver (vc4-kms-v3d, the Bookworm default) active, so X's own
# default "modesetting" driver finds /dev/dri/card0 and just works - unlike the
# old 3.5" SPI display, which needed the Legacy GL driver + a hand-written
# fbdev Xorg config because fbcp (mirroring onto that display) needed /dev/fb0,
# which the modern KMS driver doesn't expose in a usable form.
apt-get install -y \
  xserver-xorg xserver-xorg-legacy xinit x11-xserver-utils \
  matchbox-window-manager \
  || true

echo "==> Enabling SPI (needed for the RC522 RFID reader)"
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
for grp in gpio spi audio video i2c render; do
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

# Stable re-run command, independent of which directory (or which checkout)
# this script was originally invoked from: confirmed on real hardware that
# "cd owlbox" from inside an already-checked-out repo silently lands one
# level too deep in the owlbox/owlbox Python package (it shares its name
# with the repo root), after which "./scripts/install.sh" fails with
# "command not found" - the fix above (removing a stray, non-,noaudio
# dtoverlay=vc4-kms-v3d line) never got a chance to run because of exactly
# this, even though `git pull` itself had succeeded. A stable symlink into
# the synced-to-/opt/owlbox copy sidesteps the whole class of mistake: this
# always re-runs the current install, from any cwd, no `cd`/checkout-path
# guessing required.
ln -sf "$INSTALL_DIR/scripts/install.sh" /usr/local/bin/owlbox-install
echo "==> Re-runs from now on: sudo owlbox-install (works from any directory)"

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

# -- HiFiBerry Amp2 (config.txt) --------------------------------------------
# The official 7" DSI Touch Display needs NO config.txt entry at all - it's
# auto-detected over the DSI ribbon cable by the Pi's own firmware, and it
# works fine with the modern KMS driver (vc4-kms-v3d, the Bookworm default)
# active - unlike the old 3.5" SPI display this project used to target, which
# needed the Legacy GL driver plus fbcp plus a whole separate driver-installer
# repo (see git history / docs/hardware.md's older revisions for that if ever
# needed again). All that's left to manage here is the audio overlay.

NEEDS_REBOOT=0

if [ -n "$CONFIG_TXT" ]; then
  echo "==> Configuring audio (HiFiBerry Amp2) in $CONFIG_TXT"
  BEFORE_HASH="$(sha256sum "$CONFIG_TXT" | cut -d' ' -f1)"

  # Onboard audio off in favour of the HiFiBerry: an earlier version of this
  # script assumed a pre-existing "dtparam=audio=on" line was harmless to
  # leave in place, on the theory that the Pi's config.txt parser takes the
  # last occurrence of a given dtparam as authoritative, so the managed
  # block's own "dtparam=audio=off" at the end of the file would win
  # regardless. Confirmed on real hardware that this "last one wins" theory
  # doesn't reliably hold in practice - the onboard "bcm2835 Headphones" ALSA
  # card kept reappearing in aplay -l across reboots even with the managed
  # block's dtparam=audio=off correctly present and last in the file. Same
  # fix as for the vc4-kms-v3d duplicate below: don't rely on override
  # semantics, just remove every pre-existing "dtparam=audio=on" line so
  # there's nothing left to (maybe) win over.

  # Clean up leftover config.txt lines from a previous install targeting the
  # old 3.5" SPI display (tft35a/MHS-35 overlay, its forced virtual-HDMI mode,
  # its ads7846 touch line) - harmless to run on a config.txt that never had
  # them, but leaving them in place on an upgrade would make the kernel keep
  # trying to init display hardware that's no longer physically connected.
  #
  # Also strip any OTHER "dtoverlay=vc4-kms-v3d" line, with or without its
  # own params, wherever it occurs in the file - THE actual reason the
  # ",noaudio" fix below kept not working on real hardware even after it was
  # added: stock Raspberry Pi OS Bookworm images already ship an active,
  # uncommented "dtoverlay=vc4-kms-v3d" line outside this script's managed
  # block (near the end of config.txt, under an "[all]" section). Each
  # "dtoverlay=" line applies that overlay as its own independent action
  # rather than overriding an earlier one, so the stock line kept registering
  # the vc4hdmi ALSA card (no ",noaudio" on IT) regardless of the corrected
  # line this script appended afterwards - crackling persisted because the
  # conflicting HDMI-audio registration was still happening, just from a
  # second, untouched source. Confirmed on real hardware: `aplay -l` still
  # showed "card N: vc4hdmi" after a reboot even with the managed block's
  # ",noaudio" line present. Same story for "dtparam=audio=on" (see above) -
  # deleting every pre-existing occurrence of both here, before the managed
  # block re-adds exactly one correct copy of each below, is the only way to
  # guarantee there isn't a second, still-active source of either.
  sed -i -E '/^dtoverlay=mhs35/d; /^dtoverlay=tft35a/d; /^dtoverlay=ads7846/d; /^hdmi_force_hotplug=/d; /^hdmi_group=/d; /^hdmi_mode=/d; /^hdmi_cvt=/d; /^hdmi_drive=/d; /^dtoverlay=vc4-kms-v3d(,.*)?$/d; /^dtparam=audio=on$/d' "$CONFIG_TXT"

  # HiFiBerry Amp2's TAS5756M chip is PCM512x-family (same codec as the DAC+
  # Pro) - confirmed on real hardware via a failed I2C probe on the
  # TAS5713-specific "hifiberry-amp" overlay (wrong chip entirely) followed
  # by an i2cdetect scan showing a live device at 0x4d, the PCM512x family's
  # address. "hifiberry-amp" is for the older Amp/Amp+'s TAS5713 instead -
  # different chip, different overlay, even though the products are easy to
  # confuse by name.
  # dtoverlay=vc4-kms-dsi-7inch: THE actual, official overlay for this
  # display under KMS - confirmed on real hardware that without it, the DSI
  # panel node/bridge never gets instantiated at all ("[drm] Cannot find any
  # crtc or sizes" in dmesg, screen stays black) - vc4-kms-v3d alone only
  # enables the base KMS driver, it doesn't know this specific panel's
  # timings on its own.
  # No touch params (invx/invy/swapxy) added on top: confirmed on real
  # hardware that once the video itself is rotated 180° via the cmdline.txt
  # kernel parameter below, touch input already tracks correctly on its
  # own (X11/libinput applies its own coordinate transform to match the
  # rotated output) - adding invx+invy here on top double-corrected it,
  # showing up as touch mirrored on both axes relative to the now-correct
  # picture. (There's no "rotate=" param for this overlay at all, for the
  # record - /boot/firmware/overlays/README lists only sizex/sizey/invx/
  # invy/swapxy/disable_touch/dsi0 - an earlier attempt with "rotate=180"
  # tacked on here was silently ignored, no error, no effect, which is why
  # the actual video flip has to be the cmdline.txt kernel parameter below
  # instead.) This overlay also covers the touch controller (ft5406-family)
  # itself, no separate rpi-ft5406 overlay line needed.
  #
  # NOT via xrandr or display_lcd_rotate either for the video flip itself:
  # confirmed on real hardware that xrandr's --rotate is silently accepted
  # (shows up in `xrandr --query`) but never changes what's on screen, and
  # the older display_lcd_rotate/lcd_rotate params are documented to do
  # nothing under KMS.
  # dtoverlay=vc4-kms-v3d / dtparam=spi=on / dtparam=i2c_arm=on: set explicitly
  # here rather than relying on them already being present elsewhere in
  # config.txt (a previous version of this script only ever *uncommented* a
  # pre-existing vc4-kms-v3d line via sed, assuming the base image's default
  # content would still be there) - confirmed on real hardware that
  # config.txt can end up missing all of its non-OwlBox-managed content
  # (seen after what looked like an unclean shutdown - /boot/firmware is
  # FAT32, which tolerates that far worse than ext4), silently leaving the
  # KMS driver never enabled and the screen black with no obvious error.
  # Safe to always (re-)assert these here regardless of what else is/isn't
  # in the file: dtoverlay lines for different overlays are additive, not
  # exclusive, so this can't conflict with anything else in config.txt.
  #
  # ,noaudio on vc4-kms-v3d: THE actual root cause of the day-long "digital
  # path is fine but playback is crackling/fragmented" saga - confirmed on
  # real hardware. Without it, vc4-kms-v3d also registers its own HDMI audio
  # ALSA card (showed up as "card 2: vc4hdmi" in `aplay -l` the whole time)
  # even though this project never uses HDMI audio at all - display is DSI,
  # audio is exclusively the HiFiBerry. That HDMI-audio registration
  # apparently contends with the HiFiBerry's I2S path (both ultimately go
  # through the same VC4 I2S/audio hardware block) closely enough to explain
  # everything that was chased today: the recurring pcm512x I2C errors
  # (snd_soc_component_update_bits ... -5, snd_soc_pcm_component_pm_
  # runtime_get ... -22) and the audible crackling/fragments, all while the
  # signal path itself (ALSA hw_params, mixer levels, I2C addressing)
  # checked out correct every single time. None of the other things tried
  # first (Auto Mute, disable-bt, runtime-PM sysfs override, a from-scratch
  # SD card reflash) touched this because none of them address vc4-kms-v3d
  # claiming the audio side of that shared hardware block in the first
  # place. Confirmed fixed on real hardware.
  write_config_block "$CONFIG_TXT" \
    "dtparam=audio=off" \
    "dtoverlay=hifiberry-dacplus" \
    "disable_splash=1" \
    "boot_delay=0" \
    "dtoverlay=vc4-kms-v3d,noaudio" \
    "dtparam=spi=on" \
    "dtparam=i2c_arm=on" \
    "dtoverlay=vc4-kms-dsi-7inch"

  AFTER_HASH="$(sha256sum "$CONFIG_TXT" | cut -d' ' -f1)"
  [ "$BEFORE_HASH" != "$AFTER_HASH" ] && NEEDS_REBOOT=1
else
  echo "WARNUNG: config.txt nicht gefunden (weder /boot/firmware/config.txt noch /boot/config.txt)." >&2
  echo "         HiFiBerry-Overlay konnte nicht automatisch gesetzt werden - siehe docs/hardware.md." >&2
fi

# The 180° *video* flip for the physically upside-down 7" Touch Display has
# to be a kernel command-line parameter, not anything in config.txt - the
# vc4-kms-dsi-7inch overlay has no "rotate=" param at all (confirmed against
# /boot/firmware/overlays/README: only sizex/sizey/invx/invy/swapxy/
# disable_touch/dsi0 exist), and xrandr/display_lcd_rotate are both
# confirmed ineffective under KMS (see above). cmdline.txt is a single line,
# space-separated - appended in place rather than via write_config_block's
# marker-based approach, which assumes a multi-line file.
if [ -n "$CMDLINE_TXT" ]; then
  if ! grep -q "video=DSI-1" "$CMDLINE_TXT"; then
    echo "==> Adding 180° video rotation to $CMDLINE_TXT"
    CMDLINE_BEFORE="$(cat "$CMDLINE_TXT")"
    printf '%s %s\n' "$CMDLINE_BEFORE" "video=DSI-1:800x480@60,rotate=180" > "$CMDLINE_TXT"
    NEEDS_REBOOT=1
  fi
else
  echo "WARNUNG: cmdline.txt nicht gefunden (weder /boot/firmware/cmdline.txt noch /boot/cmdline.txt)." >&2
  echo "         Bild-Rotation konnte nicht automatisch gesetzt werden - siehe docs/hardware.md." >&2
fi

# Remove any leftover fbcp service/binary from a previous install targeting
# the old 3.5" SPI display - it's not needed at all for the DSI display and
# would otherwise keep running, uselessly mirroring a framebuffer nothing
# reads from anymore.
systemctl disable --now owlbox-fbcp.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/owlbox-fbcp.service /usr/local/bin/fbcp
rm -f /etc/X11/xorg.conf.d/99-owlbox-fbdev.conf

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

# No custom Xorg driver config needed: with KMS active (see above), X's
# default "modesetting" driver finds /dev/dri/card0 on its own - unlike the
# old 3.5" SPI display, which needed to be told to draw straight to a
# framebuffer instead (that config file is actively removed above if present
# from a previous install; leaving it in place here would fight the KMS
# driver we now want active).

cp "$INSTALL_DIR/systemd/owlbox-kiosk.service" /etc/systemd/system/owlbox-kiosk.service
systemctl daemon-reload
systemctl enable owlbox-kiosk.service
# Not started with --now here: the KMS driver only becomes live after the
# reboot this script asks for below (if the audio overlay changed anything),
# so a first-run start attempt could fail against a driver that isn't loaded
# yet. It's started (best-effort) at the very end once that reboot has
# happened - see the owlbox.service start line further down.

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
fi

echo "==> Installing systemd service"
cp "$INSTALL_DIR/systemd/owlbox.service" /etc/systemd/system/owlbox.service
systemctl daemon-reload
systemctl enable --now owlbox.service
[ "$(systemctl is-active owlbox-kiosk.service 2>/dev/null || true)" != "active" ] \
  && systemctl start owlbox-kiosk.service 2>/dev/null || true

# -- summary -----------------------------------------------------------------

cat <<EOF

==> owlbox.service installiert und gestartet (systemctl status owlbox).
EOF

if [ "$NEEDS_REBOOT" -eq 1 ]; then
  cat <<EOF

==> config.txt wurde geändert - starte in 10 Sekunden neu (Strg+C zum Abbrechen).
    Nach dem Neustart dieses Skript einmal erneut ausführen, um die
    Audio-Erkennung und den Kiosk-Autostart abzuschließen:
      sudo owlbox-install
EOF
  # Confirmed on real hardware: leaving this as a printed instruction rather
  # than actually rebooting meant the "der Pi startet am Ende von selbst
  # neu" documented elsewhere (README/hardware.md/this script's own header
  # comment) just wasn't true - the script never called reboot itself,
  # only told the user to. Actually doing it now instead, with a short
  # window to Ctrl+C out in case something above needs a look first.
  sleep 10
  reboot
elif [ "$AUDIO_CONFIGURED" -eq 0 ]; then
  cat <<EOF

==> HiFiBerry wurde noch nicht erkannt (config.txt unverändert seit dem
    letzten Neustart?) - bitte einmal manuell neu starten und dieses Skript
    danach erneut ausführen:
      sudo reboot
      sudo owlbox-install
EOF
else
  cat <<EOF

==> Alles eingerichtet. Noch zu erledigen (kein Skript kann das für dich tun):
  1. RC522-RFID-Leser (Software-SPI), beide Taster, beide Dreh-Encoder und die
     4 Jumperkabel des Displays (Strom + I2C für Touch) verkabeln - siehe
     OwlBox-Verkabelung.pdf.
  2. http://<pi-ip>:5000/admin öffnen, Ersteinrichtung (Benutzername/Passwort)
     durchlaufen, erste Geschichte hochladen und einem Chip zuweisen.
EOF
fi
