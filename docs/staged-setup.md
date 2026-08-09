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

## Ablauf

**1. Nur der HiFiBerry Amp2 ist angeschlossen** (noch kein Display, kein
RC522, keine Taster/Encoder). Frisches Raspberry Pi OS Lite (64-bit)
aufspielen, dann:

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/Botmaster3/OwlBox owlbox
cd owlbox
sudo ./scripts/install.sh
```

Das Skript passt `config.txt` an und startet danach automatisch neu.

**Nach dem Neustart** das Skript einmal erneut ausführen:

```bash
sudo owlbox-install
```

Bei einer echten Erstinstallation erkennt es das automatisch: `config.yaml`
wird auf "nur Sound" gestellt (RFID/Taster-Encoder/Backlight aus),
`owlbox.service` wird **bewusst noch nicht gestartet** - stattdessen zeigt
die Ausgabe direkt den nächsten Befehl:

```bash
sudo owlbox-stage sound
```

Das prüft Soundkarte und Mixer automatisch und zeigt zwei Testbefehle
(Testton bzw. eine Datei, falls schon eine hochgeladen ist). 1-2 Minuten
hören.

**2. Display anschließen** (DSI-Kabel + 4 Stromjumper, siehe
[docs/hardware.md](hardware.md)), dann:

```bash
sudo owlbox-stage display
```

Der Bildschirm sollte die Now-Playing-Anzeige zeigen. Helligkeit einmal
verstellen (Regler in den Einstellungen im Web-UI) - ändert sich der Ton
dabei, ist die Backlight-PWM die Ursache. Danach nochmal kurz hören
(Testbefehl wird wieder angezeigt).

**3. RC522-RFID-Leser anschließen** (Software-SPI auf freien GPIOs, siehe
[docs/hardware.md](hardware.md)), dann:

```bash
sudo owlbox-stage rfid
```

Das stoppt kurz `owlbox.service` (damit App und Testwerkzeug sich nicht um
dieselben GPIOs streiten) und startet ein eigenständiges Scan-Werkzeug -
kein Browser nötig, jeder erkannte Chip erscheint direkt im Terminal.
Strg+C zum Beenden, danach läuft alles automatisch wieder normal.

**4. Taster und beide Dreh-Encoder anschließen** (siehe
[docs/hardware.md](hardware.md)), dann:

```bash
sudo owlbox-stage controls
```

Genauso wie bei RFID: ein Testwerkzeug zeigt jeden Tastendruck/jede
Drehung direkt im Terminal. Strg+C zum Beenden - das ist gleichzeitig die
letzte Stufe, danach läuft die Box im vollständigen Normalbetrieb, und
`owlbox.service` wird dauerhaft aktiviert (startet ab jetzt auch nach einem
Neustart automatisch).

`sudo owlbox-stage status` zeigt jederzeit den aktuellen Stand, ohne etwas
zu verändern.

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
