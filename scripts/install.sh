#!/usr/bin/env bash
# Installs OwlBox onto a Raspberry Pi (tested against Raspberry Pi OS Bookworm/Legacy Lite).
# Run as root (sudo ./scripts/install.sh [stage]) from inside a checkout of this repo.
#
# Targets the project's standard hardware (see docs/hardware.md): Pi 3B+, HiFiBerry
# Amp2 (TAS5756M chip - the PCM512x family, same codec as the DAC+ Pro; NOT the
# older Amp/Amp+'s TAS5713, a different chip needing a different overlay), the
# official 7" Raspberry Pi Touch Display (DSI ribbon cable + 4 jumper wires for
# power/I2C touch - see docs/hardware.md), RC522 on the Pi's real hardware
# SPI0 bus (free since the display doesn't use SPI at all), buttons/encoders
# on the documented default pins.
#
# STAGED INSTALL - the real point of this script's structure. Four independent
# stages, each installing only the OS packages/config.txt lines that ONE piece
# of hardware needs, so it can be wired up and tested (via `sudo owlbox-stage
# <name>`, see docs/staged-setup.md) before moving on to the next:
#
#   sudo ./scripts/install.sh sound      # nur HiFiBerry Amp2
#   sudo ./scripts/install.sh display    # + 7"-Touch-Display (DSI)
#   sudo ./scripts/install.sh rfid       # + RC522-Leser
#   sudo ./scripts/install.sh controls   # + Taster/Encoder
#   sudo ./scripts/install.sh            # alle vier zusammen (Kurzform: "all")
#
# Every stage always applies the same small BASE step first (system user,
# Python venv, app code, systemd unit files, sudoers, boot-speed trims) -
# cheap and fully idempotent, so it's safe as a shared prerequisite no matter
# which stage runs first. Each stage's own OS-level work (packages, config.txt/
# cmdline.txt lines) touches ONLY that stage's own lines - never another
# stage's - so stages can be run any number of times, in any order, at any
# time, independent of whether earlier stages already ran. This script never
# starts owlbox.service/owlbox-kiosk.service itself; that's `owlbox-stage`'s
# job (config.yaml feature toggles + starting/testing/enabling), kept
# completely separate from "is the OS ready for this hardware" here.
#
# config.txt/cmdline.txt changes need a reboot to take effect (the overlay/KMS
# driver only reloads at boot) - if any stage run here changed either file,
# the script reboots itself at the end; re-run the same command afterward.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo ./scripts/install.sh [sound|display|rfid|controls]" >&2
  exit 1
fi

STAGE="${1:-all}"
case "$STAGE" in
  all|sound|display|rfid|controls) ;;
  *)
    echo "Unbekannte Stufe: $STAGE (erlaubt: sound display rfid controls, oder ohne Argument = alle)" >&2
    exit 1
    ;;
esac
DO_SOUND=0; DO_DISPLAY=0; DO_RFID=0; DO_CONTROLS=0
case "$STAGE" in
  all)      DO_SOUND=1; DO_DISPLAY=1; DO_RFID=1; DO_CONTROLS=1 ;;
  sound)    DO_SOUND=1 ;;
  display)  DO_DISPLAY=1 ;;
  rfid)     DO_RFID=1 ;;
  controls) DO_CONTROLS=1 ;;
esac

# readlink -f matters here: this script can be reached through the
# /usr/local/bin/owlbox-install symlink created further down. Without
# resolving it, dirname would yield /usr/local/bin and REPO_DIR would become
# /usr/local - which the rsync below would then happily copy into
# /opt/owlbox.
REPO_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
INSTALL_DIR="/opt/owlbox"
SERVICE_USER="owlbox"

CONFIG_TXT=""
for candidate in /boot/firmware/config.txt /boot/config.txt; do
  [ -f "$candidate" ] && { CONFIG_TXT="$candidate"; break; }
done

CMDLINE_TXT=""
for candidate in /boot/firmware/cmdline.txt /boot/cmdline.txt; do
  [ -f "$candidate" ] && { CMDLINE_TXT="$candidate"; break; }
done

NEEDS_REBOOT=0
[ -n "$CONFIG_TXT" ] && BEFORE_HASH="$(sha256sum "$CONFIG_TXT" | cut -d' ' -f1)" || BEFORE_HASH=""

