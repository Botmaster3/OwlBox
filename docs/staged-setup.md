# Gestaffelte Inbetriebnahme (Sound → Display → RFID → Taster/Encoder)

Diese Anleitung beschreibt den empfohlenen Weg, eine OwlBox **neu aufzubauen**:
nicht alle Hardware auf einmal anschließen und dann bei einem Problem raten,
woran es liegt, sondern **eine Komponente nach der anderen** verkabeln und
sofort testen. Jede Stufe hat ihr eigenes, kleines Testwerkzeug - keine der
späteren Komponenten muss schon angeschlossen sein, um eine frühere zu testen.

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

**3. RC522-RFID-Leser anschließen** (Software-SPI auf freien GPIOs, siehe
[docs/hardware.md](hardware.md)), dann:

```bash
sudo owlbox-install rfid   # aktiviert SPI, kein Neustart noetig
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
letzte Stufe, danach läuft die Box im vollständigen Normalbetrieb, und
`owlbox.service` wird dauerhaft aktiviert (startet ab jetzt auch nach einem
Neustart automatisch).

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
- **Erst ab "display"**: Backlight-PWM (GPIO 13). Gegenprobe: Helligkeit auf
  100% - bei vollem Tastverhältnis schaltet die PWM nicht mehr, die Störung
  muss verschwinden. Abhilfe: `gpio.backlight_pin: null` setzen (Dimmung
  entfällt, Display läuft auf voller Helligkeit) oder den
  Backlight-Treibertransistor mit einem RC-Glied entstören.
- **Erst ab "rfid"**: der RC522 hängt an Software-SPI (GPIO-Pins werden aus
  Python heraus einzeln umgeschaltet, siehe `owlbox/rfid/soft_spi.py`).
  `rfid.poll_interval` in `config.yaml` erhöhen (z.B. `0.5`) oder den RC522
  auf echtes Hardware-SPI (SPI0, seit dem DSI-Display frei) umverdrahten.
- **Erst ab "controls"**: Masseführung der Taster-/Encoder-Verkabelung
  prüfen, insbesondere gemeinsame Masse mit der Audioplatine vermeiden.

## Für eine bereits laufende Box

`sudo owlbox-stage` lässt sich jederzeit auch später noch benutzen, um ein
neu auftretendes Problem einzugrenzen - dann einfach mit `sudo owlbox-stage
sound` anfangen und nach oben durcharbeiten, unabhängig davon, ob die
Hardware schon verkabelt ist (sie bleibt es ja). Ein erneutes
`sudo owlbox-install` (z.B. nach einem `git pull`) lässt eine bereits
abgeschlossene Konfiguration unangetastet.
