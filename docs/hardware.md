# Hardware-Aufbau

**Für genau die unten stehende Standardhardware macht `scripts/install.sh`
inzwischen alle Software-Schritte auf dieser Seite automatisch** (HiFiBerry-
Overlay in `config.txt`, ALSA-Gerät/Mixer erkennen, Kiosk-Autostart ohne
Desktop-Umgebung, ein paar Boot-Zeit-Trimms) - einfach zweimal mit einem
Neustart dazwischen laufen lassen, siehe README. Diese Seite bleibt trotzdem
die vollständige Referenz: für abweichende Hardware, zum Nachvollziehen, was
das Skript eigentlich tut, oder falls ein automatischer Schritt einmal
fehlschlägt und von Hand nachgeholt werden muss.

Zielhardware:

- **Raspberry Pi 5 (4GB)** mit aktiver Kühlung (siehe eigener Abschnitt
  unten). Ersetzt das früher hier dokumentierte Pi 3B+ - dessen vollständig
  verifiziertes Setup ist noch in der Git-Historie dieser Datei zu finden,
  falls je wieder gebraucht. Noch **nicht an echter Hardware verifiziert**.
- HiFiBerry Amp2 (I2S-Verstärker-HAT, TAS5756M-Chip) - sitzt wegen des
  Kühlkörpers **nicht mehr direkt gestapelt** auf dem 40-Pin-Header, sondern
  hängt über eine eigene Adapter-Platine dran, per Jumperkabel wie RC522/
  Taster/Encoder auch (siehe eigener Abschnitt unter „HiFiBerry Amp2"
  unten). Noch **nicht an echter Hardware verifiziert**.
- RC522 RFID-Modul (SPI, 13.56 MHz)
- **Waveshare 5" DSI Capacitive Touch Display** (Modell 5-DSI-TOUCH-A,
  720×1280, DSI-Flachbandkabel für Bild und Touch, plus 4 Jumperkabel für
  Strom/I2C, siehe unten). Ersetzt das früher hier dokumentierte offizielle
  Raspberry-Pi-7"-Touch-Display (800×480) - dessen Anleitung ist noch in
  der Git-Historie dieser Datei zu finden, falls je wieder gebraucht. Noch
  **nicht an echter Hardware verifiziert**, siehe Anschluss-Abschnitt
  unten. Davor stand hier ein 3,5"-SPI-Display (tft35a/MHS-35-Klon), auch
  dessen Anleitung ist noch in der Historie zu finden.
- 2 Taster (vor/zurück)
- 1 Dreh-Encoder mit Druckschalter (Lautstärke / Pause)
- 1 weiterer Dreh-Encoder ohne Taster (Helligkeit, s.u.)

Alle Pin-Angaben sind BCM-Nummerierung und entsprechen den Defaults in
`config/config.example.yaml`. Wer andere Pins verdrahtet, passt einfach die
`gpio:`/`rfid:` Sektion in `config/config.yaml` an. Die physischen 40-Pin-
Header-Positionen sind über alle Pi-Modelle mit 40-Pin-Header hinweg identisch
(auch der Pi 5) - nur *welcher Linux-`gpiochip`* dahintersteckt, unterscheidet
sich, siehe „Raspberry Pi 5: was sich geändert hat" unten.

**GPIO-Pinbelegung als Grafik**: `docs/owlbox-gpio-pinout.svg` zeigt den
kompletten 40-Pin-Header (physische Nummerierung wie auf der Pi-Platine) mit
Zielgerät pro Pin - aktuell für RC522 (Hardware-SPI0), direkte Verkabelung
per Jumperkabel wie in diesem Dokument beschrieben. Die Display-Zeilen dort
zeigen weiterhin nur die generische DSI-Display-Stromversorgung/-I2C-Adern
(5V/GND/SDA/SCL) - die exakte Overlay-/Auflösungs-Konfiguration für das
aktuelle Waveshare-Display steht ausschließlich hier im Text, nicht in der
Grafik. Die Grafik zeigt noch nicht die neuen HiFiBerry-Adern (I2S/I2C/
Strom) auf der Adapter-Platine - dafür bis auf Weiteres die Tabelle im
HiFiBerry-Abschnitt unten verwenden, die Grafik selbst ist dafür noch nicht
aktualisiert.

**Für den Aufbau mit eigener Adapter-Platine:** `docs/owlbox-wiring-diagram.svg`
(Gesamtaufbau), `docs/owlbox-adapter-layout.svg` (Platinenlayout-Vorschlag) und
`docs/hat-wiring.html` (kompletter Schaltplan, im Browser öffnen) zeigen eine
Bauvariante, die RC522, Taster und beide Encoder statt per direktem
Jumperkabel über eine eigene, separat verdrahtete Adapter-Platine anschließt
- aktuell für RC522 (Hardware-SPI0/CE0). **Der HiFiBerry Amp2 gehört jetzt
ebenfalls auf diese Adapter-Platine** (s.o.) - die drei genannten
Diagramme zeigen das aber noch **nicht**, nur die Tabelle im HiFiBerry-
Abschnitt unten ist dafür aktuell; die Diagramme selbst folgen, sobald der
tatsächliche Aufbau feststeht. Das Display hängt weiterhin über sein
eigenes DSI-Kabel direkt am Pi, nicht an der Adapter-Platine - nur seine
vier Strom-/I2C-Adern lassen sich optional mit über die Adapter-Platine
führen. Nur relevant, wer tatsächlich eine eigene Adapter-Platine bauen
will; für den normalen Aufbau (direkte Jumperkabel, kein eigenes Board)
sind `docs/owlbox-gpio-pinout.svg` und die Tabellen unten die maßgebliche
Referenz.

## Raspberry Pi 5: was sich geändert hat

**Dieser komplette Abschnitt ist noch nicht an echter Hardware
verifiziert** - die Software-Anpassungen unten sind vorbereitet, aber
dieses Projekt lief zum Zeitpunkt des Schreibens noch auf einem Pi 3B+.

- **GPIO-Chip-Nummer:** Auf einem Pi 3B+/4 sitzen die 40-Pin-Header-GPIOs
  direkt auf dem SoC und damit auf `/dev/gpiochip0`. Auf einem Pi 5 hängen
  sie stattdessen hinter einem separaten Chip (RP1), der je nach Kernel als
  `/dev/gpiochip4` auftaucht statt als `gpiochip0`. `owlbox/rfid/
  lgpio_compat.py` (der RC522-Reset-Pin) erkennt das jetzt automatisch -
  exakt dieselbe Erkennung, die `gpiozero`s eigene `lgpio`-Pin-Factory
  bereits für die Taster/Encoder verwendet (Revision-Code prüfen, nur auf
  `gpiochip4` wechseln, wenn der auch tatsächlich existiert), damit beide
  Hälften der GPIO-Ansteuerung dieses Projekts immer denselben Chip für
  dieselben physischen Pins verwenden.
- **`RPi.GPIO` → `rpi-lgpio`:** Die echte `RPi.GPIO`-Paket kennt den Pi 5
  gar nicht (sein Board-Erkennungscode ist älter als der Pi 5) - `import
  RPi.GPIO` bricht auf einem Pi 5 mit „This module can only be run on a
  Raspberry Pi!" ab, obwohl es genau darauf läuft. Weil die Drittanbieter-
  Bibliothek `mfrc522` beim Importieren unbedingt `import RPi.GPIO as GPIO`
  ausführt (bevor dieses Projekt die Chance hat, das auf `lgpio`
  umzuleiten, s.u.), würde allein das Importieren von `mfrc522` auf einem
  Pi 5 schon fehlschlagen. `requirements.txt` installiert seit dieser
  Erkenntnis `rpi-lgpio` statt der echten `RPi.GPIO` - ein Drop-in-Ersatz
  (selber Autor wie `gpiozero`), der sich unter demselben Importnamen
  installiert, aber intern auf `lgpio` statt auf einen direkten
  Kernel-Zugriff setzt, der auf dem Pi 5 gar nicht mehr existiert.
- **HiFiBerry-Overlay:** `dtoverlay=hifiberry-dacplus-std` statt
  `dtoverlay=hifiberry-dacplus` - siehe HiFiBerry-Abschnitt unten.
  `install.sh` wählt das automatisch anhand von `/proc/device-tree/model`.
- **Aktive Kühlung:** siehe eigener Absatz unten - läuft über den
  eingebauten 4-Pin-Lüfteranschluss, keine config.txt-/GPIO-Änderung nötig.