# -- helpers ------------------------------------------------------------

# write_stage_block <file> <stage-tag> <line>...
# Each stage owns its own marker-delimited block (tagged by name), so
# re-running one stage never touches another stage's lines - the whole point
# of being safely re-runnable independently and in any order. If the block
# already exists, its content is replaced IN PLACE (same position in the
# file); a brand new block is appended at the end. Replacing in place matters
# for repeated, mixed-order re-runs: an earlier version always relocated the
# (re)written block to the end of the file, which - since a stage's block is
# essentially never at the true end once other stages have their own blocks
# too - left the blank line that used to separate it from its neighbours
# behind every single time, growing config.txt by one stray blank line per
# re-run of any given stage (confirmed by running all four stages, in mixed
# order, repeatedly). Python (already used the same way in scripts/stage.sh)
# rather than awk/sed here - simpler and more obviously correct for
# find-a-block-and-splice-it-back-in than the equivalent awk would be.
write_stage_block() {
  local file="$1" tag="$2"; shift 2
  python3 - "$file" "$tag" "$@" <<'PY'
import sys
path, tag = sys.argv[1], sys.argv[2]
new_lines = sys.argv[3:]
begin = f"# --- OwlBox:{tag} begin (managed by scripts/install.sh {tag} - re-running replaces this block) ---"
end = f"# --- OwlBox:{tag} end ---"
lines = open(path).read().splitlines()
try:
    start = lines.index(begin)
    stop = lines.index(end, start)
    lines[start:stop + 1] = [begin, *new_lines, end]
except ValueError:
    # No existing block for this tag yet - append at the end. Trim any
    # trailing blank lines first so repeated first-time appends (e.g. across
    # different stages on a fresh config.txt) converge to a fixed point
    # instead of growing an extra blank line before each new block.
    while lines and lines[-1] == "":
        lines.pop()
    lines += ["", begin, *new_lines, end]
open(path, "w").write("\n".join(lines) + "\n")
PY
}

# ============================================================ BASE (always)
# Everything here is hardware-independent - the shared prerequisite every
# stage needs (a working Python venv, the app code in place, the systemd unit
# files present so `owlbox-stage` can start/restart them) - so it always
# runs, regardless of which stage(s) were requested. Cheap and idempotent:
# running it again (e.g. as part of a later, different stage) changes nothing
# that's already correct.

echo "==> [Basis] Installing system packages"
apt-get update
apt-get install -y python3-venv python3-pip python3-dev build-essential || true

echo "==> [Basis] Boot-speed trims (disabling services this box never uses)"
for svc in bluetooth hciuart triggerhappy ModemManager dphys-swapfile; do
  systemctl disable --now "$svc" >/dev/null 2>&1 || true
done
if command -v raspi-config >/dev/null 2>&1; then
  # Don't block the rest of boot waiting for the network to come up - OwlBox
  # and the kiosk start independently of whether WLAN has associated yet.
  raspi-config nonint do_boot_wait 1 || true
fi
if [ -n "$CONFIG_TXT" ]; then
  # Clean up leftover config.txt lines from a previous install targeting the
  # old 3.5" SPI display (tft35a/MHS-35 overlay, its forced virtual-HDMI mode,
  # its ads7846 touch line) - harmless to run on a config.txt that never had
  # them, but leaving them in place on an upgrade would make the kernel keep
  # trying to init display hardware that's no longer physically connected.
  # General hygiene, not tied to any one stage, so it lives here in BASE.
  sed -i -E '/^dtoverlay=mhs35/d; /^dtoverlay=tft35a/d; /^dtoverlay=ads7846/d; /^hdmi_force_hotplug=/d; /^hdmi_group=/d; /^hdmi_mode=/d; /^hdmi_cvt=/d; /^hdmi_drive=/d' "$CONFIG_TXT"
  # disable_splash=1 only turns off the firmware-level rainbow-square splash
  # (VideoCore, before the kernel even starts) - unrelated to Plymouth below,
  # which takes over once the kernel/systemd are running. No conflict between
  # the two.
  write_stage_block "$CONFIG_TXT" base "disable_splash=1" "boot_delay=0"
fi
systemctl disable --now owlbox-fbcp.service >/dev/null 2>&1 || true
rm -f /etc/systemd/system/owlbox-fbcp.service /usr/local/bin/fbcp /etc/X11/xorg.conf.d/99-owlbox-fbdev.conf

