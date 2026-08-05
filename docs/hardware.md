# Hardware-Aufbau

**Für genau die unten stehende Standardhardware macht `scripts/install.sh`
inzwischen alle Software-Schritte auf dieser Seite automatisch** (HiFiBerry-
und Display-Overlay in `config.txt`, GL-Treiber, `fbcp` bauen, Display-Treiber
installieren, ALSA-Gerät/Mixer erkennen, Kiosk-Autostart ohne Desktop-Umgebung,
ein paar Boot-Zeit-Trimms) - einfach zweimal mit einem Neustart dazwischen
laufen lassen, siehe README. Diese Seite bleibt trotzdem die vollständige
Referenz: für abweichende Hardware, zum Nachvollziehen, was das Skript
eigentlich tut, oder falls ein automatischer Schritt einmal fehlschlägt und
von Hand nachgeholt werden muss.

Zielhardware:

- Raspberry Pi 3B+
- HiFiBerry Amp (I2S-Verstärker-HAT)
- RC522 RFID-Modul (SPI, 13.56 MHz)
- 3.5" SPI-Touchscreen, 480×320, mit Stylus, 26-Pin-Header -
  **sehr wahrscheinlich ein "MHS-35"/"tft35a"-Klon** (ILI9486 + XPT2046,
  wird unter vielen Markennamen identisch verkauft). **Touch bleibt
  deaktiviert**, siehe unten.
- 2 Taster (vor/zurück)
- 1 Dreh-Encoder mit Druckschalter (Lautstärke / Pause)
- 1 weiterer Dreh-Encoder ohne Taster (Helligkeit, s.u.)
- 1 NPN-Transistor (z.B. BC547) oder Logic-Level-N-MOSFET, für dimmbares
  Backlight (s.u.)

Alle Pin-Angaben sind BCM-Nummerierung und entsprechen den Defaults in
`config/config.example.yaml`. Wer andere Pins verdrahtet, passt einfach die
`gpio:`/`rfid:` Sektion in `config/config.yaml` an.

**Verkabelungsplan als Grafik**: `docs/owlbox-wiring-diagram.svg` zeigt den
kompletten, fertig verkabelten Gesamtaufbau auf einen Blick - Pi + HiFiBerry
direkt gestapelt (inkl. Lautsprecher L/R an dessen Federklemmen), per Kabel
verbunden mit der Adapter-Platine, die wiederum RC522, Taster, beide Encoder,
Display und Backlight-Dimmen verkabelt.

**GPIO-Pinbelegung als Grafik**: `docs/owlbox-gpio-pinout.svg` zeigt den
kompletten 40-Pin-Header (physische Nummerierung wie auf der Pi-Platine) mit
Zielgerät pro Pin - gedacht als Bauvorlage für eine per Kabel angeschlossene
Adapter-Platine (Pi + HiFiBerry bleiben gestapelt, alle übrigen Komponenten
hängen an der Adapter-Platine).

**Layout-Vorschlag für die Adapter-Platine**: `docs/owlbox-adapter-layout.svg`
zeigt, wie die Steckverbinder auf der Platine selbst angeordnet werden können -
IDC-Buchsenleiste an einer Kante (Richtung Pi/HiFiBerry), die übrigen sechs
Anschlüsse jeweils zur Seite ihres Zielbauteils im Gehäuse ausgerichtet, plus
eine gemeinsame GND-/3.3V-Schiene statt einzelner Rückführungen zum Kabel.

**Verteiler-Platine**: `docs/hat-wiring.html` (im Browser öffnen) zeigt den
kompletten Schaltplan inkl. 40-Pin-Belegung und Steckverbinder-Pinouts pro
Modul - Kabel-Konzept wie oben, kein Stapelaufbau der Adapter-Platine selbst.
Die Pin-Zuordnung dort ist identisch mit den Tabellen unten.

## Woran die Identifikation hängt