- **Stromversorgung:** Der Pi 5 empfiehlt offiziell ein 5V/5A-USB-C-PD-
  Netzteil (27W) - mit HiFiBerry Amp2 (kann bei Zimmerlautstärke durchaus
  über 1A aus der 5V-Schiene ziehen) und aktivem Lüfter zusammen an einem
  schwächeren Netzteil (die alten 5V/2,5-3A-Netzteile vom Pi-3B+-Aufbau)
  drohen Unterspannungswarnungen/-drosselung. Ein 3A-Netzteil reicht laut
  Raspberry Pi selbst nur bei geringerer Peripherie-Last - für diesen
  Aufbau (Amp2 unter Last plus Lüfter) das offizielle 27W-Netzteil
  verwenden.

### Aktive Kühlung

Verbaut: **GeeekPi Low-Profile Plus CPU Cooler** (Aluminium-Kühlkörper mit
Lüfter, für Pi 5 4GB/8GB/16GB). Steckt wie der offizielle Raspberry-Pi-
„Active Cooler" auf den eigenen **4-Pin-JST-Lüfteranschluss** des Pi 5
(rechts oben, zwischen 40-Pin-Header und den USB-2-Ports) - **kein GPIO-Pin,
keine config.txt-Zeile nötig**. Die Drehzahl regelt die Pi-5-Firmware selbst
temperaturabhängig (Stufen bei ca. 60°C/67,5°C/75°C), unabhängig vom
Betriebssystem. Damit ist die Kühlung für dieses Projekt reine Mechanik -
sie taucht in keiner der GPIO-Tabellen unten auf und braucht keine eigene
`config.yaml`-Einstellung.

**Nur falls stattdessen doch einmal ein anderer, GPIO-verdrahteter Lüfter
verbaut wird** (nicht der hier tatsächlich verbaute, nur zur Einordnung):
das bräuchte einen zusätzlichen freien BCM-Pin (siehe GPIO-Belegung unten,
welche noch frei sind) plus einen eigenen Fan-Overlay/eine eigene
Steuerlogik - für den GeeekPi-Kühler oben nicht relevant, der läuft komplett
über den festen 4-Pin-Anschluss.

## Anschluss: 5" Waveshare DSI Touch Display

**Dieser Abschnitt ist noch nicht an echter Hardware verifiziert** - anders
als der Rest dieser Datei. Das Display (Waveshare 5-DSI-TOUCH-A, 720×1280,
kapazitiver Touch, Aluminiumgehäuse) löst das bisherige offizielle
7"-Touch-Display (800×480) ab; dessen vollständig verifizierte Anleitung
bleibt in der Git-Historie dieser Datei erhalten, falls je wieder gebraucht.

Wie beim bisherigen Display sitzt es **nicht** auf dem 40-Pin-Header - Bild
und Touch laufen über das DSI-Flachbandkabel (eigener Steckplatz auf dem
Pi, neben den HDMI-Buchsen), keine Steckplatz-Kollision mit dem HiFiBerry,
der normal direkt auf dem 40-Pin-Header sitzt.

Die Adapter-/Power-Platine des Displays braucht vermutlich weiterhin 4
Jumper-/Dupont-Kabel zum Pi (Strom + I2C für den Touch-Controller), analog
zum bisherigen Display:

| Display-Adapterplatine | Pi-Pin (BCM) | Zweck |
|---|---|---|
| 5V  | Pin 2 oder Pin 4 | Stromversorgung |
| GND | Pin 6 (oder jeder andere GND-Pin) | Masse |
| SDA | Pin 3 (GPIO2) | I2C-Datenleitung (Touch-Controller) |
| SCL | Pin 5 (GPIO3) | I2C-Taktleitung (Touch-Controller) |

**Bitte gegen das Waveshare-eigene Handbuch/Wiki prüfen, sobald das Display
da ist** - dieses Sandbox-Netzwerk konnte waveshare.com nicht direkt
erreichen, die obige Tabelle ist aus dem bisherigen Display übernommen
(gleiches Funktionsprinzip: DSI + separate Stromversorgung + I2C-Touch),
aber nicht produktspezifisch bestätigt. Der I2C-Konflikt mit dem HiFiBerry
bleibt aus demselben Grund wie bisher unkritisch (Mehrgeräte-Bus,
unterschiedliche Adressen) - vorausgesetzt, der Touch-Controller dieses
Displays sitzt tatsächlich auch auf I2C.