echo "==> [Basis] Boot-Fortschrittsbalken (Plymouth) statt roher Boot-Textausgabe"
# Not verified on real hardware yet - see docs/staged-setup.md. Minimal custom
# theme (own script + two tiny solid-colour PNGs, no external assets) instead
# of relying on whatever theme happens to ship in plymouth-themes, so this
# doesn't depend on an optional package's exact theme selection. Matches the
# app's own default colour theme (owlbox/themes.py: bg #12141c, accent
# #f2a93c, text #f5f2ea). owlbox-kiosk.service already has
# `After=... plymouth-quit.service` (see systemd/owlbox-kiosk.service) - the
# kiosk only grabs tty1 once Plymouth has quit, so no extra ordering work
# needed here beyond actually installing and enabling Plymouth itself.
apt-get install -y plymouth || true
if command -v plymouth-set-default-theme >/dev/null 2>&1; then
  THEME_DIR=/usr/share/plymouth/themes/owlbox
  mkdir -p "$THEME_DIR"
  cat > "$THEME_DIR/owlbox.plymouth" <<'EOF'
[Plymouth Theme]
Name=OwlBox
Description=OwlBox boot splash - progress bar in the app's own colours
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/owlbox
ScriptFile=/usr/share/plymouth/themes/owlbox/owlbox.script
EOF
  cat > "$THEME_DIR/owlbox.script" <<'EOF'
# OwlBox Plymouth theme - title + a progress bar, nothing else. Colours match
# owlbox/themes.py's default theme (bg #12141c, text #f5f2ea); the bar's fill
# colour (#f2a93c, the accent colour) is baked into fill.png directly since
# Plymouth script has no fill-rectangle primitive - a solid-colour source
# image scaled to the target width is the standard way to draw a bar.

Window.SetBackgroundTopColor(0.070588, 0.078431, 0.109804);
Window.SetBackgroundBottomColor(0.070588, 0.078431, 0.109804);

screen_width = Window.GetWidth();
screen_height = Window.GetHeight();

title_image = Image.Text("OwlBox", 0.960784, 0.949020, 0.917647, 1, "Sans 28");
title_sprite = Sprite(title_image);
title_sprite.SetX(screen_width / 2 - title_image.GetWidth() / 2);
title_sprite.SetY(screen_height / 2 - 40);
title_sprite.SetZ(10);

bar_width = 320;
bar_height = 6;
bar_x = screen_width / 2 - bar_width / 2;
bar_y = screen_height / 2 + 20;

track_sprite = Sprite(Image("track.png").Scale(bar_width, bar_height));
track_sprite.SetX(bar_x);
track_sprite.SetY(bar_y);
track_sprite.SetZ(10);

fill_image = Image("fill.png");
fill_sprite = Sprite();
fill_sprite.SetX(bar_x);
fill_sprite.SetY(bar_y);
fill_sprite.SetZ(11);

fun owlbox_progress_callback(duration, progress) {
  width = Math.Int(bar_width * progress);
  if (width < 2) {
    width = 2;
  }
  fill_sprite.SetImage(fill_image.Scale(width, bar_height));
}
Plymouth.SetBootProgressFunction(owlbox_progress_callback);

fun owlbox_quit_callback() {
  title_sprite.SetOpacity(0);
  track_sprite.SetOpacity(0);
  fill_sprite.SetOpacity(0);
}
Plymouth.SetQuitFunction(owlbox_quit_callback);
EOF
  # Two 4x4 solid-colour PNGs (78 bytes each) - accent (#f2a93c) for the
  # filled part of the bar, panel (#1c2030) for the empty track behind it.
  base64 -d > "$THEME_DIR/fill.png" <<'EOF'
iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAFUlEQVR42mP8tNLmPwMSYGJAA4QFALs4At5FX0S0AAAAAElFTkSuQmCC
EOF
  base64 -d > "$THEME_DIR/track.png" <<'EOF'
iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAFUlEQVR42mOUUTD4z4AEmBjQAGEBAFzYAXNp7vV+AAAAAElFTkSuQmCC
EOF
  # -R also rebuilds the initramfs (needed so the theme is actually picked up
  # at boot on systems that boot through one) - falls back to a plain
  # set-default-theme if this Pi's plymouth build doesn't support -R.
  plymouth-set-default-theme -R owlbox 2>/dev/null || plymouth-set-default-theme owlbox || true
  if command -v update-initramfs >/dev/null 2>&1; then
    update-initramfs -u || true
  fi
  if [ -n "$CMDLINE_TXT" ] && ! grep -q 'splash' "$CMDLINE_TXT"; then
    echo "==> [Basis] Adding quiet splash to $CMDLINE_TXT"
    CMDLINE_BEFORE="$(cat "$CMDLINE_TXT")"
    printf '%s %s\n' "$CMDLINE_BEFORE" "quiet splash plymouth.ignore-serial-consoles" > "$CMDLINE_TXT"
    CMDLINE_ADDED=1
  fi
else
  echo "WARNUNG: plymouth-set-default-theme nicht gefunden - Boot-Fortschrittsbalken uebersprungen." >&2
fi

echo "==> [Basis] Creating service user '$SERVICE_USER'"
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
for grp in gpio spi audio video i2c render; do
  groupadd -f "$grp"
  usermod -aG "$grp" "$SERVICE_USER" || true
done

echo "==> [Basis] Granting passwordless sudo for shutdown/WLAN/service-restart"
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

echo "==> [Basis] Copying application to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude ".venv" --exclude "data" --exclude "__pycache__" "$REPO_DIR"/ "$INSTALL_DIR"/

# Stable update command, independent of which directory this script was
# originally invoked from: confirmed on real hardware that "cd owlbox" from
# inside an already-checked-out repo silently lands one level too deep in
# the owlbox/owlbox Python package (it shares its name with the repo root),
# after which "./scripts/install.sh" fails with "command not found" - a
# config.txt fix never got a chance to run because of exactly this, even
# though `git pull` itself had succeeded.
#
# This deliberately is NOT a symlink into $INSTALL_DIR: /opt/owlbox is only
# ever an rsync target, never a git checkout, so re-running the copy there
# could never pick up new commits - it would rsync /opt/owlbox onto itself
# and silently "succeed" while changing nothing. Instead a tiny generated
# wrapper remembers the checkout this was first installed from, pulls there,
# and hands over to that checkout's install.sh (forwarding any stage
# argument), so "sudo owlbox-install [stage]" works the same as running the
# checkout's own script directly, from any cwd.
if [ "$REPO_DIR" != "$INSTALL_DIR" ]; then
  cat > /usr/local/bin/owlbox-install <<WRAPPER
#!/usr/bin/env bash
# Generated by scripts/install.sh - do not edit, gets overwritten on install.
set -euo pipefail
CHECKOUT="$REPO_DIR"
if [ ! -x "\$CHECKOUT/scripts/install.sh" ]; then
  echo "OwlBox checkout not found at \$CHECKOUT (moved or deleted?)." >&2
  echo "Re-run the install from your checkout once to repair this command." >&2
  exit 1
fi
if [ -d "\$CHECKOUT/.git" ]; then
  echo "==> Updating \$CHECKOUT"
  # -c safe.directory: the checkout belongs to the login user, but this runs
  # as root, which git otherwise refuses with a "dubious ownership" error.
  # A failed pull (no network, local edits, no upstream) must not abort the
  # run - reinstalling the code that's already checked out is still useful,
  # and silently doing nothing would be the worse outcome.
  if ! git -C "\$CHECKOUT" -c safe.directory="\$CHECKOUT" pull --ff-only; then
    echo "!!  git pull failed - continuing with the checkout as it is." >&2
  fi
fi
exec "\$CHECKOUT/scripts/install.sh" "\$@"
WRAPPER
  chmod +x /usr/local/bin/owlbox-install
  echo "==> Updates from now on: sudo owlbox-install [stage] (pulls + reinstalls, from any directory)"
fi

