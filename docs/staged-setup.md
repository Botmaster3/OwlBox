# Gestaffelte Inbetriebnahme (Sound → Display → RFID → Taster/Encoder)

Diese Anleitung beschreibt den empfohlenen Weg, eine OwlBox **neu aufzubauen**:
nicht alle Hardware auf einmal anschließen und dann bei einem Problem raten,
woran es liegt, sondern **eine Komponente nach der anderen** verkabeln und
sofort testen. Jede Stufe hat ihr eigenes, kleines Testwerkzeug - keine der
späteren Komponenten muss schon angeschlossen sein, um eine frühere zu testen.

**Wer stattdessen schon komplett verkabelte Standardhardware hat und keine
Rückkehr zur Konsole zwischen den Schritten will:** `sudo
./scripts/autoinstall.sh` führt genau diesen ganzen Ablauf inklusive
Neustart-Wiederaufnahme und Ersteinrichtung des Verwaltungs-Zugangs
vollautomatisch durch, ganz ohne die einzelnen Testwerkzeuge/-pausen unten -
siehe README.md, Abschnitt "Vollautomatisch, ganz ohne Rückkehr zur
Konsole". Diese Datei hier bleibt der empfohlene Weg für den *ersten*
Aufbau einer neuen Box, wo genau die Testwerkzeuge Gold wert sind, um ein
Verkabelungsproblem sofort einer einzelnen Komponente zuzuordnen.

## Warum nicht alles auf einmal

Ein Problem, das erst auffällt, wenn RFID, Display, Taster und Sound alle
gleichzeitig laufen, lässt sich kaum eingrenzen: jede der vier Komponenten
kommt als Ursache infrage, und ein Fehler in einer kann durch eine andere
verdeckt oder verstärkt werden. Getrennt nacheinander in Betrieb genommen,
benennt die erste Stufe, bei der etwas nicht passt, die Ursache direkt.

## Zwei Werkzeuge pro Stufe

Jede der vier Stufen hat zwei getrennte Schritte:

1. **`sudo ./scripts/install.sh <stufe>`** (bzw. später `sudo owlbox-install
   <stufe>`) - installiert nur die Pakete/`config.txt`-Zeilen, die genau
   diese eine Stufe braucht. Komplett unabhängig von den anderen Stufen:
   lässt sich **in jeder Reihenfolge, beliebig oft, jederzeit erneut**
   ausführen, ohne dass eine schon installierte Stufe dadurch verändert oder
   zurückgesetzt wird. Ändert `config.txt`/`cmdline.txt`, startet aber
   **nie** einen Dienst.
2. **`sudo owlbox-stage <stufe>`** - schaltet die Hardware in `config.yaml`
   scharf, startet/testet sie. Das ist der Teil aus dem vorherigen Abschnitt
   dieser Datei.

Ohne Stufenangabe (`sudo ./scripts/install.sh` bzw. `sudo owlbox-install`)
laufen alle vier OS-Vorbereitungen auf einmal durch - die klassische
Ein-Kommando-Installation, für alle, die nicht schrittweise vorgehen wollen.

## Ablauf

