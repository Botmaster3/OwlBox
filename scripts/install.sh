#!/usr/bin/env bash
# Installs OwlBox onto a Raspberry Pi (tested against Raspberry Pi OS Bookworm).
# Run as root (sudo ./scripts/install.sh) from inside a checkout of this repo.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root: sudo ./scripts/install.sh" >&2
  exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/owlbox"
SERVICE_USER="owlbox"

echo "==> Installing system packages"
apt-get update
apt-get install -y \
  python3-venv python3-pip python3-dev build-essential \
  mpv alsa-utils \
  git curl \
  unclutter \
  || true
# Debian's chromium package name varies by release; try both.
apt-get install -y chromium-browser || apt-get install -y chromium || true

echo "==> Enabling SPI (needed for the RC522 RFID reader)"
if command -v raspi-config >/dev/null 2>&1; then
  raspi-config nonint do_spi 0 || true
else
  echo "raspi-config not found, enable SPI manually: add 'dtparam=spi=on' to /boot/firmware/config.txt"
fi

echo "==> Creating service user '$SERVICE_USER'"
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
for grp in gpio spi audio video i2c; do
  groupadd -f "$grp"
  usermod -aG "$grp" "$SERVICE_USER" || true
done

echo "==> Copying application to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --exclude ".venv" --exclude "data" --exclude "__pycache__" "$REPO_DIR"/ "$INSTALL_DIR"/

echo "==> Creating Python virtualenv"
python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

if [ ! -f "$INSTALL_DIR/config/config.yaml" ]; then
  cp "$INSTALL_DIR/config/config.example.yaml" "$INSTALL_DIR/config/config.yaml"
  echo "==> Wrote default config/config.yaml - review it (audio device, GPIO pins, admin password)"
fi

mkdir -p "$INSTALL_DIR/media" "$INSTALL_DIR/data"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/kiosk.sh"

echo "==> Installing systemd service"
cp "$INSTALL_DIR/systemd/owlbox.service" /etc/systemd/system/owlbox.service
systemctl daemon-reload
systemctl enable --now owlbox.service

cat <<EOF

==> Core service installed and started (systemctl status owlbox).

Still to do manually:
  1. Add the HiFiBerry device tree overlay to /boot/firmware/config.txt, e.g. for a
     HiFiBerry Amp/Amp2: dtoverlay=hifiberry-amp   (see docs/hardware.md), then reboot.
  2. Run 'aplay -L' and 'amixer -c 0 scontrols' to confirm the ALSA device/mixer name
     in $INSTALL_DIR/config/config.yaml (audio.alsa_device / audio.mixer_control) match your board.
  3. Wire the RC522 reader and the buttons/encoder per docs/hardware.md.
  4. Set up the kiosk display autostart (see docs/hardware.md) so the 5" touchscreen
     shows http://localhost:5000/ full-screen on boot - this depends on your desktop
     session/user and isn't done by this script.
  5. Open http://<pi-ip>:5000/admin to upload stories and assign RFID chips.
EOF