echo "==> [Basis] Creating Python virtualenv"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
# One requirements.txt covers every stage's Python dependencies (gpiozero,
# mfrc522, spidev, lgpio included) - installed in full here regardless of
# which stage was requested, so e.g. `install.sh rfid` alone still has
# everything `owlbox-stage rfid`'s standalone test tool needs.
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# A genuinely first-time install (no config.yaml yet) starts with every
# hardware toggle off - RFID/buttons/encoders/backlight - regardless of which
# stage was requested first. Starting owlbox.service (which only
# `owlbox-stage` ever does, never this script) against hardware that isn't
# wired yet would try to open the RC522/buttons/encoders/backlight
# transistor before any of it exists - exactly the "guess what's wrong"
# situation the staged flow (docs/staged-setup.md) replaces. A re-run must
# NOT touch these settings again - that would silently undo a stage the user
# has already progressed past (or is deliberately testing at right now).
if [ ! -f "$INSTALL_DIR/config/config.yaml" ]; then
  cp "$INSTALL_DIR/config/config.example.yaml" "$INSTALL_DIR/config/config.yaml"
  sed -i -E 's/^(\s*reader:).*/\1 simulated   # mfrc522 | simulated/' "$INSTALL_DIR/config/config.yaml"
  sed -i -E 's/^(\s*enabled:).*/\1 false/' "$INSTALL_DIR/config/config.yaml"
  sed -i -E 's/^(\s*backlight_pin:).*/\1 null/' "$INSTALL_DIR/config/config.yaml"
  echo "==> [Basis] Wrote default config/config.yaml (alle Hardware-Stufen erstmal aus)"
fi

mkdir -p "$INSTALL_DIR/media" "$INSTALL_DIR/data"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/kiosk.sh" "$INSTALL_DIR/scripts/stage.sh" \
  "$INSTALL_DIR/scripts/test_rfid.py" "$INSTALL_DIR/scripts/test_controls.py"
# Guided staged bring-up (sound -> display -> rfid -> controls): starts/stops/
# tests each stage's hardware and owns config.yaml's feature toggles - see
# docs/staged-setup.md. Safe as a plain symlink (unlike owlbox-install
# above): this script only edits config.yaml and restarts services, it never
# derives a source directory from its own path.
ln -sf "$INSTALL_DIR/scripts/stage.sh" /usr/local/bin/owlbox-stage

cp "$INSTALL_DIR/systemd/owlbox.service" /etc/systemd/system/owlbox.service
systemctl daemon-reload

# ============================================================ SOUND
# The official 7" DSI Touch Display needs NO config.txt entry at all - it's
# auto-detected over the DSI ribbon cable by the Pi's own firmware (handled
# under DISPLAY below regardless). All that's needed here is the audio path.
if [ "$DO_SOUND" -eq 1 ]; then
  echo "==> [Sound] Installing packages (mpv, ALSA)"
  apt-get install -y mpv alsa-utils || true

  if [ -n "$CONFIG_TXT" ]; then
    echo "==> [Sound] Configuring HiFiBerry Amp2 in $CONFIG_TXT"

    # THE actual root cause of a day-long "digital path is fine but playback
    # is crackling/fragmented" saga, confirmed on real hardware: stock
    # Raspberry Pi OS Bookworm images already ship their own, active,
    # uncommented "dtoverlay=vc4-kms-v3d" (no ",noaudio") and
    # "dtparam=audio=on" lines. An earlier version of this script left those
    # two alone and just appended its own corrected lines elsewhere, on the
    # assumption that a later dtoverlay/dtparam line always wins over an
    # earlier one - that assumption does NOT reliably hold in practice for
    # either directive: `aplay -l` kept showing both the "vc4hdmi" HDMI-audio
    # card (from the stock, non-,noaudio overlay application - dtoverlay
    # lines are independent actions, not key/value overrides, so a second
    # corrected line doesn't retroactively undo what the first one already
    # registered) and the onboard "bcm2835 Headphones" card (from the stock
    # dtparam=audio=on) even with this script's own corrected lines present
    # and last in the file. Editing the two stock lines directly, in place,
    # instead of leaving them untouched and fighting them with something
    # appended elsewhere, is what actually fixed it on real hardware.
    sed -i -E 's/^dtoverlay=vc4-kms-v3d$/dtoverlay=vc4-kms-v3d,noaudio/' "$CONFIG_TXT"
    sed -i -E 's/^dtparam=audio=on$/#dtparam=audio=on/' "$CONFIG_TXT"
    # Safety net for the two lines just edited: delete any further/duplicate
    # bare copy the in-place substitutions didn't already catch (e.g. a
    # second stock occurrence) - these patterns only match what's still
    # unfixed, so they never touch the lines just corrected above.
    sed -i -E '/^dtoverlay=vc4-kms-v3d$/d; /^dtparam=audio=on$/d' "$CONFIG_TXT"
    # Fallback for a config.txt that never had a stock "dtoverlay=vc4-kms-v3d"
    # line to begin with (non-standard/minimal image, or one already
    # stripped by hand) - the in-place edit above had nothing to upgrade in
    # that case, so assert the line directly instead of silently ending up
    # without it.
    grep -q -E '^dtoverlay=vc4-kms-v3d(,.*)?$' "$CONFIG_TXT" \
      || echo "dtoverlay=vc4-kms-v3d,noaudio" >> "$CONFIG_TXT"

    # HiFiBerry Amp2's TAS5756M chip is PCM512x-family (same codec as the
    # DAC+ Pro) - confirmed on real hardware via a failed I2C probe on the
    # TAS5713-specific "hifiberry-amp" overlay (wrong chip entirely) followed
    # by an i2cdetect scan showing a live device at 0x4d, the PCM512x
    # family's address. "hifiberry-amp" is for the older Amp/Amp+'s TAS5713
    # instead - different chip, different overlay, even though the products
    # are easy to confuse by name.
    write_stage_block "$CONFIG_TXT" sound \
      "dtparam=audio=off" \
      "dtoverlay=hifiberry-dacplus"
  else
    echo "WARNUNG: config.txt nicht gefunden (weder /boot/firmware/config.txt noch /boot/config.txt)." >&2
    echo "         HiFiBerry-Overlay konnte nicht automatisch gesetzt werden - siehe docs/hardware.md." >&2
  fi