**1. Nur der HiFiBerry Amp2 ist angeschlossen** (noch kein Display, kein
RC522, keine Taster/Encoder). Frisches Raspberry Pi OS Lite (64-bit)
aufspielen, dann:

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/Botmaster3/OwlBox owlbox
cd owlbox
sudo ./scripts/install.sh sound
```

Ändert `config.txt`, startet danach automatisch neu (Basis-Systempakete,
Systembenutzer, Python-venv, App-Code laufen dabei immer mit, unabhängig von
der angegebenen Stufe - das ist die gemeinsame Grundlage aller vier Stufen).

**Nach dem Neustart** denselben Befehl einmal erneut ausführen:

```bash
sudo owlbox-install sound
```

Jetzt ist die HiFiBerry-Soundkarte aktiv. `owlbox.service` wird dabei
**bewusst nicht gestartet** - das übernimmt erst der zweite Schritt:

```bash
sudo owlbox-stage sound
```

Das prüft Soundkarte und Mixer automatisch und zeigt zwei Testbefehle
(Testton bzw. eine Datei, falls schon eine hochgeladen ist). 1-2 Minuten
hören.

**2. Display anschließen** (DSI-Kabel + 4 Stromjumper, siehe
[docs/hardware.md](hardware.md)), dann:

```bash
sudo owlbox-install display   # Pakete + config.txt/cmdline.txt fuer das Display
sudo owlbox-stage display     # scharf schalten + testen
```

`owlbox-install display` ändert wieder `config.txt`/`cmdline.txt` (löst also
noch einen Neustart aus) - danach beide Befehle wie oben, erst `install`,
nach dem Neustart nochmal `install`, dann `stage`. Der Bildschirm sollte die
Now-Playing-Anzeige zeigen. Helligkeit einmal verstellen (Regler in den
Einstellungen im Web-UI) - ändert sich der Ton dabei, ist die Backlight-PWM
die Ursache. Danach nochmal kurz hören (Testbefehl wird wieder angezeigt).

**3. RC522-RFID-Leser anschließen** (Hardware-SPI0, siehe
[docs/hardware.md](hardware.md)), dann:

```bash
sudo owlbox-install rfid   # aktiviert SPI0
```

Genau wie bei "display" startet dieser Befehl danach automatisch neu - beim
allerersten Aktivieren von SPI0 ist das nicht optional: `raspi-config nonint
do_spi 0` schaltet SPI0 sonst nur per Live-Overlay ein, ohne echten Neustart,
und das kann an echter Hardware bestätigt den Audiotreiber in denselben
kaputten Zustand versetzen wie ein Absturz-Loop (digital sieht alles
unauffällig aus - Mixer korrekt, `speaker-test` läuft fehlerfrei durch -, es
kommt aber trotzdem kein Ton, bis einmal sauber neu gestartet wurde). Nach dem
Neustart denselben Befehl einmal erneut ausführen, dann testen:

```bash
sudo owlbox-install rfid   # nach dem Neustart erneut - jetzt ohne weiteren Reboot
sudo owlbox-stage rfid     # startet ein eigenstaendiges Scan-Testwerkzeug
```

`owlbox-stage rfid` stoppt kurz `owlbox.service` (damit App und Testwerkzeug
sich nicht um dieselben GPIOs streiten) und startet das Scan-Werkzeug - kein
Browser nötig, jeder erkannte Chip erscheint direkt im Terminal. Strg+C zum
Beenden, danach läuft alles automatisch wieder normal.

**4. Taster und beide Dreh-Encoder anschließen** (siehe
[docs/hardware.md](hardware.md)), dann:

```bash
sudo owlbox-install controls   # nichts zu installieren, gpiozero ist schon Teil der Basis
sudo owlbox-stage controls     # startet ein eigenstaendiges Tasten-Testwerkzeug
```

Genauso wie bei RFID: ein Testwerkzeug zeigt jeden Tastendruck/jede
Drehung direkt im Terminal. Strg+C zum Beenden - das ist gleichzeitig die
letzte Stufe, danach läuft die Box im vollständigen Normalbetrieb, und sowohl
`owlbox.service` als auch `owlbox-kiosk.service` werden dauerhaft aktiviert
(starten ab jetzt auch nach einem Neustart automatisch).

`sudo owlbox-stage status` zeigt jederzeit den aktuellen Stand, ohne etwas
zu verändern.

## Egal wie oft, egal wann, egal in welcher Reihenfolge

`sudo ./scripts/install.sh <stufe>` schreibt jede Stufe in einen eigenen,
klar markierten Abschnitt von `config.txt` (`# --- OwlBox:<stufe> begin/end
---`) und lässt jeden anderen Abschnitt unangetastet. Erneutes Ausführen
ersetzt nur den eigenen Abschnitt an derselben Stelle in der Datei - egal ob
das die erste oder die zehnte Ausführung ist, egal ob andere Stufen davor,
danach oder nie liefen. Getestet: alle vier Stufen zehnmal in wechselnder
Reihenfolge durchlaufen lassen konvergiert auf eine feste, duplikatfreie
`config.txt` - kein Wildwuchs an doppelten Zeilen oder Leerzeilen, egal wie
oft oder in welcher Kombination man es laufen lässt.

## Boot-Fortschrittsbalken (Plymouth) statt roher Boot-Textausgabe

Ab der ersten Stufe ("sound", weil das Teil von BASE ist, das jede Stufe
mitinstalliert) richtet `owlbox-install` einen eigenen, minimalen
Plymouth-Splash ein: "OwlBox" plus ein schmaler Fortschrittsbalken in den
Farben des App-Standard-Themes (`owlbox/themes.py`), statt der rohen
Kernel-/systemd-Textmeldungen, die vorher beim Hochfahren durchliefen.

Genau ein Balken für die gesamte Wartezeit, nicht zwei: der Splash bleibt
bewusst so lange stehen, bis die OwlBox-App selbst tatsächlich antwortet -
nicht nur, bis systemd den allgemeinen Bootvorgang für "fertig" hält (das
wäre deutlich früher, da `owlbox.service` als `Type=simple`-Dienst schon als
"gestartet" gilt, sobald der Prozess läuft, nicht erst wenn Flask/DB/RFID
intern wirklich bereit sind). Deshalb installiert `owlbox-install` das
mitgelieferte `plymouth-quit(-wait).service` als maskiert, und
`systemd/owlbox-kiosk.service` ruft stattdessen selbst, über
`scripts/kiosk-boot-wait.sh` als `ExecStartPre`, `plymouth quit` erst dann
auf, wenn `/api/state` tatsächlich antwortet (oder nach ~60s ohnehin, damit
der Bildschirm nicht für immer hängen bleibt) - erst danach startet X/
Chromium überhaupt. Der Kiosk selbst zeigt deshalb keine eigene
Ladeseite mehr, sondern öffnet direkt die echte Oberfläche.

**Nicht an echter Hardware verifiziert** - anders als der Rest dieses
Dokuments. Falls es nach der Installation nicht sauber aussieht (Balken
hängt fest, springt nicht mit, oder der Bildschirm bleibt schwarz länger
als erwartet), zurückrollen mit:

```bash
sudo plymouth-set-default-theme -R pix   # oder: -l zeigt alle installierten Themes
sudo sed -i -E 's/ ?quiet splash plymouth\.ignore-serial-consoles//' /boot/firmware/cmdline.txt
sudo reboot
```

(`pix` ist Debian/Raspberry-Pi-OS-Standardtheme, falls installiert -
alternativ tut es auch `plymouth-set-default-theme text` oder komplett
`apt-get remove plymouth`.) Bitte kurz Rückmeldung geben, wie es aussieht -
das ist der einzige Teil dieser Sitzung, der noch keine echte
Hardware-Bestätigung hat.

## Warum die Hörprobe ab Stufe 2 den Dienst kurz anhält

Ab "display" läuft `owlbox.service` durchgehend (davor, bei "sound", ist es
bewusst aus). Sein `mpv`-Prozess hält die Soundkarte offen, solange er lebt
(`--idle=yes`) - ein zweiter Prozess wie `speaker-test`, der versucht,
dieselbe Karte gleichzeitig zu öffnen, scheitert dann mit `Device or
resource busy` (bestätigt an echter Hardware; derselbe Grund, aus dem laut
Code-Kommentar in `owlbox/feedback.py` auch ein Hinweiston mal ausbleiben
kann, wenn er genau mit `mpv` kollidiert). Deshalb hält `owlbox-stage` den
Dienst für die Hörprobe ab Stufe 2 selbst kurz an, testet, und startet ihn
danach automatisch wieder - kein manueller Eingriff nötig, aber wichtig zu
wissen: **"Device or resource busy" bei eigenen manuellen `speaker-test`-
Versuchen ist kein Fehler**, sondern bedeutet nur, dass `owlbox.service`
gerade läuft. Erst `sudo systemctl stop owlbox` nicht vergessen, wenn man
von Hand testen will, ohne `owlbox-stage` zu benutzen.

## Wenn eine Stufe nicht sauber ist

### Kein Ton bei "sound"

`sudo owlbox-stage sound` prüft automatisch:

1. **Keine HiFiBerry-Karte in `aplay -l`** → `config.txt` stimmt nicht.
   Prüfen: `dtoverlay=hifiberry-dacplus` vorhanden, `dtparam=audio=on`
   auskommentiert, `dtoverlay=vc4-kms-v3d` mit `,noaudio` - siehe
   [docs/hardware.md](hardware.md).
2. **Mixer stumm/0%** → wird direkt erkannt und der Befehl zum Beheben
   angezeigt (`amixer sset Digital 80% unmute`). Das ist keine
   Hardware-Ursache, sondern ein Lautstärke-Zustand, der von einem
   vorherigen Lauf übrig geblieben sein kann.
3. Sitzt beides richtig, aber es kommt trotzdem nichts: Lautsprecherklemmen
   und Stromversorgung des Amp2 nachziehen (er braucht eine eigene
   Spannungsversorgung, nicht nur den Pi-USB-C-Stecker), testweise ein
   anderes Netzteil versuchen.

### Es knistert/knackt (bei jeder Stufe möglich)

Ein knisterndes Signal kann mehrere, sich gegenseitig verdeckende Ursachen
haben:

| Ursache | Klingt wie | Zeigt sich in |
|---|---|---|
| Falsche `config.txt` (zweite Soundkarte aktiv) | verzerrt, komplett falsch | `aplay -l` |
| Unterspannung / Netzteil zu schwach | Aussetzer, Neustarts | `vcgencmd get_throttled` |
| Buffer-Underrun (CPU/Scheduling) | Stottern, Aussetzer | `dmesg`, ALSA-XRUN-Meldungen |
| Elektrische Einkopplung (GPIO/PWM/Schaltlast) | **Knistern wie ein Wackelkontakt** | **nirgends** - keine Logmeldung |

Der letzte Fall erzeugt keine Fehlermeldung - CPU im Leerlauf, `dmesg`
sauber, ALSA meldet nichts, und trotzdem knistert es. Das ist genau der
Grund für die gestaffelte Inbetriebnahme: die Stufe, bei der es anfängt,
benennt die Komponente.

- **Knistert es schon bei "sound"**: liegt nicht an der Software, sondern an
  Hardware/Verkabelung/Netzteil/`config.txt`.
- **Erst ab "display"**: an echter Hardware bestätigt, dass die Helligkeit
  bei diesem Display über ein Sysfs-Backlight-Gerät läuft
  (`/sys/class/backlight/.../brightness`, siehe docs/hardware.md), **nicht**
  über GPIO13-PWM wie beim früheren Display - `gpio.backlight_pin` ist für
  dieses Display gar nicht mehr verkabelt und kommt als Störquelle damit
  nicht mehr in Frage. Gegenprobe trotzdem sinnvoll: Helligkeit auf 100%
  stellen - bleibt die Störung dabei unverändert bestehen, liegt es an
  etwas anderem, das erst mit dem Display dazukam (z.B. der I2C-Bus, über
  den sowohl Touch-Controller als auch HiFiBerry-Amp-Steuerung laufen).
- **Erst ab "rfid"**: der RC522 hängt an Hardware-SPI0 (siehe
  `owlbox/rfid/mfrc522_reader.py`). Falls hier trotzdem Störungen auftreten,
  `rfid.poll_interval` in `config.yaml` erhöhen (z.B. `0.5`) als erste
  Gegenprobe.
- **Erst ab "controls"**: Masseführung der Taster-/Encoder-Verkabelung
  prüfen, insbesondere gemeinsame Masse mit der Audioplatine vermeiden.

## Für eine bereits laufende Box

`sudo owlbox-stage` lässt sich jederzeit auch später noch benutzen, um ein
neu auftretendes Problem einzugrenzen - dann einfach mit `sudo owlbox-stage
sound` anfangen und nach oben durcharbeiten, unabhängig davon, ob die
Hardware schon verkabelt ist (sie bleibt es ja). Ein erneutes
`sudo owlbox-install` (z.B. nach einem `git pull`) lässt eine bereits
abgeschlossene Konfiguration unangetastet.