480×320px, Stylus im Lieferumfang, 26-Pin-Anschluss und der (leicht
falsch übersetzte) Hinweis "sonst wird die Touch-Funktion ausgebrannt"
sind das exakte Wortmuster, das auf praktisch jedem Amazon-Listing für
diese Referenzplatine steht - verkauft unter vielen Namen (Kuman, OSOYOO,
Elegoo, SunFounder, "MPI3508", generische "3.5 Zoll Display"-Listings),
aber elektrisch identisch: **ILI9486-Controller fürs Display, XPT2046
für Touch**, Treiber über das `goodtft/LCD-show`-Installationsskript
(`MHS35-show` bzw. `tft35a`-Overlay). Falls der beiliegende Download-Link
der Anleitung einen anderen Treibernamen nennt, bitte kurz Bescheid geben -
dann passe ich das unten an.

## Wichtiger Hinweis: physische Steckplatz-Kollision mit dem HiFiBerry

Das Display wird laut Beschreibung direkt auf den 26/40-Pin-GPIO-Header
gesteckt ("mit einem 26-poligen SPI-Anschluss ... bitte über den ersten
Anschluss anschließen"). Der HiFiBerry Amp braucht aber **ebenfalls**
einen direkten Sitz auf demselben Header (I2S ist empfindlich gegenüber
langen/zusätzlichen Steckverbindern). **Beide gleichzeitig aufstecken
geht nicht**, sofern keins der beiden Boards einen sauberen Pass-Through-
Header mitbringt (bei diesem günstigen Display-Typ i.d.R. nicht der Fall).

**Lösung: Das Display nicht aufstecken, sondern per Jumper-/Dupont-Kabeln
verdrahten.** Der 26-Pin-Header auf der Display-Platine ist ein normaler
2.54mm-Pfostenverbinder - er lässt sich genauso gut mit einzelnen
Kabeln verbinden wie durch direktes Aufstecken. Das hat zwei Vorteile:

1. Der HiFiBerry sitzt normal direkt auf dem Pi, das Display hängt per
   Kabel daneben.
2. **Es müssen nur die tatsächlich gebrauchten Leitungen verbunden
   werden** - die Touch-Leitungen (CE1/PENIRQ) werden dabei einfach
   **gar nicht erst angeschlossen**, Touch bleibt also elektrisch inaktiv.
   **Wichtig, falls RC522 und Display beide verbaut sind**: Der
   Display-Treiber (`mhs35`/`tft35a`-Overlay) meldet dem Kernel trotzdem
   einen Touch-Controller auf SPI0 CE1 an - fest im Overlay einprogrammiert,
   ohne Parameter zum Abschalten, unabhängig davon, ob Touch physisch
   angeschlossen ist. Beide SPI0-Chipselects (CE0 fürs Display, CE1 für
   diesen Touch-Eintrag) sind damit softwareseitig belegt. Der RC522 kann
   deshalb **nicht** auf SPI0 mitlaufen - siehe „RC522 RFID-Leser" unten für
   die tatsächliche Verkabelung über Software-SPI auf freien GPIOs.

Nur diese Leitungen vom Display-Header zum Pi verbinden:

| Display-Pin (26-Pin-Header) | Pi-Pin (BCM) | Zweck |
|---|---|---|
| VCC        | 3.3V        | Versorgung |
| GND        | GND         | Masse |
| SCK        | GPIO11      | SPI0-Takt (nur Display - der RC522 hängt an eigenen GPIOs, s.u.) |
| MOSI (SDI) | GPIO10      | SPI0 (nur Display) |
| MISO (SDO) | GPIO9       | SPI0 (nur Display) |
| CS/CE0     | GPIO8       | Display-Chipselect |
| DC/RS      | GPIO24      | Data/Command (Standardwert des tft35a-Overlays) |
| RST        | GPIO25      | Reset (Standardwert des tft35a-Overlays) |
| LED/Backlight | **GPIO13, über Treibertransistor** (dimmbar, Standard) | siehe unten |
| T_CLK, T_CS, T_DIN, T_DO, T_IRQ (Touch) | **nicht anschließen** | Touch bleibt so auch elektrisch inaktiv |

**Zur Hintergrundbeleuchtung**: Je nach Fertigungscharge ist die LED-Leitung
bei diesem Board-Typ ab Werk entweder fest verdrahtet oder auf einen GPIO
gelegt (öfter berichtet: GPIO18 - genau der Pin, den der HiFiBerry für die
I2S-Bit-Clock braucht, hier also nicht verwendbar). Bei OwlBox ist das
Backlight-Dimmen **Pflicht, kein optionales Extra** - der Helligkeitsregler
unter Einstellungen (und der zweite Dreh-Encoder) sind zentrale
Bedienelemente, keine Kür:

1. Die LED-Leitung nicht an 3.3V, sondern an einen freien GPIO anschließen -
   **GPIO13** (physischer Pin 33, einer der Hardware-PWM-fähigen Pins neben
   12/18/19, von denen 18/19 dem HiFiBerry gehören).
2. Da ein Pi-GPIO nicht genug Strom für die Hintergrundbeleuchtung liefern
   kann, einen kleinen NPN-Transistor (z.B. BC547) oder Logic-Level-N-MOSFET
   als Schalter dazwischenschalten: GPIO13 → Basis/Gate (über ~1kΩ
   Vorwiderstand bei einem BJT), Kollektor/Drain → LED-Kathode, Emitter/
   Source → GND. Die LED-Anode bleibt wie gehabt an 3.3V bzw. an der vom
   Board vorgesehenen Versorgung.
3. In `config.yaml`: `gpio.backlight_pin: 13` setzen (Default in
   `config.example.yaml`). Nur auf `null` setzen, wenn das Backlight
   abweichend vom Standardaufbau doch fest an 3.3V hängt - dann hat der
   Regler in den Einstellungen keine Wirkung.
4. Den zweiten KY-040-Dreh-Encoder (ohne Taster) für die Helligkeit
   verdrahten, siehe Tabelle unten - Drehen ändert die Helligkeit sofort um
   `gpio.brightness_step` (Standard 5%) pro Rastung. Es gibt bewusst **kein**
   automatisches Dimmen (weder nach Inaktivität noch beim Einschlaf-Timer) -
   die Helligkeit bleibt, wie sie zuletzt eingestellt wurde.

Beide Erweiterungen (Backlight-Dimmen, Helligkeits-Encoder) sind in
`docs/hat-wiring.html` eingezeichnet - dieselben Inhalte liegen als
PDF-Referenz auch unter `owlbox/web/static/docs/OwlBox-Verkabelung.pdf`
(Download über die Info-Seite in der Verwaltung).

## GPIO-Belegung im Überblick

| Funktion                        | BCM Pin | Genutzt von         |
|----------------------------------|---------|---------------------|
| I2S BCLK                        | 18      | HiFiBerry (Display-Backlight bewusst NICHT hierauf gelegt, s.o.) |
| I2S LRCLK                       | 19      | HiFiBerry           |
| I2S DIN                         | 20      | HiFiBerry           |
| I2S DOUT                        | 21      | HiFiBerry           |
| I2C SDA                         | 2       | HiFiBerry (Amp-Steuerung) |
| I2C SCL                         | 3       | HiFiBerry (Amp-Steuerung) |
| SPI0 SCLK/MOSI/MISO             | 11/10/9 | Display (der RC522 hängt NICHT hier, s.u.) |
| SPI0 CE0                        | 8       | Display (TFT-Chipselect) |
| SPI0 CE1                        | 7       | vom Display-Overlay softwareseitig für Touch reserviert - **unbenutzbar**, auch unverdrahtet |
| Display DC                      | 24      | Display |
| Display RST                     | 25      | Display |
| RC522 SCK (Software-SPI)        | 4       | RC522 (`rfid.sck_pin`) |
| RC522 MOSI (Software-SPI)       | 16      | RC522 (`rfid.mosi_pin`) |
| RC522 MISO (Software-SPI)       | 15      | RC522 (`rfid.miso_pin`) |
| RC522 SDA/CS (Software-SPI)     | 14      | RC522 (`rfid.cs_pin`) |
| RC522 RST                       | 26      | RC522 (`rfid.reset_pin`) |
| Taster Weiter                   | 5       | Taster              |
| Taster Zurück                   | 6       | Taster              |
| Encoder CLK                     | 17      | Lautstärke-Encoder  |
| Encoder DT                      | 27      | Lautstärke-Encoder  |
| Encoder SW                      | 22      | Lautstärke-Encoder  |
| Display-Backlight (dimmbar)     | 13      | Backlight-Dimmen (Treibertransistor, s.o.) |
| Helligkeits-Encoder CLK         | 23      | Helligkeits-Encoder |
| Helligkeits-Encoder DT          | 12      | Helligkeits-Encoder |

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

### Lautsprecher anschließen

Der HiFiBerry Amp2 hat dafür **keine Stecker** (kein Cinch/Klinke), sondern
zwei 2-polige Federklemmen direkt auf der Platine (eine pro Kanal, jeweils
+/-). Angeschlossen wird ganz normales 2-adriges Lautsprecherkabel:

- Querschnitt **≥ 0,75 mm² (AWG 18)** reicht für 15 W / 4 Ω locker; bei
  längeren Kabelwegen (> 3-5 m) eher 1,0-1,5 mm² nehmen.
- Enden abisolieren (~10 mm); bei feindrähtiger Litze verzinnen oder
  Aderendhülsen verwenden, damit die Federklemme sauber greift.
- **Polarität an beiden Lautsprechern konsistent anschließen** (+ zu + und
  Minus zu Minus) - sonst laufen sie gegenphasig und Bass/Stereo-Ortung leiden.
- Am Lautsprecher selbst hängt der Anschluss vom jeweiligen Modell ab
  (blanker Draht, Flachsteckhülsen/Bananas oder Lötfahnen).

## RC522 RFID-Leser (Software-SPI auf freien GPIOs)

**Wichtig, unterscheidet sich von den meisten RC522-Anleitungen im Netz:**
Auf dieser Standardhardware hängt der RC522 **nicht** an einem der beiden
Hardware-SPI-Busse des Pi, sondern an vier per Software angesteuerten
GPIOs. Grund: beide Hardware-SPI-Busse sind hier bereits vergeben -
SPI0 komplett vom Display-Treiber (CE0 fürs Display, CE1 fest für einen
Touch-Controller reserviert, siehe oben), SPI1 liegt auf GPIO18-21, exakt
den Pins, die der HiFiBerry für I2S-Ton braucht. Für den RC522 bleibt daher
nur echtes Software-SPI (Bit-Banging) auf ansonsten freien GPIOs - der
RC522 hat keine Mindesttaktrate, das funktioniert zuverlässig, nur eben
etwas langsamer als Hardware-SPI (für einen Chip-Scan völlig ausreichend).

| RC522 Pin | Raspberry Pi | Config-Feld |
|-----------|--------------|-------------|
| VCC       | 3.3V (**nicht 5V!**) | - |
| GND       | GND          | - |
| RST       | GPIO26       | `rfid.reset_pin` |
| SDA (CS)  | GPIO14       | `rfid.cs_pin` |
| SCK       | GPIO4        | `rfid.sck_pin` |
| MOSI      | GPIO16       | `rfid.mosi_pin` |
| MISO      | GPIO15       | `rfid.miso_pin` |
| IRQ       | nicht verbunden | - |

Alle vier GPIOs (4/14/15/16) sind sonst von nichts in diesem Projekt belegt.
Die eigentliche Bit-Bang-Logik steckt in `owlbox/rfid/soft_spi.py`, die
`mfrc522`-Python-Bibliothek (Registerprotokoll) läuft unverändert darüber -
siehe `owlbox/rfid/mfrc522_reader.py` für Details. SPI selbst muss trotzdem
aktiviert bleiben, weil das Display es braucht (macht `scripts/install.sh`
bereits via `raspi-config nonint do_spi 0`).

Wer den RC522 ohne dieses Display betreibt (dann ist SPI0 komplett frei),
kann natürlich stattdessen ganz normal Hardware-SPI nutzen - dafür
`owlbox/rfid/mfrc522_reader.py` entsprechend anpassen (dort direkt
`spidev`/`MFRC522(bus=0, device=...)` verwenden statt `SoftSpi`).

## Taster (vor/zurück)

Als Taster kommen Cherry-MX-Switches (3-Pin-Variante) zum Einsatz. Elektrisch
sind das ganz normale Momentary-Schalter (schließt nur beim Drücken, öffnet
sonst) - dieselbe Verdrahtung wie jeder andere Taster:

- Von den 3 Pins sind nur die **beiden Metall-Pins** die elektrischen
  Kontakte (die sich diagonal gegenüberliegen); der dritte, meist aus
  Kunststoff, ist nur ein mechanischer Halteclip fürs Gehäuse/die Platine
  und hat keine elektrische Funktion - er muss nirgends angeschlossen werden.
- Jeweils einer der beiden Metall-Pins an GPIO, der andere an GND. Kein
  externer Widerstand nötig, der interne Pull-up wird von gpiozero aktiviert.
- Da Cherry-MX-Switches (anders als billige Blechtaster) sehr sauber
  prellen, reicht die Default-Entprellzeit (`gpio.bounce_time`, 50ms)
  komfortabel aus.

| Funktion | BCM Pin |
|----------|---------|
| Zurück   | 6       |
| Weiter   | 5       |

Kurz drücken springt zum vorherigen/nächsten Track. Gedrückt halten (länger
als `gpio.seek_hold_seconds`, Default 0.4s) spult stattdessen im aktuellen
Track vor/zurück, in Schritten von `gpio.seek_step_seconds` (Default 10s) -
kein Trackwechsel, solange gehalten wird.

## Dreh-Encoder mit Taster (KY-040)

| Encoder Pin | Raspberry Pi |
|-------------|--------------|
| CLK         | GPIO17       |
| DT          | GPIO27       |
| SW          | GPIO22       |
| +           | 3.3V         |
| GND         | GND          |

Das KY-040-Modul bringt eigene Pull-up-Widerstände für CLK/DT mit; die
zusätzlich von gpiozero aktivierten Pull-ups des Pi stören dabei nicht
(einfach parallel). Für den Taster (SW) hat das Modul in der Regel
**keinen** eigenen Pull-up - das übernimmt `gpiozero.Button(pull_up=True)`
in `owlbox/controls/gpio_controls.py`, hier also nichts weiter nötig.

Drehen ändert die Lautstärke (Schritweite `audio.volume_step`), Drücken
schaltet Play/Pause um. Ein langer Druck (`gpio.shutdown_hold_seconds`,
Default 4s) fährt den Pi sicher herunter - praktisch für ein Kindergerät
ohne Zugriff auf ein Terminal. Auf 0 setzen, um das abzuschalten.

## Zweiter Dreh-Encoder für Helligkeit (KY-040)

Gehört zum Standardaufbau, zusammen mit dem dimmbaren Backlight oben -
dasselbe KY-040-Modul, diesmal ohne den Taster zu verdrahten (kein eigener
Klick, nur Drehen):

| Encoder Pin | Raspberry Pi |
|-------------|--------------|
| CLK         | GPIO23       |
| DT          | GPIO12       |
| +           | 3.3V         |
| GND         | GND          |

Drehen ändert die Helligkeit (Schrittweite `gpio.brightness_step`, Standard
5%), sofort und rein manuell - es gibt kein automatisches Dimmen.

Damit Shutdown/Neustart (auch über die Web-UI unter Einstellungen bzw.
über einen "Pi neu starten"/"WLAN aus"-Funktions-Chip, siehe unten) sowie der
Update-Button auf der Info-Seite (startet nur den `owlbox`-Dienst neu, nicht
den ganzen Pi) ohne Passwortabfrage funktionieren, braucht der Service-User
`owlbox` passwortloses sudo dafür, z.B. in `/etc/sudoers.d/owlbox`:

```
owlbox ALL=(ALL) NOPASSWD: /sbin/shutdown, /usr/bin/nmcli, /usr/bin/systemctl restart owlbox
```

## Fallback-Hotspot (WLAN-Recovery)

Ist WLAN eingeschaltet, aber für `network.hotspot_after_seconds` (Standard
60s) mit keinem Netzwerk verbunden - z.B. weil das Heimnetz sein Passwort
geändert hat oder der Pi an einen neuen Ort umgezogen ist - macht der Pi
automatisch seinen eigenen Access Point auf (`nmcli device wifi hotspot`),
statt komplett unerreichbar zu bleiben. SSID und Passwort (aus
`config.yaml` unter `network:`, Standard `OwlBox-Setup` /
`owlbox-setup`) werden dafür auf dem Kiosk-Display (Banner oben) und im
Admin-Bereich (Home und Einstellungen → WLAN) angezeigt, inklusive der
URL, unter der die Einstellungen-Seite dann im Hotspot erreichbar ist
(normalerweise `http://10.42.0.1:5000/admin` - NetworkManagers
Standard-Adresse für einen geteilten Access Point).

Ablauf: mit einem Laptop/Handy in dieses WLAN einwählen, die angezeigte
URL öffnen, unter Einstellungen → WLAN das eigentliche Netzwerk
auswählen/verbinden. Sobald das klappt, beendet der Pi den Hotspot von
selbst wieder. Solange keine echte Verbindung zustande kommt, prüft er
außerdem alle `network.hotspot_retry_interval_seconds` (Standard 120s)
kurz, ob ein bereits bekanntes Netzwerk wieder in Reichweite ist, und
schaltet dann automatisch zurück.

Das WLAN-Radio explizit auszuschalten (Einstellungen oder
"WLAN aus"-Funktions-Chip) wird respektiert - der Hotspot startet dann
nicht automatisch.

**Sicherheitshinweis**: Das Standardpasswort `owlbox-setup` steht so im
Repo und ist damit öffentlich bekannt - für den Einsatz in einer Umgebung,
in der Fremde in Funkreichweite kommen könnten, unbedingt in
`config.yaml` ein eigenes Passwort setzen.

## 3.5" SPI-Display: Treiber (ohne Touch)

Diese Board-Familie (tft35a/MHS-35) funktioniert **nicht** über einen
direkten KMS-Grafikausgang, sondern über einen Trick: der Pi bekommt per
`config.txt` einen "unsichtbaren" virtuellen HDMI-Ausgang in der
Auflösung des Displays vorgegaukelt, X11/Chromium rendern ganz normal
dorthin, und ein kleines Hilfsprogramm (`fbcp`) kopiert das Bild laufend
per SPI aufs eigentliche TFT. Für den Rest des Systems (inkl. unserem
`scripts/kiosk.sh`) sieht das aus wie ein ganz normaler Bildschirm.

**Empfohlener Weg**: statt `config.txt` von Hand zu editieren, den
Treiber-Installer benutzen, den der Verkäufer laut Artikelbeschreibung
verlinkt ("kostenlose Treiberinstallation und Tutorials sind verfügbar"),
oder alternativ das quelloffene `goodtft/LCD-show`-Skript (auf GitHub,
Skriptname i.d.R. `MHS35-show` oder `LCD35-show`) - der Installer setzt
automatisch die passenden `config.txt`-Werte für genau dieses Board,
kompiliert/installiert `fbcp` und richtet den Autostart ein. Passenden
Namen/Link ggf. auf dem beiliegenden Handzettel oder in der
Amazon-Produktbeschreibung ("siehe Bild unten für Details") nachsehen.

**Danach nur einen Schritt selbst nachziehen**: in `/boot/firmware/config.txt`
die vom Installer eingetragene Touch-Zeile wieder entfernen/auskommentieren -
sie beginnt mit `dtoverlay=ads7846,...`. Ohne diese Zeile lädt der Kernel
den XPT2046-Touch-Treiber gar nicht erst, Touch ist damit auch
softwareseitig aus (zusätzlich zur ohnehin nicht verdrahteten Touch-Leitung
von oben). Die restlichen vom Installer gesetzten Zeilen (virtueller HDMI-
Modus, `dtoverlay=tft35a:rotate=...` o.ä., SPI aktivieren) unverändert
lassen.

Zur Referenz, wie diese Zeilen ungefähr aussehen (der Installer setzt sie
automatisch, exakte Werte können je nach Skriptversion leicht abweichen):

```
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=480 320 60 6 0 0 0
hdmi_drive=2
dtparam=spi=on
dtoverlay=tft35a:rotate=90
```

Und als systemd-Service für `fbcp`, falls der Installer keinen eigenen
Autostart einrichtet (Vorlage liegt in `systemd/owlbox-fbcp.service`,
Pfad ggf. anpassen falls der Installer `fbcp` woanders ablegt):

```
sudo cp systemd/owlbox-fbcp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now owlbox-fbcp.service
```

### Wichtig: legacy Grafiktreiber statt Wayland/labwc

`fbcp` liest von `/dev/fb0` - das gibt es unter dem modernen
KMS-Grafiktreiber (`vc4-kms-v3d`, Standard seit Raspberry Pi OS Bullseye/
Bookworm mit Wayland/labwc) meist nicht mehr in nutzbarer Form. Für dieses
Display-Familie also in `/boot/firmware/config.txt` den KMS-Treiber
deaktivieren bzw. auskommentieren:

```
#dtoverlay=vc4-kms-v3d
```

Empfohlenes Basis-Image ist deshalb **Raspberry Pi OS (Legacy) Lite, 64-bit**
(Bookworm, alter Grafiktreiber, aber *ohne* Desktop-Umgebung) - nicht die
volle "Legacy"-Variante mit Desktop. Der Kiosk startet X selbst nur für
Chromium (siehe "Kiosk-Autostart" unten), eine mitinstallierte
Desktop-Umgebung (lightdm, LXDE) würde beim Boot nur unnötig Zeit kosten,
ohne dass sie je zu sehen wäre. (Alternative für alle, die KMS/Wayland
behalten wollen: der Fork `fbcp-ili9341`, der über DRM statt `/dev/fb0`
liest - aufwändiger einzurichten, hier nicht weiter dokumentiert.)

### Falls es doch ein anderes Board ist

Sollte die Anleitung/Download-Karte, die dem Display beilag, einen
anderen Overlay-/Treibernamen nennen als oben: gerne den genauen Namen
schicken, dann passe ich `config.txt` und die Pin-Tabelle entsprechend an.

## Kiosk-Autostart (Chromium fullscreen, ohne Desktop-Umgebung)

Da die Basis "Legacy Lite" **keine** Desktop-Umgebung mitbringt, gibt es
auch kein lightdm/LXDE, in das sich der Kiosk einhängen könnte. Stattdessen
startet ein eigener systemd-Dienst (`owlbox-kiosk.service`) X direkt selbst
(per `startx`), übernimmt dafür `tty1` und lässt `scripts/kiosk.sh` (das
Chromium im Kiosk-Modus gegen `http://localhost:5000/` startet) als
einzigen "Client" laufen - keine Fensterleiste, kein Dateimanager-Desktop,
kein Panel. Das funktioniert, sobald `fbcp` läuft und der legacy
Grafiktreiber (nicht Wayland) aktiv ist, weil Chromium dann ganz normal auf
den virtuellen HDMI-Ausgang rendert.

**Autostart einrichten:**

```
# X ohne Display-Manager erlauben:
cat > /etc/X11/Xwrapper.config <<'EOF'
allowed_users=anybody
needs_root_rights=yes
EOF

sudo cp /opt/owlbox/systemd/owlbox-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now owlbox-kiosk.service
```

`owlbox-kiosk.service` bringt `Conflicts=getty@tty1.service` schon mit, muss
also `getty@tty1.service` nicht extra deaktiviert bekommen - läuft aber
sauberer, wenn man es trotzdem tut (`sudo systemctl disable getty@tty1.service`),
damit dort kein ungenutzter Login-Prompt mehr mitstartet.

Läuft doch eine volle Desktop-Umgebung (z.B. weil bewusst die volle
"Legacy"-Variante statt Lite geflasht wurde), lässt sich der Kiosk
alternativ ganz klassisch über deren Autostart-Datei einhängen:
`~/.config/lxsession/LXDE-pi/autostart` um die Zeile
`@/opt/owlbox/scripts/kiosk.sh` ergänzen.