fi

# ============================================================ DISPLAY
if [ "$DO_DISPLAY" -eq 1 ]; then
  echo "==> [Display] Installing packages (Chromium, minimal X stack)"
  # fonts-noto-color-emoji: "Legacy Lite" has no emoji-capable font at all out
  # of the box, so every 🦉/😴/▶️/etc. in the kiosk UI renders as an empty box
  # ("tofu") instead - confirmed on real hardware.
  apt-get install -y unclutter fonts-noto-color-emoji || true
  # Debian's chromium package name varies by release; try both.
  apt-get install -y chromium-browser || apt-get install -y chromium || true
  # Minimal X stack for the kiosk display - deliberately no desktop
  # environment (no lightdm, no LXDE) on top of the "Legacy Lite" base image.
  # xserver-xorg-legacy provides the Xwrapper.config mechanism needed to
  # start X without a display manager; matchbox-window-manager is tiny but
  # keeps things well-behaved if a stray JS alert()/confirm() window ever
  # pops up in Chromium. No fbdev/legacy GL driver package needed here: the
  # official DSI touch display works with the modern KMS driver
  # (vc4-kms-v3d, the Bookworm default) active, so X's own default
  # "modesetting" driver finds /dev/dri/card0 and just works.
  apt-get install -y xserver-xorg xserver-xorg-legacy xinit x11-xserver-utils matchbox-window-manager || true

  # Belt-and-suspenders against the "German/English" translate bar Chromium
  # shows on first load: kiosk.sh's --disable-features=Translate command-line
  # flag alone did NOT actually suppress it on real hardware (confirmed) -
  # this managed policy is the mechanism Chromium itself documents for
  # kiosk/enterprise deployments, and covers both possible package/policy
  # directory names depending on which of the two chromium packages above
  # got installed.
  mkdir -p /etc/chromium/policies/managed /etc/chromium-browser/policies/managed
  for policy_dir in /etc/chromium/policies/managed /etc/chromium-browser/policies/managed; do
    cat > "$policy_dir/owlbox.json" <<'EOF'
{
  "TranslateEnabled": false
}
EOF
  done

  if [ -n "$CONFIG_TXT" ]; then
    echo "==> [Display] Configuring 7\" DSI Touch Display in $CONFIG_TXT"
    # dtoverlay=vc4-kms-dsi-7inch: THE actual, official overlay for this
    # display under KMS - confirmed on real hardware that without it, the
    # DSI panel node/bridge never gets instantiated at all ("[drm] Cannot
    # find any crtc or sizes" in dmesg, screen stays black) - vc4-kms-v3d
    # alone (see SOUND above) only enables the base KMS driver, it doesn't
    # know this specific panel's timings on its own. Also covers the touch
    # controller (ft5406-family) itself, no separate rpi-ft5406 overlay line
    # needed. dtparam=i2c_arm=on: the display's touch controller needs I2C.
    write_stage_block "$CONFIG_TXT" display \
      "dtparam=i2c_arm=on" \
      "dtoverlay=vc4-kms-dsi-7inch"
  else
    echo "WARNUNG: config.txt nicht gefunden - Display-Overlay konnte nicht automatisch gesetzt werden." >&2
  fi

  # The 180° *video* flip for the physically upside-down 7" Touch Display has
  # to be a kernel command-line parameter, not anything in config.txt - the
  # vc4-kms-dsi-7inch overlay has no "rotate=" param at all (confirmed
  # against /boot/firmware/overlays/README: only sizex/sizey/invx/invy/
  # swapxy/disable_touch/dsi0 exist), and xrandr/display_lcd_rotate are both
  # confirmed ineffective under KMS. No touch params (invx/invy/swapxy) added
  # on top: confirmed on real hardware that once the video itself is rotated
  # via this cmdline.txt parameter, touch input already tracks correctly on
  # its own (X11/libinput applies its own coordinate transform to match the
  # rotated output) - adding invx+invy here on top double-corrected it.
  if [ -n "$CMDLINE_TXT" ]; then
    if ! grep -q "video=DSI-1" "$CMDLINE_TXT"; then
      echo "==> [Display] Adding 180° video rotation to $CMDLINE_TXT"
      CMDLINE_BEFORE="$(cat "$CMDLINE_TXT")"
      printf '%s %s\n' "$CMDLINE_BEFORE" "video=DSI-1:800x480@60,rotate=180" > "$CMDLINE_TXT"
      CMDLINE_ADDED=1
    fi
  else
    echo "WARNUNG: cmdline.txt nicht gefunden - Bild-Rotation konnte nicht automatisch gesetzt werden." >&2
  fi

  echo "==> [Display] Setting up kiosk autostart (minimal X, no desktop environment)"
  cat > /etc/X11/Xwrapper.config <<'EOF'
