# Hardware-Aufbau

Getestete/angenommene Zielhardware:

- Raspberry Pi 3B+
- HiFiBerry Amp (I2S-Verstärker-HAT)
- RC522 RFID-Modul (SPI, 13.56 MHz)
- 5" Touch-Display (HDMI+USB-Touch oder DSI)
- 2 Taster (vor/zurück)
- 1 Dreh-Encoder mit Druckschalter (Lautstärke / Pause)

Alle Pin-Angaben sind BCM-Nummerierung und entsprechen den Defaults in
`config/config.example.yaml`. Wer andere Pins verdrahtet, passt einfach die
`gpio:`/`rfid:` Sektion in `config/config.yaml` an.

## HiFiBerry Amp

Der HiFiBerry belegt die I2S-Pins (BCM 18/19/20/21) sowie ggf. I2C
(BCM 2/3) zur Verstärkersteuerung. Diese Pins bleiben frei für RFID/Taster.

In `/boot/firmware/config.txt` (bzw. `/boot/config.txt` auf älteren Images):

```
dtparam=audio=off
dtoverlay=hifiberry-amp
```

(Für andere HiFiBerry-Varianten den passenden Overlay-Namen verwenden, z.B.
`hifiberry-dacplus` für ein reines DAC+. Nach der Änderung neu starten.)

Danach mit `aplay -L` und `amixer -c 0 scontrols` das ALSA-Device bzw. den
Mixer-Namen prüfen und in `config.yaml` unter `audio.alsa_device` /
`audio.mixer_control` eintragen (Amp/Amp2 nutzen meist `Digital`, manche
Boards `PCM` oder `Master`).

## RC522 RFID-Leser (SPI)

| RC522 Pin | Raspberry Pi         |
|-----------|----------------------|
| VCC       | 3.3V (**nicht 5V!**) |
| GND       | GND                  |
| RST       | GPIO25 (frei wählbar, siehe `rfid.reset_pin`) |
| SDA (CS)  | GPIO8 / CE0          |
| SCK       | GPIO11               |
| MOSI      | GPIO10               |
| MISO      | GPIO9                |
| IRQ       | nicht verbunden      |

SPI muss aktiviert sein (macht `scripts/install.sh` bereits via
`raspi-config nonint do_spi 0`, alternativ `sudo raspi-config` →
Interface Options → SPI).

## Taster (vor/zurück)

Jeweils ein Taster zwischen GPIO und GND, kein externer Widerstand nötig
(interner Pull-up wird von gpiozero aktiviert):

| Funktion | BCM Pin |
|----------|---------|
| Zurück   | 6       |
| Weiter   | 5       |

## Dreh-Encoder mit Taster (z.B. KY-040)

| Encoder Pin | Raspberry Pi |
|-------------|--------------|
| CLK         | GPIO17       |
| DT          | GPIO27       |
| SW          | GPIO22       |
| +           | 3.3V         |
| GND         | GND          |

Drehen ändert die Lautstärke (Schritweite `audio.volume_step`), Drücken
schaltet Play/Pause um. Ein langer Druck (`gpio.shutdown_hold_seconds`,
Default 4s) fährt den Pi sicher herunter - praktisch für ein Kindergerät
ohne Zugriff auf ein Terminal. Auf 0 setzen, um das abzuschalten.

Damit der Shutdown ohne Passwortabfrage funktioniert, braucht der
Service-User `owlbox` passwortloses sudo dafür, z.B. in
`/etc/sudoers.d/owlbox`:

```
owlbox ALL=(ALL) NOPASSWD: /sbin/shutdown
```

## 5" Touch-Display

Die meisten günstigen 5"-Displays hängen per HDMI + separatem USB-Touch am
Pi und funktionieren ohne weitere Treiber. DSI-Displays brauchen ggf. ein
herstellerspezifisches Overlay/Treiberpaket - der Anleitung des jeweiligen
Displays folgen. Für den Kiosk-Modus sollte der Pi so konfiguriert sein,
dass er direkt in den Desktop (Auto-Login) bootet.

## Kiosk-Autostart (Chromium fullscreen)

`scripts/kiosk.sh` startet Chromium im Kiosk-Modus gegen
`http://localhost:5000/`. Wie er beim Boot gestartet wird, hängt von der
Desktop-Umgebung ab:

**Variante A - systemd user unit (empfohlen, funktioniert unter X11 und
Wayland/labwc auf aktuellem Raspberry Pi OS):**

```
mkdir -p ~/.config/systemd/user
cp /opt/owlbox/systemd/owlbox-kiosk.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now owlbox-kiosk.service
sudo loginctl enable-linger $USER   # optional: startet auch ohne aktive Anmeldung
```

**Variante B - Autostart-Datei der Desktop-Umgebung** (falls A nicht greift):

- LXDE/X11: Zeile in `~/.config/lxsession/LXDE-pi/autostart` ergänzen:
  `@/opt/owlbox/scripts/kiosk.sh`
- labwc (Wayland, Bookworm-Default): Zeile in `~/.config/labwc/autostart`
  ergänzen: `/opt/owlbox/scripts/kiosk.sh &`