**Overlay**: Laut [Waveshare-Wiki](https://www.waveshare.com/wiki/5-DSI-TOUCH-A)
(nicht direkt erreichbar, nur über Suchergebnisse geprüft - bitte
gegenlesen):

```
dtparam=i2c_arm=on
dtoverlay=vc4-kms-dsi-waveshare-panel-v2,5_0_inch_a
```

**Nicht** der bisherige `dtoverlay=vc4-kms-dsi-7inch` - das war spezifisch
für das alte offizielle Display, dieses Panel braucht einen eigenen,
produktspezifischen Overlay-Namen (auch **nicht** zu verwechseln mit dem
ähnlich klingenden `vc4-kms-dsi-waveshare-panel,5_0_inch` ohne `-v2`/`_a`,
den *andere* Waveshare-5"-DSI-Modelle verwenden - falsches Overlay dürfte
sich vermutlich genauso wie beim alten Display als komplett schwarzer
Bildschirm äußern). `install.sh` trägt das automatisch ein.

**Drehung/Rotation bewusst nicht konfiguriert.** Das Panel ist nativ
720×1280 (Hochformat) - anders als das bisherige, physisch auf dem Kopf
verbaute 800×480-Display wird die Ausrichtung hier über den physischen
Einbau gelöst, nicht per Software. Falls sich das nach dem Einbau doch
als nötig herausstellt: die Bild-Rotation gehört in `cmdline.txt` als
`video=DSI-1:<Modus>,rotate=<Grad>` (siehe Git-Historie dieser Datei für
das exakte Vorgehen beim alten Display) - **nicht** über `xrandr` oder
`display_lcd_rotate` versuchen, beide waren beim alten Display unter KMS
bestätigt wirkungslos (`xrandr --rotate` wird zwar anstandslos angenommen,
das Panel zeichnet aber nie tatsächlich neu). Bei einer 90°/270°-Drehung
zusätzlich beachten: anders als bei den bisherigen 180°, die Touch-Achsen
X/Y vertauschen - ob X11/libinput das wie beim alten Display automatisch
mitkorrigiert oder ob `invx`/`invy`/`swapxy` von Hand nötig sind, ist für
dieses Display noch nicht getestet.

**Erste tatsächliche Nutzung des Touch: Spiele-Menü.** Bisher blieb der
Touch-Controller dieses Displays komplett ungenutzt - die komplette
Kiosk-Oberfläche war reines Anzeige-Display, bedient wurde nur über
physische Taster/Encoder/RFID-Chips. Seit dem Spiele-Menü (Einstellungen
→ Spiel, aktiviert/deaktiviert per eigenem RFID-Funktions-Chip
"Spiele-Menü an/aus") ist das die **eine** Bildschirmansicht der Box, auf
der Touch tatsächlich etwas bewirkt (Menü-Kachel bzw. Karten/Felder
antippen) - überall sonst bleibt der Kiosk weiterhin reines Anzeige-Display.
Sechs Mini-Spiele hängen an diesem einen Menü: Memory, Simon Sagt,
Schiebe-Puzzle, Reaktion, Tier-Sound-Quiz und Sound-Memory (Details siehe
README.md) - jedes ein eigenes `owlbox/web/static/js/game-<name>.js`, vom
Menü-Orchestrator `game.js` per `window.OwlBoxGame<Name> = {start, stop}`
ein-/ausgeblendet. Die Client-seitige Logik braucht dafür keinerlei
zusätzlichen Treiber- oder Betriebssystem-Code: sobald der Touch-Controller
wie oben beschrieben per I2C angebunden ist, kommen Tipp-Ereignisse als
normale Browser-Klick-/Pointer-Events an, auf die jedes Mini-Spiel mit ganz
gewöhnlichen `addEventListener("click", ...)`-Handlern reagiert. **Noch
nicht an echter Hardware verifiziert** - dieses Projekt hatte bislang keine
Gelegenheit, Touch-Eingaben auf dem echten Waveshare-Display zu testen, ob
sich der Touch-Controller unter X11/Chromium tatsächlich so unauffällig
wie eine Maus meldet, wie hier angenommen.

**Zur Hintergrundbeleuchtung:** An echter Hardware bestätigt - dieses
Display bietet Helligkeitsregelung über eine interne Linux-Backlight-
Sysfs-Schnittstelle an (`/sys/class/backlight/<id>/brightness`, auf dem
geprüften Gerät als `/sys/class/backlight/11-0045/` zu finden; die
Zahl davor ist eine I2C-Bus/Adress-Kombination und kann je nach Board/
Kernel-Version abweichen). `max_brightness` war `255`, die Datei
`brightness` group-schreibbar für `video` - genau die Gruppe, die
`owlbox.service` über seine `SupplementaryGroups` ohnehin schon hat, keine
zusätzliche Berechtigung nötig. `owlbox/backlight.py` erkennt dieses
Sysfs-Gerät automatisch (`SysfsBacklight.detect()`) und nutzt es, sobald
vorhanden - **keine GPIO-Verkabelung nötig**, passend dazu, dass die
Anschluss-Tabelle oben für dieses Display ohnehin nur 4 Kabel
(5V/GND/SDA/SCL) kennt, keine separate Backlight-Leitung. Der alte
GPIO13-PWM-Transistor-Ansatz (`GpioBacklight`) bleibt als Fallback im Code,
greift aber nur noch, wenn kein Sysfs-Gerät gefunden wird - `config.yaml`s
`gpio.backlight_pin` ist für dieses Display damit praktisch irrelevant
(darf `13` oder `null` sein, beides funktioniert identisch, solange das
Sysfs-Gerät vorhanden ist). Software-seitig ist der zweite Encoder
vollständig angebunden (Drehen **und** sein Taster für den Nachtmodus,
s.u.) - der interne `brightness`-Wert ändert sich zuverlässig **und**
dimmt jetzt auch tatsächlich das Display sichtbar.

## GPIO-Belegung im Überblick

| Funktion                        | BCM Pin | Genutzt von         |
|----------------------------------|---------|---------------------|
| I2S BCLK                        | 18      | HiFiBerry           |
| I2S LRCLK                       | 19      | HiFiBerry           |
| I2S DIN                         | 20      | HiFiBerry           |
| I2S DOUT                        | 21      | HiFiBerry           |
| I2C SDA                         | 2       | HiFiBerry (Amp-Steuerung) **und** Display-Touch-Controller - gemeinsam am selben I2C-Bus, kein Konflikt (unterschiedliche Adressen), s.o. |
| I2C SCL                         | 3       | HiFiBerry (Amp-Steuerung) **und** Display-Touch-Controller, s.o. |
| SPI0 SCLK/MOSI/MISO/CE0         | 11/10/9/8 | RC522 (Hardware-SPI, s.u.) |
| SPI0 CE1                        | 7       | **frei** (nicht genutzt - der RC522 braucht nur CE0) |
| RC522 RST                       | 26      | RC522 (`rfid.reset_pin`) |
| Taster Weiter                   | 5       | Taster              |
| Taster Zurück                   | 6       | Taster              |
| Encoder CLK                     | 1       | Lautstärke-Encoder (17 ist inzwischen wieder belegt, s.u.) |
| Encoder DT                      | 27      | Lautstärke-Encoder  |
| Encoder SW                      | 22      | Lautstärke-Encoder  |
| HiFiBerry 5V (Speiseleitung)     | Pin 2 und/oder 4 (physisch, nicht BCM) | HiFiBerry - jetzt über Adapter-Platine statt direkt gestapelt, s.u. |
| HiFiBerry GND                   | z.B. Pin 6/9/14 (physisch) | HiFiBerry - über Adapter-Platine, s.u. |
| Display-Backlight               | -       | läuft über Sysfs, kein GPIO mehr - ob die Helligkeits-Änderung über den Encoder unten physisch etwas bewirkt, ist noch offen, s.u. |
| Helligkeits-Encoder CLK         | 23      | Helligkeits-Encoder |
| Helligkeits-Encoder DT          | 12      | Helligkeits-Encoder |
| Helligkeits-Encoder SW          | 17      | Helligkeits-Encoder - Nachtmodus-Umschalter (`gpio.brightness_encoder_switch`), s.u. |

## HiFiBerry Amp2

Der HiFiBerry belegt die I2S-Pins (BCM 18/19/20/21) sowie I2C (BCM 2/3)
zur Verstärkersteuerung.

In `/boot/firmware/config.txt` (bzw. `/boot/config.txt` auf älteren Images):

```
dtparam=audio=off
dtoverlay=hifiberry-dacplus
```

**Auf dem Pi 5 stattdessen `dtoverlay=hifiberry-dacplus-std`** (noch nicht
an echter Hardware verifiziert, siehe „Raspberry Pi 5: was sich geändert
hat" oben) - `install.sh` wählt das automatisch anhand des erkannten
Boards, hier zur Referenz falls von Hand eingetragen wird.

**Wichtig, an echter Hardware bestätigt (Ursache eines tagelangen
"Wiedergabe knackt/fragmentiert trotz digital korrektem Signalweg"-Rätsels):**
Der `vc4-kms-v3d`-Grafiktreiber-Overlay registriert standardmäßig **zusätzlich
eine eigene HDMI-Audio-ALSA-Karte** (taucht in `aplay -l` als `card N:
vc4hdmi` auf), auch wenn HDMI-Audio in diesem Projekt nie genutzt wird
(Anzeige läuft über DSI, Ton ausschließlich über den HiFiBerry). Diese
HDMI-Audio-Registrierung kollidiert offenbar mit dem I2S-Pfad des HiFiBerry
(beide laufen letztlich über denselben VC4-I2S/Audio-Hardwareblock) - äußert
sich als digital sauber ankommende, aber physisch knacksende/fragmentierte
Wiedergabe, dazu wiederkehrende `pcm512x`-I2C-Fehler im Kernel-Log
(`snd_soc_component_update_bits ... -5`, `snd_soc_pcm_component_pm_
runtime_get ... -22`) - bei ansonsten unauffälligem Signalweg (korrekte
`hw_params`, korrekte Mixer-Werte, korrekte I2C-Adresse). Keins der
naheliegenden Gegenmittel (Auto Mute an/aus, Bluetooth deaktivieren,
Runtime-Power-Management-Sysfs-Override, selbst ein komplett frisches
SD-Karten-Image) behebt das, weil keins davon die eigentliche Ursache
anfasst. **Der Fix: `,noaudio` an den Overlay anhängen**, damit `vc4-kms-v3d`
sich aus der Audio-Seite dieses gemeinsam genutzten Hardwareblocks
komplett heraushält:

```
dtoverlay=vc4-kms-v3d,noaudio
```

`install.sh` trägt das automatisch so ein.

**Zweite Falle, an echter Hardware bestätigt: Der Fix wirkt nur, wenn er die
EINZIGE `dtoverlay=vc4-kms-v3d`-Zeile in der Datei ist.** Ein frisches
Raspberry Pi OS Bookworm-Image bringt in `/boot/firmware/config.txt` bereits
eine eigene, unkommentierte `dtoverlay=vc4-kms-v3d`-Zeile mit (ohne
`,noaudio`, meist unter einem `[all]`-Abschnitt weiter unten in der Datei).
Anders als bei `dtparam=`-Zeilen sind `dtoverlay=`-Zeilen **nicht**
Key/Value-Overrides, sondern jede einzelne wendet den Overlay als eigene,
unabhängige Aktion an. Stehen also zwei
`dtoverlay=vc4-kms-v3d`-Zeilen in der Datei - die mitgelieferte ohne
`,noaudio` und die von `install.sh` ergänzte mit `,noaudio` - registriert die
erste trotzdem ihre eigene `vc4hdmi`-ALSA-Karte, und das Knacksen bleibt
bestehen, obwohl die korrekte Zeile ebenfalls in der Datei steht. Kontrolle:
`grep -n dtoverlay=vc4-kms-v3d /boot/firmware/config.txt` sollte genau eine
Treffer-Zeile zeigen (die mit `,noaudio`) und `aplay -l` sollte keine
`vc4hdmi`-Karte mehr auflisten. `install.sh` passt seit dieser Erkenntnis die
vorbestehende `dtoverlay=vc4-kms-v3d`-Zeile automatisch direkt an Ort und
Stelle an (statt sie zu löschen und eine eigene Kopie ans Dateiende
anzuhängen - das hält den Diff in `config.txt` minimal und die restliche
Struktur der Datei unangetastet) - auf einer schon länger laufenden
Installation reicht dafür ein erneutes `sudo owlbox-install` plus Neustart. Wichtig: dafür wirklich
`owlbox-install` verwenden (ein stabiler Befehl, den das Skript bei seinem
ersten erfolgreichen Durchlauf selbst unter `/usr/local/bin` anlegt), nicht
`cd owlbox && sudo ./scripts/install.sh` - `cd owlbox` von innerhalb eines
bereits ausgecheckten Repos landet nicht im Repo-Root, sondern eine Ebene zu
tief im gleichnamigen Python-Paket-Unterordner, und `./scripts/install.sh`
meldet dann nur „command not found“, ohne dass irgendetwas vom Skript
tatsächlich läuft - an echter Hardware genau so aufgetreten.

**Dritte Falle, ebenfalls an echter Hardware bestätigt: `dtparam=audio=on`
muss aus demselben Grund verschwinden, nicht nur auskommentiert oder von
einem späteren `dtparam=audio=off` "überschrieben" werden.** Ein frisches
Bookworm-Image bringt standardmäßig eine eigene, unkommentierte
`dtparam=audio=on`-Zeile mit. Die naheliegende Annahme - `dtparam=`-Zeilen
seien Key/Value-Overrides, bei denen die letzte Zeile in der Datei gewinnt,
also würde `install.sh`s eigenes, weiter unten stehendes
`dtparam=audio=off` automatisch siegen - hat sich an echter Hardware **nicht
zuverlässig** bestätigt: die onboard „bcm2835 Headphones“-ALSA-Karte tauchte
trotz korrekt zuletzt stehendem `dtparam=audio=off` über mehrere Neustarts
hinweg immer wieder in `aplay -l` auf. `install.sh` kommentiert seit dieser
Erkenntnis die vorbestehende `dtparam=audio=on`-Zeile automatisch direkt an
Ort und Stelle aus (`#dtparam=audio=on`), statt sich auf Override-Semantik
zu verlassen - derselbe `sudo owlbox-install` plus Neustart wie oben behebt
beides in einem Rutsch.

**Vierte Falle, an echter Hardware bestätigt: jede Live-Overlay-Änderung ohne
anschließenden Neustart kann denselben Effekt haben, unabhängig von
`config.txt`.** `raspi-config nonint do_spi 0` (macht `install.sh` beim
`rfid`-Stage, um SPI0 für den RC522 zu aktivieren) wendet den Overlay sofort
zur Laufzeit an, nicht erst beim nächsten Boot. An echter Hardware
beobachtet: danach digital alles unauffällig (Mixer korrekt, `speaker-test`
läuft fehlerfrei durch, kein ALSA-Fehler), aber kein Ton am Lautsprecher -
bis einmal sauber `sudo reboot` gemacht wurde, danach zuverlässig wieder da.
Dasselbe Symptombild wie bei einem Absturz-Loop (schnell aufeinanderfolgende
`systemctl restart` mit je einem frischen `mpv`-Start): die Ursache ist
vermutlich, dass der VC4-I2S/Audio-Hardwareblock (s.o., derselbe, den auch
der HDMI-Audio-Konflikt betrifft) irgendeine Laufzeitänderung an einem
benachbarten Peripherie-Treiber nicht sauber verkraftet. `install.sh` stößt
seit dieser Erkenntnis nach dem `rfid`-Stage automatisch einen Neustart an
(genau wie bei `sound`/`display`, wenn `config.txt` sich ändert) - auch wenn
`config.txt` diesmal unverändert bleibt, weil `dtparam=spi=on` schon
vorher drinstand. `docs/staged-setup.md` beschreibt den Ablauf: `owlbox-install
rfid` ausführen, Neustart abwarten, denselben Befehl noch einmal ausführen,
erst danach `owlbox-stage rfid`.

**An echter Hardware bestätigt:** Der Amp2 hat einen TAS5756M-Chip - das ist
dieselbe PCM512x-Chipfamilie wie bei der DAC+ Pro, ein komplett anderer Chip
als der TAS5713 des älteren Amp/Amp+. `dtoverlay=hifiberry-amp` ist speziell
für den TAS5713 und funktioniert mit dem Amp2 **nicht**: der Kernel versucht
dann, den TAS5756M unter der TAS5713-I2C-Adresse anzusprechen, bekommt keine
Antwort (`ASoC: error at snd_soc_component_probe ...: -5`), und `aplay -l`
zeigt „no soundcards found“ - äußert sich am Gerät als Lautstärke, die sich
nie ändert (bleibt bei 0). Zum Nachprüfen, welcher Chip tatsächlich verbaut
ist: `i2cdetect -y 1` - antwortet Adresse `0x4d`, ist es der TAS5756M/Amp2
(`hifiberry-dacplus`); antwortet stattdessen `0x1b`, ist es der TAS5713 vom
Amp/Amp+ (`hifiberry-amp`). Nach einer Overlay-Änderung neu starten -
dabei verschiebt sich meist auch die von `aplay -l` gemeldete Kartennummer,
siehe unten.

Danach mit `aplay -l` die Kartennummer der HiFiBerry ermitteln (z.B. `card 2:
...`) und mit `amixer -c <Kartennummer> scontrols` den Mixer-Namen prüfen -
davon in `config.yaml` eintragen: `audio.mixer_control` (Amp/Amp2 nutzen
meist `Digital`, manche Boards `PCM` oder `Master`) **und `audio.mixer_card`**
(nur die Kartennummer, ohne `hw:`/`,0`). Beide müssen zur selben Karte passen -
`install.sh` trägt sie bei der automatischen Erkennung mittlerweile ein, aber
wer das von Hand einträgt, vergisst leicht `mixer_card`: bleibt die dann auf
ihrem Standardwert `"0"` stehen während die HiFiBerry tatsächlich auf einer
anderen Kartennummer läuft, zielt jede Lautstärkeabfrage/-änderung ins Leere -
äußert sich als "eingestellte Lautstärke wird nie gespeichert, zeigt immer 0".
`audio.alsa_device` selbst bleibt normalerweise unverändert auf `"owlbox"`
stehen (siehe unten) - das ist das dmix-Gerät aus `/etc/asound.conf`, nicht
die rohe Kartennummer. Läuft die HiFiBerry nicht auf Karte 0, muss stattdessen
das `slave.pcm "hw:0,0"` in `/etc/asound.conf` (Stage `sound` in `install.sh`,
Abschnitt „Kein Ton" in `docs/staged-setup.md`) auf die richtige Kartennummer
angepasst werden - `alsa_device` direkt auf eine rohe `"hw:<Kartennummer>,0"`
zu setzen funktioniert zwar auch, bringt dann aber den unten beschriebenen
mpv/aplay-Konflikt zurück (Hinweistöne würden nie mehr spielen).

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

### Nicht mehr direkt aufgesteckt: Anschluss über Adapter-Platine

**Dieser Abschnitt ist noch nicht an echter Hardware verifiziert.** Wegen
des Kühlkörpers auf dem Pi 5 sitzt der Amp2 nicht mehr direkt gestapelt auf
dem Pi-eigenen 40-Pin-Header, sondern auf einem eigenen, auf der
Adapter-Platine aufgelöteten 40-Pin-Stecker. Wichtig: Der Amp2 ist ein
**HAT** und hat - anders als RC522/Taster/Encoder - keine einzelnen
Lötpads für BCLK/LRCLK/SDA/etc., sondern ausschließlich diesen einen
kompletten 40-Pin-Header als Schnittstelle. Er kann also nicht wie die
übrigen Bauteile per Einzel-Jumperkabel angeschlossen werden.

Der Aufbau in zwei Schritten:

1. Auf die Adapter-Platine wird eine vollständige 40-Pin-Buchse gelötet.
   Der Amp2 steckt komplett und mechanisch genau wie bei einem normalen
   Pi-Stack auf diese Buchse - exakt wie sonst direkt auf den Pi.
2. Von dieser 40-Pin-Buchse wird über einen zweiten Stecker **nur** die
   tatsächlich benötigte Teilmenge der Pins (siehe Tabellen unten) mit
   dünnerem Kabel zum Pi-eigenen Header weiterverbunden. Die übrigen
   Pin-Positionen der Buchse bleiben mechanisch belegt, aber elektrisch
   unbeschaltet.

Eine bebilderte Übersicht dazu (inkl. aller anderen Bauteile) gibt es in
`docs/owlbox-adapter-wiring-pi5.svg`.

Alle sechs für diesen Anschluss relevanten Signal-/Steuerleitungen, wie
oben schon einzeln erwähnt:

| HiFiBerry Amp2 | Pi-Pin (BCM) | Zweck |
|---|---|---|
| BCLK | GPIO18 | I2S-Bit-Clock |
| LRCLK/WS | GPIO19 | I2S-Wortauswahl (links/rechts) |
| DIN | GPIO20 | I2S-Audiodaten |
| DOUT | GPIO21 | I2S (vom Amp2 ungenutzt für reine Wiedergabe, trotzdem verbinden) |
| SDA | GPIO2 | I2C-Datenleitung (Verstärkersteuerung, Lautstärke/Mute-Register) |
| SCL | GPIO3 | I2C-Taktleitung (Verstärkersteuerung) |

Dazu **Stromversorgung, getrennt von den Signalleitungen zu betrachten**:

| HiFiBerry Amp2 | Pi-Pin (physisch) | Zweck |
|---|---|---|
| 5V | Pin 2 und Pin 4 (beide, siehe unten) | Versorgung des kompletten Verstärkers inkl. Lautsprecherausgang |
| GND | mindestens 1-2 der GND-Pins (z.B. 6, 9, 14) | Masse |

**Wichtig, unabhängig von echter Hardware ableitbar (Elektrotechnik, nicht
projektspezifisch getestet):** Anders als bei RC522/Tastern/Encodern, die
nur Milliampere-Signalpegel führen, zieht der Amp2 seine komplette
Lautsprecher-Ausgangsleistung direkt aus der 5V-Schiene (Class-D-Verstärker
- die Ausgangsleistung kommt praktisch 1:1 aus der Versorgungsspannung,
nicht aus einer separaten Verstärkerstufe). Bei Zimmerlautstärke können das
ohne Weiteres deutlich über 1A sein, kurzzeitig bei Bässen/hoher Lautstärke
auch mehr. Für diese eine Verbindung **nicht** dieselben dünnen
Jumper-/Dupont-Kabel wie für RC522/Taster/Encoder verwenden (typischerweise
nur für < 1A ausgelegt, spürbarer Spannungsabfall bei mehr) - stattdessen:

- Beide 5V-Pins (2 und 4) UND mehrere GND-Pins parallel nutzen, nicht nur je
  einen - reduziert den Übergangswiderstand.
- Wenn möglich kurze, dickere Leitungen (z.B. AWG 20 oder dicker) statt
  Standard-Dupont-Kabel für genau diese beiden Adern.
- Nach dem Zusammenbau prüfen: `vcgencmd get_throttled` sollte `0x0` zeigen
  (keine Unterspannung); bei hörbarem Verzerren/Aussetzern unter Last zuerst
  hier ansetzen, bevor andere Ursachen gesucht werden.
- **Kein 3.3V-Pin nötig** - der Amp2 hat kein `ID_SD`/`ID_SC`-EEPROM, über
  das dieses Projekt ihn erkennen lässt (der Overlay wird manuell in
  `config.txt` eingetragen, s.o.), entsprechend bleibt auch der sonst dafür
  reservierte 3.3V-Pin unbenutzt.

Die genaue Stromaufnahme steht im Datenblatt des Amp2 (HiFiBerry-eigene
Seite) - vor dem endgültigen Verkabeln dort noch einmal gegenprüfen, welcher
Peak-Strom bei voller Lautstärke/4-Ω-Last tatsächlich zu erwarten ist.

## AirPlay (optional, shairport-sync)

**Kein zusätzliches Kabel, kein zusätzlicher Chip** - AirPlay läuft komplett
über WLAN und dieselbe HiFiBerry-Ausgabe, die OwlBox ohnehin schon nutzt.
Ein optionales Software-Add-on: `sudo ./scripts/install.sh airplay`
installiert [shairport-sync](https://github.com/mikebrady/shairport-sync),
den etablierten Open-Source-AirPlay-Empfänger für Linux, als eigenen
systemd-Dienst - **bewusst nicht** Teil von `sudo ./scripts/install.sh`
(bzw. `all`) ohne Argument, da es kein Kernbestandteil der Box ist, sondern
ein optionales Extra für Eltern, die vom Handy/Mac aus eigene Musik über
denselben Lautsprecher abspielen wollen, ohne einen Chip aufzulegen.

**Zusammenspiel mit der eigentlichen Wiedergabe:** mpv (für Geschichten) und
shairport-sync (für AirPlay) würden sich sonst dasselbe ALSA-Gerät streitig
machen bzw. - schlimmer - beide gleichzeitig hörbar übereinanderlaufen.
Gelöst über automatisches Ducking statt gemeinsamer ALSA-Nutzung:
shairport-sync ruft über seine `sessioncontrol`-Hooks
(`run_this_before_play_begins`/`run_this_after_play_ends`, siehe
`/etc/shairport-sync.conf`, geschrieben vom Installer) zwei kleine Skripte
auf (`scripts/airplay-session-start.sh`/`-end.sh`, per `curl` gegen
`127.0.0.1:5000`), die wiederum `Engine.airplay_session_started()`/
`_ended()` antriggern:

- **Session-Start**: läuft gerade eine Geschichte, wird sie pausiert
  (Position wie gewohnt gespeichert) - lief nichts, passiert nichts.
- **Session-Ende**: nur falls der Start-Hook tatsächlich pausiert hat, wird
  die Geschichte wieder fortgesetzt. Eine Geschichte, die schon vorher aus
  einem anderen Grund pausiert war (z.B. Einschlaf-Timer), bleibt pausiert.

Auf dem Kiosk-Display erscheint währenddessen unten rechts ein kleines
„📡 AirPlay"-Abzeichen (`owlbox/web/static/js/player.js`, gespeist aus
`state.airplay.active`), damit auf einen Blick klar ist, warum eine
Geschichte gerade pausiert wirkt.

Die beiden `/api/airplay/session-start`/`-end`-Endpunkte (siehe
`owlbox/web/api.py`) sind bewusst **nicht** `@admin_required` - ein
headless laufendes Systemd-Skript kann keinen Login-Flow durchlaufen -
stattdessen auf lokale Aufrufe beschränkt (`request.remote_addr` gegen
`127.0.0.1`/`::1` geprüft, nicht spoofbar wie ein Header). Genau das ist
shairport-sync als lokal laufender Dienst auf demselben Pi immer.

**AirPlay-Version:** das Debian/Raspberry-Pi-OS-Paket unterstützt AirPlay 1
(von praktisch jeder AirPlay-Quell-App weiterhin akzeptiert, nur ohne
AirPlay 2s Mehrraum-/„Gerade läuft"-Zusatzfunktionen). AirPlay 2 bräuchte
einen Build aus dem Quellcode mit zusätzlichen Abhängigkeiten (`nqptp`,
`libplist`, `libsodium`, `libavahi-client`) - zu fehleranfällig, um das
blind ohne echte Hardware zum Gegenprüfen zu skripten; bei Bedarf siehe
shairport-sync-eigene Doku.

**Noch nicht an echter Hardware verifiziert** - wie der Rest dieser Datei
für die aktuelle Pi-5-Ausbaustufe: weder der `apt install shairport-sync`-
Ablauf noch das tatsächliche Ducking-Verhalten (Pause/Fortsetzen im
richtigen Moment, kein hörbares Überlappen) wurden bisher an einem echten
Gerät gegengeprüft, nur die OwlBox-eigene Seite (Engine-Methoden, API-
Endpunkte, Kiosk-Abzeichen) über die Testsuite bzw. den Simulationsmodus.

## Mehrraum-Wiedergabe (optional, Snapcast)

Mehrere OwlBoxen im selben Haus/WLAN können denselben Ton synchron
wiedergeben - eine Box ist die **Hauptbox**, alle anderen **Slave-Boxen**
geben nur deren Ton aus. Löst das über [Snapcast](https://github.com/badaix/snapcast),
dasselbe "auf ein bewährtes, dafür gebautes externes Tool setzen statt
selbst ein Sync-Protokoll erfinden" wie bei AirPlay/shairport-sync oben.

**Architektur:** Die Hauptbox schreibt ihren Ton statt direkt auf die
HiFiBerry-ALSA-Karte in eine benannte Pipe (`/tmp/owlbox-multiroom.fifo`,
siehe `owlbox/player.py`s `_audio_output_args` - nur wenn eine Rolle aktiv
ist, der Standard-Ein-Box-Betrieb bleibt komplett unverändert). `snapserver`
liest diese Pipe und verteilt den Ton synchron an alle verbundenen
`snapclient`-Instanzen. **Jede Box, die tatsächlich Ton macht - die
Hauptbox eingeschlossen** - läuft dabei selbst als `snapclient`
(`owlbox-snapclient.service`, siehe `systemd/owlbox-snapclient.service`):
die Hauptbox hört ihren eigenen weitergereichten Stream über `127.0.0.1`
genauso wie jede Slave-Box den echten Netzwerknamen der Hauptbox. Welchen
Host der eigene `snapclient` ansteuert, steht in einer einfachen Textdatei
(`/tmp/owlbox-multiroom-host.txt`), die die App selbst schreibt (kein
sudo nötig) - nur das (Neu-)Starten des systemd-Dienstes selbst braucht
die passwortlose sudo-Regel aus `scripts/install.sh`.

**Installation:**

```bash
sudo ./scripts/install.sh multiroom
```

Installiert `snapserver`+`snapclient`+`avahi-utils`, schreibt
`/etc/snapserver.conf` (Pipe-Quelle, `sampleformat=48000:16:2` - muss exakt
zu `player.py`s eigener `--audio-samplerate`/`--audio-channels`/
`--audio-format` passen, beide Seiten sind dieses Projekts eigener Code),
richtet `owlbox-snapclient.service` ein und legt die Pipe an - all das
bewusst **ohne** etwas zu aktivieren/starten, das hängt von der später
gewählten Rolle ab. Eine Ausnahme: `owlbox-mdns.service` (Selbstankündigung
im Netzwerk, siehe unten) läuft sofort, unabhängig von jeder Rolle - eine
Box muss auffindbar sein, bevor irgendeine Rolle überhaupt gewählt werden
kann.

**Automatische Erkennung (kein manuelles Verknüpfen):** Jede Box mit
installierter `multiroom`-Stufe meldet sich per mDNS im Netzwerk an
(`avahi-publish-service`, derselbe Avahi-Dienst, der schon `<hostname>.local`
bereitstellt - siehe `systemd/owlbox-mdns.service`) und durchsucht beim
Laden von Einstellungen > Netzwerk automatisch das Netzwerk nach anderen
OwlBoxen (`avahi-browse`, siehe `owlbox/multiroom.py`s `discover_peers`).
Gefundene Boxen erscheinen unter "Andere OwlBoxen im Netzwerk" von selbst -
nichts einzutragen, auf keiner der Boxen. Ein manuelles Eintragen per
Name+Hostname/IP bleibt als Rückfallebene bestehen (z.B. für ein WLAN mit
Client-Isolation, wo mDNS nicht durchkommt).

**Komplett deaktivierbar:** Die ganze Funktion ist standardmäßig aus
(auf jeder Box einzeln, wie jedes andere optionale Add-on in dieser App).
Solange "Mehrraum-Wiedergabe aktivieren" nicht angehakt ist, tut die Box
nichts dergleichen - keine mDNS-Netzwerksuche, kein Abfragen anderer Boxen,
kein Snapcast. Wer die Funktion nie nutzen möchte, muss nichts weiter tun.

**Einrichtung:**

1. Auf jeder beteiligten Box: `sudo ./scripts/install.sh multiroom`.
2. Auf jeder beteiligten Box: Einstellungen > Netzwerk > "Mehrraum-Wiedergabe
   aktivieren" anhaken, speichern.
3. Auf **genau der einen** Box, die den Ton vorgeben soll: zusätzlich "Diese
   Box ist die Hauptbox" aktivieren, speichern, `owlbox.service` neu starten.

Das war's - jede andere Box mit installierter `multiroom`-Stufe und
aktivierter Mehrraum-Wiedergabe erkennt automatisch (per periodischem
`/api/state`-Abruf bei jeder bekannten Box, `Engine._check_multiroom`, alle
15s), dass eine Hauptbox aktiv ist, und schaltet sich selbst als Slave-Box
dazu, ganz ohne eigenen Rollen-Schalter. Wird der Hauptbox-Schalter wieder
ausgeschaltet oder auf eine andere Box verschoben, folgen alle automatisch
dorthin bzw. fallen in den normalen Einzelbetrieb zurück. Wird die
Mehrraum-Wiedergabe selbst wieder deaktiviert, schaltet sich diese Box sofort
komplett ab (auch als Hauptbox, falls sie gerade eine war) und hört auf,
andere Boxen abzufragen.

**Hauptbox wechseln:** Einfach auf der neuen Box den Haken setzen - die
alte schaltet sich von selbst wieder aus, kein vorheriges manuelles
Deaktivieren nötig. Dahinter steckt kein Raten: jede Box merkt sich beim
Aktivieren einen Zeitstempel ("seit wann bin ich Hauptbox") und meldet ihn
über dasselbe `/api/state` mit. Beanspruchen zwei Boxen die Rolle
gleichzeitig, gewinnt schlicht die mit dem späteren Zeitstempel - die
ältere erkennt das bei ihrem eigenen nächsten Check (auch eine Hauptbox
fragt weiterhin regelmäßig bei ihren bekannten Boxen nach, gerade um genau
das zu bemerken), schaltet ihren eigenen Haken automatisch aus und wird
selbst zur Slave-Box der neuen Hauptbox. Jede Box kommt dabei unabhängig
zum exakt gleichen Ergebnis, ohne dass eine Box einer anderen einen Befehl
schickt.

Ein Klick auf "Öffnen" neben einem gefundenen Peer wechselt direkt in
dessen Verwaltungsoberfläche (`http://<host>:5000/admin`) - praktisch, um
mehrere Boxen zu verwalten, ohne sich jeden Hostnamen einzeln zu merken.
Der grüne/graue Punkt davor ist ein kurzer Erreichbarkeits-Check beim Laden
der Seite, kein Dauer-Polling; ein 🔊-Symbol markiert, welche Box gerade
die Hauptbox ist.

**Sicherheit:** Die automatische Rollenübernahme fragt ausschließlich beim
schon länger öffentlichen, unauthentifizierten `/api/state` jeder Box nach
(genau das, was auch das Kiosk-Display selbst abfragt) - keine neuen
Zugangsdaten, kein gemeinsames Geheimnis zwischen den Boxen, keine
Fernsteuerung einer Box durch eine andere. Jede Box wendet eine Rolle
ausschließlich auf sich selbst an.

**Lautstärke/Hinweistöne:** Die Hauptbox steuert Lautstärke weiterhin über
den echten Hardware-Mixer (`amixer`, siehe `player.py`s `AlsaMixer`) -
unverändert, unabhängig davon, ob mpv gerade in die Pipe oder direkt auf
die Karte schreibt. `owlbox-snapclient.service` läuft deshalb explizit mit
`--mixer none`, damit Snapcast keine eigene Lautstärkeregelung obendrauf
legt. Hinweistöne (`feedback.play_chime`) laufen weiterhin über `aplay`,
seit Kurzem aber wie mpv/`snapclient` selbst über das dmix-Gerät `owlbox`
(`/etc/asound.conf`, siehe „Kein Ton" in `docs/staged-setup.md` sowie
`audio.alsa_device` weiter oben) statt direkt über eine rohe `hw:X,Y`-Karte -
an echter Hardware bestätigt: ohne dmix hielt mpv (`--idle=yes`) die rohe
Karte durchgehend offen, wodurch `aplay` sie praktisch nie öffnen konnte und
Hinweistöne komplett ausblieben, nicht nur gelegentlich. Kollidiert trotz
dmix trotzdem mal etwas, wird der Chime übersprungen und als WARNING
geloggt (siehe `owlbox/feedback.py`), exakt dasselbe bekannte Verhalten wie
beim AirPlay-Ducking oben - keine neue Fehlerklasse.

**Noch nicht an echter Mehrgeräte-Hardware verifiziert** - deutlich mehr
noch als bei AirPlay: weder die `snapserver`/`snapclient`/`avahi-utils`-
Paketinstallation, noch die genauen Kommandozeilenflags in
`systemd/owlbox-snapclient.service`/`owlbox-mdns.service`, noch das
tatsächliche mDNS-Auffinden über `avahi-browse`s Ausgabeformat, noch (am
wichtigsten) die tatsächliche Sample-genaue Synchronisation über mehrere
echte Geräte hinweg wurden bisher getestet - nur die OwlBox-eigene Seite
(automatische Rollenübernahme, Peer-Erkennung, Audio-Routing-Logik in
`player.py`) über die Testsuite und den Simulationsmodus. Vor dem
Erstaufbau lohnt sich ein Blick in die Snapcast- und Avahi-eigene
Dokumentation, um die hier getroffenen Annahmen (Paketnamen,
`snapserver.conf`-Syntax, `snapclient`-Flags, `avahi-browse -p`-Format)
gegenzuprüfen.

## RC522 RFID-Leser (Hardware-SPI0)

Der RC522 hängt an SPI0, dem Hardware-SPI-Bus des Pi (`/dev/spidev0.0`,
CE0). Grund, warum das möglich ist: SPI1 liegt auf GPIO18-21, exakt den
Pins, die der HiFiBerry für I2S-Ton braucht - SPI0 ist mit dem aktuellen
DSI-Touch-Display aber frei (anders als beim frühren SPI-Display, dessen
Overlay beide Chip-Selects von SPI0 belegte). SPI selbst muss aktiviert
sein (macht `scripts/install.sh` via `raspi-config nonint do_spi 0`).

| RC522 Pin | Raspberry Pi | Config-Feld |
|-----------|--------------|-------------|
| VCC       | 3.3V (**nicht 5V!**) | - |
| GND       | GND          | - |
| RST       | GPIO26       | `rfid.reset_pin` |
| SDA (CS)  | GPIO8 (SPI0 CE0) | - |
| SCK       | GPIO11 (SPI0 SCLK) | - |
| MOSI      | GPIO10 (SPI0 MOSI) | - |
| MISO      | GPIO9 (SPI0 MISO)  | - |
| IRQ       | nicht verbunden | - |

Die `mfrc522`-Python-Bibliothek spricht den Bus direkt über `spidev` an,
kein Bit-Banging mehr nötig - siehe `owlbox/rfid/mfrc522_reader.py` für
Details. (Die frühere Software-SPI-Implementierung, `owlbox/rfid/soft_spi.py`,
bleibt im Repo bestehen - getestet, weiterverwendbar, aber seit dieser
Umstellung nicht mehr der Standardpfad.)

**Wichtig, an echter Hardware bestätigt:** Der RC522-Reset-Pin läuft über
`lgpio` (`owlbox/rfid/lgpio_compat.py`), **nicht** über `RPi.GPIO` - obwohl
die `mfrc522`-Bibliothek intern eigentlich fest auf `RPi.GPIO` setzt (wird
per `unittest.mock.patch` umgeleitet, nur für diesen einen Pin - die
SPI-Datenleitungen selbst laufen über den Kernel-`spidev`-Treiber, gar nicht
über GPIO). Grund: `gpiozero` (Taster/Encoder) braucht auf aktuellen
Kerneln zwingend `lgpio`, weil `RPi.GPIO`s eigene Kantenerkennung dort mit
„Failed to add edge detection" abbricht. `RPi.GPIO` zeigte in diesem
Prozess außerdem selbst für Pins, die sonst nichts anfasst, sofort „already
in use"-Warnungen - ein Zeichen, dass es auf diesem Kernel generell nicht
sauber läuft. Deshalb läuft die komplette GPIO-Ansteuerung dieses Projekts
konsistent über `lgpio`, nirgends mehr über `RPi.GPIO`.

**Auf dem Pi 5 kommt eine zweite, noch nicht an echter Hardware verifizierte
Ebene desselben Themas dazu:** die echte `RPi.GPIO`-Bibliothek unterstützt
den Pi 5 gar nicht - `import RPi.GPIO` bricht dort ab, bevor `mfrc522`
überhaupt fertig importiert ist, also bevor dieses Projekt die Chance hat,
irgendetwas umzuleiten. `requirements.txt` installiert deshalb `rpi-lgpio`
(ein Drop-in-Ersatz, installiert sich unter demselben `RPi.GPIO`-Namen,
läuft aber selbst schon auf `lgpio`) statt der echten `RPi.GPIO` - siehe
„Raspberry Pi 5: was sich geändert hat" oben für den genauen Grund.
Zusätzlich wählt `owlbox/rfid/lgpio_compat.py` jetzt automatisch den
richtigen `lgpio`-Chip (`gpiochip4` statt `gpiochip0` auf einem Pi 5, falls
vorhanden) - exakt dieselbe Erkennung, die `gpiozero`s eigene
`lgpio`-Pin-Factory für die Taster/Encoder ohnehin schon macht.

**Historischer Hintergrund zum Lautstärke-Encoder auf GPIO1 statt GPIO17:**
Das frühere SPI-Display beanspruchte zusätzlich zu SPI0 CE0/CE1 auch
**GPIO17 als Interrupt-Pin („pendown") für den (nie verdrahteten) Touch-
Controller** - fest im damaligen Overlay einprogrammiert, unabhängig davon,
ob Touch physisch angeschlossen war. Deshalb liegt der Lautstärke-Encoder-CLK
auf **GPIO1** (ID_SC, konventionell für ein HAT-ID-EEPROM reserviert, hier
aber echt frei, da der HiFiBerry ohnehin per manueller `dtoverlay`-Zeile
statt EEPROM-Erkennung konfiguriert wird). Mit dem neuen DSI-Display war
GPIO17 zwischenzeitlich wieder frei - inzwischen aber wieder belegt, siehe
„Zweiter Dreh-Encoder für Helligkeit" unten (dessen Taster für den
Nachtmodus). Die Verkabelung des Lautstärke-Encoders bleibt trotzdem auf
GPIO1, um nicht ohne Grund vom dokumentierten Standard abzuweichen.

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
| CLK         | GPIO1 (nicht 17 - siehe „RC522 RFID-Leser" weiter oben) |
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
dasselbe KY-040-Modul wie beim Lautstärke-Encoder, diesmal **mit** Taster
(anders als früher, s.u. warum):

| Encoder Pin | Raspberry Pi |
|-------------|--------------|
| CLK         | GPIO23       |
| DT          | GPIO12       |
| SW          | GPIO17 (`gpio.brightness_encoder_switch`) |
| +           | 3.3V         |
| GND         | GND          |

Drehen ändert die Helligkeit (Schrittweite `gpio.brightness_step`, Standard
5%), sofort und rein manuell - es gibt kein automatisches Dimmen. Das
Waveshare-Display kann laut Auftraggeber seine Helligkeit auch eigenständig
per Touch regeln - diese Box nutzt das **bewusst nicht**, ausschließlich
den Encoder/die Web-UI. Beide gleichzeitig zu verwenden würde die hier
gespeicherte `brightness`-Einstellung und die tatsächliche
Display-Helligkeit auseinanderlaufen lassen, ohne dass OwlBox davon etwas
mitbekommt - die Touch-Helligkeitsregelung des Displays also am besten gar
nicht erst anfassen.

**An echter Hardware bestätigt:** der Encoder dimmt das Display jetzt auch
sichtbar - siehe „Zur Hintergrundbeleuchtung" oben für den dabei
verwendeten Mechanismus (Sysfs-Backlight-Gerät, automatisch erkannt).

**Nachtmodus, noch nicht an echter Hardware verifiziert:** Ein Druck auf den
Taster (SW) schaltet zwischen der normalen ("Tag"-)Helligkeit und einer
separat konfigurierbaren, oft deutlich dunkleren Nachtmodus-Helligkeit um -
konfigurierbar in Einstellungen → Anzeige (`night_brightness`, Standard 5%).
Anders als die normale Helligkeit darf die Nachtmodus-Helligkeit bewusst
unter die dort eingestellte Minimal-Helligkeit gehen, das ist der ganze
Zweck. Kein Zeitplan - bleibt aktiv, bis erneut gedrückt wird, außer über
einen Neustart hinweg (startet immer im Tag-Modus). Ändert sich die
Helligkeit während des Nachtmodus direkt (Schieberegler, Drehen an
demselben Encoder), beendet das den Nachtmodus automatisch, statt den neuen
Wert beim nächsten Tastendruck wieder zu verwerfen - siehe
`Engine.toggle_night_mode`/`Engine._exit_night_mode_without_restoring_locked`
in `owlbox/engine.py`. `gpio.brightness_encoder_switch` auf `null` setzen,
um den Taster unverdrahtet zu lassen und die Funktion nur über die Web-UI
nutzbar zu machen (dort geht sie immer, unabhängig von diesem Pin).

Damit Shutdown/Neustart (auch über die Web-UI unter Einstellungen bzw.
über einen "Pi neu starten"/"WLAN aus"-Funktions-Chip, siehe unten), der
Update-Button auf der Info-Seite (startet nur den `owlbox`-Dienst neu, nicht
den ganzen Pi) sowie der Gerätename in Einstellungen > System (siehe unten)
ohne Passwortabfrage funktionieren, braucht der Service-User `owlbox`
passwortloses sudo dafür. **`scripts/install.sh` richtet das automatisch ein**
(`/etc/sudoers.d/owlbox`, syntaxgeprüft per `visudo -c` vor dem Einspielen) -
hier nur zur Referenz bzw. zum manuellen Nachtragen auf einer Installation von
vor dieser Automatisierung:

```
owlbox ALL=(ALL) NOPASSWD: /sbin/shutdown, /usr/bin/nmcli, /usr/bin/systemctl restart --no-block owlbox, /usr/bin/hostnamectl set-hostname *
```

**Wichtig:** Die Argumente müssen exakt so dastehen wie hier gezeigt (inklusive
`--no-block`) - sudo vergleicht die komplette Befehlszeile, nicht nur den
Programmnamen. Fehlt `--no-block` in der sudoers-Zeile, meldet der
Update-Button auf der Info-Seite beim Neustart `sudo: a password is required`,
weil der tatsächlich ausgeführte Befehl dann nicht mehr zur Regel passt. Ein
einfaches `git pull` reicht auf einem Bestandssystem nicht, um eine bereits
vorhandene `/etc/sudoers.d/owlbox` zu aktualisieren - dafür entweder
`sudo owlbox-install` erneut laufen lassen oder die Zeile per
`sudo visudo -f /etc/sudoers.d/owlbox` von Hand anpassen.

### Gerätename (mehrere OwlBoxen im selben Haus/WLAN unterscheiden)

Einstellungen > System > "Gerätename" ändert den echten Linux-Hostnamen des
Pi selbst (`hostnamectl set-hostname`, siehe `owlbox/system_info.py`), nicht
nur eine kosmetische Anzeigebezeichnung. Freitext wird dabei automatisch in
einen gültigen Namen umgewandelt (Kleinbuchstaben/Ziffern/Bindestriche, siehe
`normalize_hostname`) - "Kinderzimmer!" wird z.B. zu "kinderzimmer". Der neue
Name erscheint sofort oben neben "OwlBox" auf jeder Verwaltungsseite (nicht
auf dem Kiosk-Display, `player.html` bindet `_admin_nav.html` gar nicht erst
ein) sowie im Browser-Tab-Titel - beides über `/api/system/hostname` (GET),
live bei jedem Seitenaufruf abgefragt statt in einer eigenen DB-Spalte
dupliziert, damit es nie mit dem echten Hostnamen auseinanderlaufen kann.

Für volle Erreichbarkeit unter dem neuen `<name>.local` im ganzen Netzwerk
(mDNS/Avahi - bei Raspberry Pi OS vorinstalliert, keine eigene Einrichtung
nötig) empfiehlt sich danach ein Neustart, da avahi-daemon eine
Laufzeit-Umbenennung nicht unbedingt von selbst bemerkt.

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

## DSI-Display: kein separater Treiber-Installer nötig

Im Gegensatz zum früheren 3,5"-SPI-Display (das einen virtuellen-HDMI-Trick,
`fbcp` und den alten Legacy-Grafiktreiber brauchte, um überhaupt ein Bild zu
zeigen) kommt das aktuelle DSI-Display an einem normalen Raspberry Pi OS
Bookworm-Image **ohne Treiber-Installer, ohne extra Paket** aus - nur die
eine `dtoverlay=`-Zeile aus dem Anschluss-Abschnitt oben ist nötig, sonst
nichts. Empfohlenes Basis-Image bleibt **Raspberry Pi OS Lite, 64-bit**
(ohne Desktop-Umgebung) - der Kiosk startet X selbst nur für Chromium
(siehe unten), eine mitinstallierte Desktop-Umgebung (lightdm, LXDE) würde
beim Boot nur unnötig Zeit kosten, ohne dass sie je zu sehen wäre. Wichtig
ist nur: der moderne KMS-Grafiktreiber (`vc4-kms-v3d`) bleibt **aktiv**
(Bookworm-Standard) - er wurde beim alten SPI-Display extra deaktiviert,
das ist mit einem DSI-Display nicht mehr nötig und würde die
GPU-Beschleunigung sogar wieder kosten.

### Falls es doch ein anderes Board ist

Sollte es ein anderes DSI-Board als das oben genannte Waveshare-Modell
sein, oder falls Waveshare für dieses Modell zwischenzeitlich ein anderes
Vorgehen dokumentiert als oben angenommen: gerne kurz Bescheid geben, dann
passe ich diese Seite an.

## Kiosk-Autostart (Chromium fullscreen, ohne Desktop-Umgebung)

Da die Basis "Lite" **keine** Desktop-Umgebung mitbringt, gibt es auch kein
lightdm/LXDE, in das sich der Kiosk einhängen könnte. Stattdessen startet
ein eigener systemd-Dienst (`owlbox-kiosk.service`) X direkt selbst (per
`startx`), übernimmt dafür `tty1` und lässt `scripts/kiosk.sh` (das Chromium
im Kiosk-Modus startet) als einzigen "Client" laufen - keine Fensterleiste,
kein Dateimanager-Desktop, kein Panel. Mit aktivem KMS-Treiber findet X's
eigener, automatisch gewählter "modesetting"-Treiber `/dev/dri/card0` von
selbst - keine eigene Xorg-Konfiguration nötig (anders als beim alten
Display, das X explizit auf einen Framebuffer-Treiber zwingen musste).

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

Läuft doch eine volle Desktop-Umgebung (z.B. weil bewusst die volle Variante
statt Lite geflasht wurde), lässt sich der Kiosk alternativ ganz klassisch
über deren Autostart-Datei einhängen: `~/.config/lxsession/LXDE-pi/autostart`
um die Zeile `@/opt/owlbox/scripts/kiosk.sh` ergänzen.

`owlbox-kiosk.service` läuft bewusst mit niedrigerer CPU-/IO-Priorität als
`owlbox.service` (`Nice=15`, `IOSchedulingClass=best-effort`,
`IOSchedulingPriority=7`). Grund: Chromium läuft auf dieser Hardware
komplett softwaregerendert (keine GPU-Beschleunigung verfügbar) - ohne eine
Prioritätsdifferenz konkurrieren Chromium und `mpv` (läuft in
`owlbox.service`) mit exakt gleicher Priorität um die knappe CPU eines Pi
3B+. Ein positiver `Nice`-Wert braucht keine besonderen Rechte (nur ein
*negativer*, also höhere Priorität als Standard, würde das) - `install.sh`
trägt das automatisch ein und startet `owlbox-kiosk.service` bei Bedarf
neu, damit die neue Priorität auch ohne kompletten Neustart greift.

**Hinweis für den Pi 5:** Der komplette Rest dieses Abschnitts (Nice-Fix,
die folgenden zwei Korrekturen/Vermutungen zum Knacken, die entfernten
Dauerschleifen) wurde ausschließlich an einem Pi 3B+ untersucht - "die
knappe CPU eines Pi 3B+" trifft auf einen Pi 5 (deutlich schnellere CPU,
zudem echte GPU-Beschleunigung für Chromium grundsätzlich möglich) so
womöglich gar nicht mehr zu. Die Priorisierung selbst bleibt harmlos und
wird nicht entfernt, aber ob sie auf einem Pi 5 überhaupt noch etwas
bewirkt (oder das zugrundeliegende Knack-Problem auf dieser Hardware
überhaupt noch auftritt) ist offen - noch nicht an echter Pi-5-Hardware
verifiziert.

**Korrektur, an echter Hardware geprüft:** Dieser Nice-Fix allein hat das
durchgehende Knacken bei Wiedergabe *nicht* behoben - an echter Hardware
mit dem Fix aktiv knackte es weiterhin. `vcgencmd get_throttled` zeigte
`0x0` (keine Unterspannung/Drosselung), `top` zeigte im knackenden Zustand
noch 62.5% CPU im Leerlauf (Load Average 0.52) und `dmesg` keinerlei
ALSA-/I2S-Fehler - die CPU war also im klassischen Sinn nie wirklich
ausgelastet, der Nice-Unterschied konnte also gar nicht viel bewirken.
Trotzdem bleibt die Priorisierung sinnvoll (kostet nichts, kann in anderen
Situationen helfen) und wurde nicht wieder zurückgenommen.

**Aktuelle, noch nicht an echter Hardware verifizierte Vermutung:** nicht
die *Menge* an CPU-Last war das Problem, sondern *kontinuierliches*
Repaint/Compositing im Kiosk selbst, das auf dem komplett softwaregerenderten
Chromium immer wieder kurze, aber regelmäßige Lastspitzen erzeugt haben
könnte - genug, um `mpv`s Audio-Thread gelegentlich einen Scheduling-Slot
zu kosten, ohne dass das in einer `top`-Momentaufnahme auffällt. Zwei
Dauerschleifen in der Jetzt-läuft-Seite kamen dafür in Frage und wurden
entfernt:

- Der Titel-Marquee-Effekt (langer Titel läuft als Laufschrift durch)
  nutzte eine CSS-`@keyframes`-Animation mit
  `animation-iteration-count: infinite`, die lief, solange ein langer Titel
  angezeigt wurde - nicht nur kurz beim Wechsel. Ersetzt durch einfaches
  Abschneiden mit "…" (`text-overflow: ellipsis`), das nur einmal beim
  Rendern kostet.
- Die VU-Meter-Balkenanzeige (rein dekorativ) randomisierte per
  `setInterval` alle 450ms erneut die Höhe von 5 Balken, samt CSS-
  `transition`, für die komplette Dauer der Wiedergabe. Ersetzt durch eine
  einmalige Randomisierung beim Start der Wiedergabe.

Diese beiden Änderungen sind Stand jetzt **noch nicht auf echter Hardware
getestet** - sie beheben nichts nachweislich, sind aber die nächsten
plausiblen Kandidaten, nachdem `config.txt`, Kernel/ALSA, Stromversorgung
und CPU-Auslastung alle bereits sauber geprüft wurden.