allowed_users=anybody
needs_root_rights=yes
EOF
  # No custom Xorg driver config needed: with KMS active, X's default
  # "modesetting" driver finds /dev/dri/card0 on its own.
  cp "$INSTALL_DIR/systemd/owlbox-kiosk.service" /etc/systemd/system/owlbox-kiosk.service
  systemctl daemon-reload
  # Not enabled/started here - `owlbox-stage display` (and later stages) own
  # starting it, same reasoning as owlbox.service above: this script's job
  # ends at "the OS is ready", not "hardware nothing has confirmed is wired
  # yet is now running".
fi

# ============================================================ RFID
if [ "$DO_RFID" -eq 1 ]; then
  echo "==> [RFID] Enabling SPI"
  # Required: the RC522 runs on the Pi's hardware SPI0 bus (/dev/spidev0.0,
  # CE0), see owlbox/rfid/mfrc522_reader.py and docs/hardware.md. Without
  # this the kernel's spi-bcm2835 driver never loads and the device node
  # doesn't exist.
  #
  # /dev/spidev0.0 existing already (before we touch anything below) means
  # SPI0 survived a previous clean boot - `do_spi` below is then a no-op and
  # doesn't need another reboot. If it's missing, this run is the one
  # activating SPI0 for the first time.
  SPI_ALREADY_ACTIVE=0
  [ -e /dev/spidev0.0 ] && SPI_ALREADY_ACTIVE=1
  if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_spi 0 || true
  elif [ -n "$CONFIG_TXT" ]; then
    write_stage_block "$CONFIG_TXT" rfid "dtparam=spi=on"
  fi
  # `raspi-config nonint do_spi 0` uncomments the image's own stock
  # "#dtparam=spi=on" line in place, outside any managed block - confirmed on
  # real hardware this can duplicate a copy from an earlier install() that
  # went the write_stage_block route instead. Converge to a single active
  # copy regardless of which path set it.
  if [ -n "$CONFIG_TXT" ] && grep -q '^dtparam=spi=on$' "$CONFIG_TXT"; then
    OCCURRENCES="$(grep -c '^dtparam=spi=on$' "$CONFIG_TXT")"
    if [ "$OCCURRENCES" -gt 1 ]; then
      # Delete every bare copy, then re-add exactly one via the stage block
      # (so it's still tracked/removable the same way as everything else
      # this script manages).
      sed -i -E '/^dtparam=spi=on$/d' "$CONFIG_TXT"
      write_stage_block "$CONFIG_TXT" rfid "dtparam=spi=on"
    fi
  fi
  # Force the reboot path below if SPI0 just went from inactive to active,
  # even though config.txt's hash may not have changed (e.g. the line was
  # already there from an earlier install(), just never actually loaded).
  # `raspi-config nonint do_spi 0` applies the overlay live - confirmed on
  # real hardware that this live toggle alone (no crash, no config.txt
  # change) can leave the audio driver in a broken-but-silent state
  # (digitally clean writes, no error, no sound) until a clean reboot, see
  # docs/hardware.md's "Vierte Falle". Gated on SPI_ALREADY_ACTIVE so a
  # second, already-clean run doesn't reboot again on every invocation.
  [ "$SPI_ALREADY_ACTIVE" -eq 0 ] && NEEDS_REBOOT=1
