# Hardware-Aufbau

Zielhardware:

- Raspberry Pi 3B+
- HiFiBerry Amp (I2S-Verstärker-HAT)
- RC522 RFID-Modul (SPI, 13.56 MHz)
- 3.5" SPI-TFT-Display, **Touch vorhanden, aber bewusst deaktiviert** (siehe unten)
- 2 Taster (vor/zurück)
- 1 Dreh-Encoder mit Druckschalter (Lautstärke / Pause)

Alle Pin-Angaben sind BCM-Nummerierung und entsprechen den Defaults in
`config/config.example.yaml`. Wer andere Pins verdrahtet, passt einfach die
`gpio:`/`rfid:` Sektion in `config/config.yaml` an.

## Wichtig: GPIO-Konflikte bei dieser Kombination

Ein 3.5" SPI-Display + HiFiBerry + RC522 + Taster + Encoder auf einem
einzigen 40-Pin-Header ist eng - hier kollidieren üblicherweise:

- **CE0 (GPIO8)**: Bei praktisch jedem SPI-TFT ist der Display-Controller
  auf SPI0 CE0. Der RC522 wird deshalb in dieser Anleitung auf **CE1
  (GPIO7)** gelegt statt auf CE0 - beide Geräte teilen sich dann den
  gleichen SPI0-Bus (SCLK/MOSI/MISO), aber mit getrennter Chip-Select-Leitung,
  das funktioniert problemlos.
- **GPIO18**: Viele günstige SPI-TFT-Boards (z.B. auf Basis von
  ILI9486/XPT2046, oft als "3.5 inch RPi LCD", "MHS3528", "Kedei" o.ä.
  verkauft) nutzen GPIO18 standardmäßig für die **Hintergrundbeleuchtung
  (LED/Backlight)**. GPIO18 ist gleichzeitig der I2S-Bit-Clock des
  HiFiBerry - **das ist ein echter Konflikt**. Lösungen (eine davon nötig):
  1. Auf dem Display-Board prüfen, ob ein Jumper/Lötpad existiert, um die
     Hintergrundbeleuchtung dauerhaft auf 3.3V zu legen statt sie per GPIO
     zu schalten (bei den meisten Klonen vorhanden, oft mit "BL" beschriftet).
  2. Falls der Overlay einen Parameter für den Backlight-Pin anbietet
     (z.B. `led_pin=`), einen freien GPIO verwenden statt GPIO18.
  3. Falls beides nicht geht: Display an einen anderen freien GPIO für die
     Beleuchtung verkabeln (Platine erlaubt das oft per Lötbrücke).
- **GPIO24/25**: Werden bei vielen dieser Displays für DC (Data/Command)
  und RST (Reset) des TFT-Controllers verwendet - unabhängig von RFID/Tastern,
  aber unbedingt mit der Doku des eigenen Displays abgleichen, bevor Taster
  oder RC522-Reset auf dieselben Pins gelegt werden.

**Vor dem Verkabeln also unbedingt die Pin-Belegung des konkret gekauften
Display-Boards nachschlagen** (Aufdruck auf der Platine, Amazon-Beschreibung
oder beiliegende Anleitung nennen meist Chipsatz + Pinbelegung) und mit der
Tabelle unten abgleichen. Sag mir gerne den genauen Produktnamen/Chipsatz
(z.B. von der Platine abfotografiert oder aus der Artikelbeschreibung
kopiert), dann kann ich die Overlay-Zeile und Pin-Tabelle exakt anpassen.

| Funktion                        | BCM Pin | Genutzt von         |
|----------------------------------|---------|---------------------|
| I2S BCLK                        | 18      | HiFiBerry (**Konflikt mit Display-Backlight möglich, siehe oben**) |
| I2S LRCLK                       | 19      | HiFiBerry           |
| I2S DIN                         | 20      | HiFiBerry           |
| I2S DOUT                        | 21      | HiFiBerry           |
| I2C SDA                         | 2       | HiFiBerry (Amp-Steuerung) |
| I2C SCL                         | 3       | HiFiBerry (Amp-Steuerung) |
| SPI0 SCLK/MOSI/MISO             | 11/10/9 | Display + RC522 (gemeinsamer Bus) |
| SPI0 CE0                        | 8       | Display (TFT-Chipselect) |
| SPI0 CE1                        | 7       | RC522 (`rfid.spi_device: 1`) |
| RC522 RST                       | 26      | RC522 (`rfid.reset_pin`, **gegen Display-Pinout prüfen**) |
| Taster Weiter                   | 5       | Taster              |
| Taster Zurück                   | 6       | Taster              |
| Encoder CLK                     | 17      | Encoder             |
| Encoder DT                      | 27      | Encoder             |
| Encoder SW                      | 22      | Encoder             |

## HiFiBerry Amp

Der HiFiBerry belegt die I2S-Pins (BCM 18/19/20/21) sowie ggf. I2C
(BCM 2/3) zur Verstärkersteuerung.

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