fi

# ============================================================ CONTROLS
if [ "$DO_CONTROLS" -eq 1 ]; then
  # No packages or config.txt lines of its own: buttons/rotary encoders are
  # plain GPIO via gpiozero, already installed as part of BASE's venv, and
  # need no overlay/dtparam at all. This stage exists mainly so the four
  # stages form a complete, symmetric set matching docs/staged-setup.md and
  # `owlbox-stage` - `sudo owlbox-stage controls` is where the actual
  # wiring gets tested and where owlbox.service becomes permanently enabled.
  echo "==> [Taster/Encoder] Nichts zu installieren (gpiozero ist Teil der Basis) - direkt testen mit: sudo owlbox-stage controls"
fi

# -- summary -----------------------------------------------------------------

if [ -n "$CONFIG_TXT" ]; then
  AFTER_HASH="$(sha256sum "$CONFIG_TXT" | cut -d' ' -f1)"
  [ "$BEFORE_HASH" != "$AFTER_HASH" ] && NEEDS_REBOOT=1
fi
# cmdline.txt's own rotation line is a one-time addition (guarded by the
# "grep -q video=DSI-1" check above) - CMDLINE_ADDED is set right where that
# happens, since cmdline.txt has no natural "hash before/after" comparison
# point as clean as CONFIG_TXT's (it's rewritten unconditionally above, not
# edited in place).
[ "${CMDLINE_ADDED:-0}" -eq 1 ] && NEEDS_REBOOT=1

if [ "$NEEDS_REBOOT" -eq 1 ]; then
  cat <<EOF

==> Neustart noetig (config.txt/cmdline.txt geaendert, oder ein Overlay wurde
    live umgeschaltet - z.B. SPI0 fuer den RC522) - starte in 10 Sekunden neu
    (Strg+C zum Abbrechen).
    Nach dem Neustart denselben Befehl einmal erneut ausführen:
      sudo owlbox-install $STAGE
EOF
  # Confirmed on real hardware: leaving this as a printed instruction rather
  # than actually rebooting meant the "startet am Ende von selbst neu"
  # documented elsewhere just wasn't true. Actually doing it now instead,
  # with a short window to Ctrl+C out in case something above needs a look
  # first.
  sleep 10
  reboot
else
  cat <<EOF

==> OS-Vorbereitung für Stufe "$STAGE" abgeschlossen.
EOF
  case "$STAGE" in
    sound)    echo "    Jetzt testen: sudo owlbox-stage sound" ;;
    display)  echo "    Jetzt testen: sudo owlbox-stage display" ;;
    rfid)     echo "    Jetzt testen: sudo owlbox-stage rfid" ;;
    controls) echo "    Jetzt testen: sudo owlbox-stage controls" ;;
    all)      cat <<'EOF'
    Jetzt Stück für Stück in Betrieb nehmen (jede Stufe einzeln testbar,
    siehe docs/staged-setup.md):
        sudo owlbox-stage sound
        sudo owlbox-stage display
        sudo owlbox-stage rfid
        sudo owlbox-stage controls
EOF
      ;;
  esac
  cat <<EOF

    Danach noch manuell: http://<pi-ip>:5000/admin öffnen, Ersteinrichtung
    (Benutzername/Passwort) durchlaufen, erste Geschichte hochladen und
    einem Chip zuweisen.
EOF
fi