## RC522 RFID-Leser (SPI, CE1)

| RC522 Pin | Raspberry Pi         |
|-----------|----------------------|
| VCC       | 3.3V (**nicht 5V!**) |
| GND       | GND                  |
| RST       | GPIO26 (frei wählbar, siehe `rfid.reset_pin`, gegen Display-Pinout prüfen) |
| SDA (CS)  | GPIO7 / CE1          |
| SCK       | GPIO11 (mit Display geteilt) |
| MOSI      | GPIO10 (mit Display geteilt) |
| MISO      | GPIO9 (mit Display geteilt)  |
| IRQ       | nicht verbunden      |

Der RC522 liegt hier bewusst auf **CE1 (GPIO7)** statt CE0, weil das
Display normalerweise CE0 belegt (siehe Konflikt-Tabelle oben). In
`config.yaml`: `rfid.spi_device: 1`.

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

## 3.5" SPI-Display (Touch bewusst deaktiviert)

Anders als ein HDMI-Display hängt ein SPI-TFT nicht "einfach so" am Pi -
es braucht einen passenden Kernel-Treiber/Overlay, der je nach Board zu
einer von zwei Treiber-Familien gehört:

1. **Moderne DRM/KMS-Overlays** (z.B. `panel-mipi-dbi`/`mi0283qt`-Familie
   auf neueren Raspberry Pi OS-Images): das Display erscheint als ganz
   normaler Grafikausgang - funktioniert direkt unter X11 **und**
   Wayland/labwc, `scripts/kiosk.sh` läuft ohne weitere Anpassung.
2. **Ältere fbtft/Staging-Treiber**: erzeugen nur ein Framebuffer-Device
   (z.B. `/dev/fb1`), aber keinen echten KMS-Grafikausgang. Dafür gibt es
   zwei Wege:
   - X11 mit dem `fbdev`-Treiber direkt auf `/dev/fb1` zeigen lassen
     (funktioniert **nicht** unter Wayland/labwc, X11 zwingend nötig):
     ```
     # /usr/share/X11/xorg.conf.d/99-owlbox-display.conf
     Section "Device"
         Identifier "TFT"
         Driver "fbdev"
         Option "fbdev" "/dev/fb1"
     EndSection
     ```
   - oder `fbcp`/`fbcp-ili9341` installieren, das den HDMI-/Dummy-
     Framebuffer laufend nach `/dev/fb1` spiegelt (funktioniert mit jeder
     Desktop-Umgebung, kostet etwas CPU).

Welcher Overlay-Name (`dtoverlay=...` in `/boot/firmware/config.txt`) und
welche der beiden Treiber-Familien für das konkrete Board gilt, hängt vom
verbauten Chipsatz ab (steht meist in der Artikelbeschreibung oder auf der
Platine, z.B. "ILI9486", "ST7796"). Bitte den genauen Produktnamen/Chipsatz
nennen, dann trage ich hier die exakte Overlay-Zeile ein.

### Touch deaktivieren

Auch wenn das Board einen Touch-Controller mitbringt, soll er hier nicht
aktiv sein (die Weboberfläche zeigt bewusst keine Touch-Buttons an, siehe
`owlbox/web/templates/player.html`). Zwei Ebenen, um das sauber
sicherzustellen:

1. **Im Overlay/Device-Tree**: falls die Anleitung des Boards eine
   Overlay-Variante *ohne* Touch anbietet (manche Hersteller liefern z.B.
   `...-overlay` und `...-overlay-notouch` getrennt), diese verwenden bzw.
   den Touch-Parameter im Overlay-Aufruf weglassen/auf `false` setzen.
2. **In X11, unabhängig vom Treiber** (funktioniert auch, falls der
   Touch-Chip trotzdem als Eingabegerät auftaucht):
   ```
   # /etc/X11/xorg.conf.d/99-owlbox-notouch.conf
   Section "InputClass"
       Identifier "ignore touchscreen"
       MatchIsTouchscreen "on"
       Option "Ignore" "on"
   EndSection
   ```

## Kiosk-Autostart (Chromium fullscreen)

`scripts/kiosk.sh` startet Chromium im Kiosk-Modus gegen
`http://localhost:5000/`. Wie er beim Boot gestartet wird, hängt von der
Desktop-Umgebung ab:

**Variante A - systemd user unit** (funktioniert unter X11 immer; unter
Wayland/labwc nur, wenn das Display über einen DRM/KMS-fähigen Overlay
läuft, siehe oben):

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
- labwc (Wayland, Bookworm-Default, nur bei DRM/KMS-fähigem Display-Overlay):
  Zeile in `~/.config/labwc/autostart` ergänzen: `/opt/owlbox/scripts/kiosk.sh &`

Bei einem reinen fbtft/`/dev/fb1`-Treiber ohne KMS empfiehlt sich statt
Wayland ein minimales X11 (z.B. `startx` mit nur `openbox` als
Fenstermanager) mit der `fbdev`-Konfiguration von oben.
