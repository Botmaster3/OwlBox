# OwlBox 🦉

Eine Toniebox-ähnliche Musik-/Hörspielbox für den Raspberry Pi: RFID-Chip
auflegen, Geschichte/Musik spielt automatisch weiter genau dort, wo sie beim
letzten Mal aufgehört hat. Inhalte werden bequem über eine Web-Oberfläche auf
den Pi geladen und einem Chip zugewiesen.

## Funktionen

- **RFID-gesteuerte Wiedergabe**: Chip auflegen → zugehörige Playlist startet
  (mit gemerkter Position). Chip abnehmen unterbricht die Wiedergabe nicht -
  die Geschichte läuft weiter, nur die Position wird laufend gespeichert. Erst
  ein anderer Chip (oder ein Funktions-Chip/Taster für Pause) wechselt bzw.
  stoppt die Wiedergabe; denselben Chip wieder aufzulegen ist ein No-Op.
- **Livestream-Chips**: ein Chip kann statt einer lokalen Playlist auch direkt
  eine Audio-Livestream-URL (Internetradio o.ä.) abspielen - verbindet beim
  Auflegen immer live, ohne gespeicherte Position und ohne Vor-/Zurückspulen.
- **Funktions-Chips**: eigene Chips, die statt einer Geschichte eine Aktion
  auslösen - Play/Pause, Weiter/Zurück, Lauter/Leiser, WLAN an/aus, Shuffle
  an/aus, Wiederholung Ordner an/aus, Wiederholung Track an/aus,
  Einschlaf-Timer starten (15/30/45/60 Min., blendet die Lautstärke in den
  letzten 60s sanft aus statt hart abzuschneiden) oder abbrechen,
  Spiele-Menü an/aus (siehe unten), Pi neu starten/herunterfahren. Praktisch
  als "Bedienkarten" ohne Taster anfassen zu müssen. Die
  Shuffle-/Wiederholungs-/Spiele-Menü-Chips wirken auch nachdem der jeweils
  auslösende Chip schon wieder abgenommen wurde, und schalten beim ersten
  Auflegen ein und beim erneuten Auflegen wieder aus.
- **Akustisches Feedback**: kurzer, unterschiedlicher Ton für Chip erkannt /
  unbekannter Chip / Funktions-Chip sowie beim Hochfahren und beim
  Herunterfahren/Neustart - läuft über `aplay` parallel zur laufenden
  Geschichte, unterbricht sie also nicht. Spielt immer bei einer festen,
  leisen Lautstärke (Standard 15% der maximalen Lautstärke), egal wie laut
  die Geschichte gerade eingestellt ist. In Einstellungen abschaltbar.
- **7" Touch Display** (offizielles Raspberry-Pi-Display, DSI): Cover,
  Geschichte, aktueller Kapitel-/Track-Titel, verbleibende Zeit im Track,
  Track-Liste der Geschichte mit hervorgehobenem aktuellen Titel, Lautstärke,
  WLAN-Empfang - Bedienung läuft primär über Taster/Encoder/Funktions-Chips
  (siehe docs/hardware.md); die Touch-Hardware wird von der Oberfläche einzig
  im Spiele-Menü ausgewertet (siehe unten) - überall sonst bleibt der Kiosk
  reines Anzeige-Display. Helligkeit ausschließlich manuell regelbar (Regler
  unter Einstellungen/Home oder ein zweiter Dreh-Encoder am Gerät) - kein
  automatisches Dimmen; jede Änderung blendet den neuen Wert kurz auf dem
  Display ein, **die eigentliche Backlight-Steuerung ist auf dieser Hardware
  aber noch nicht angeschlossen** (das Display regelt seine Helligkeit über
  eine Linux-Sysfs-Schnittstelle statt über GPIO/PWM, siehe docs/hardware.md).
- **Spiele-Menü**: per Funktions-Chip "Spiele-Menü an/aus" freigeschaltete
  Bildschirmansicht - die einzige Stelle im ganzen Kiosk, an der Touch
  tatsächlich etwas bewirkt. Erstes Auflegen zeigt ein Menü mit sechs
  antippbaren Mini-Spielen; erneutes Auflegen desselben Chips verlässt das
  Menü komplett und zeigt wieder die normale Now-Playing-Anzeige, egal in
  welchem Mini-Spiel man gerade war. Ein eigener „← Menü“-Knopf springt
  jederzeit vom laufenden Mini-Spiel zurück zur Auswahl, ohne den Chip
  abnehmen zu müssen. Läuft unabhängig von der Wiedergabe - eine Geschichte
  spielt im Hintergrund weiter. **Touch-Bedienung noch nicht an echter
  Hardware verifiziert** (siehe docs/hardware.md). Die sechs Spiele:
  - **Memory** - Bildpaare finden (Karten antippen zum Umdrehen). Vor jeder
    Runde eine Schwierigkeitsauswahl (Leicht/Mittel/Schwer = 4/8/12
    Bildpaare), danach zufällig aus dem Bilderpool gezogene Paare, mit
    Zug-Zähler und Gewinn-Anzeige samt "Nochmal spielen" und "Schwierigkeit
    ändern".
  - **Simon Sagt** - eine wachsende Farb-/Ton-Sequenz nachtippen (4 große
    Farbfelder); ein Fehler beendet die Runde und zeigt das erreichte Level.
    Kein Bilder-Upload nötig.
  - **Schiebe-Puzzle** - ein zufälliges Bild aus demselben Bilderpool wie
    Memory wird in Teile zerschnitten (3×3/4×4/5×5 je nach Schwierigkeit);
    zwei Teile antippen vertauscht sie, bis das Bild wieder stimmt.
  - **Reaktion** - ein Whack-a-Mole-artiges Tippspiel: eine Eule taucht kurz
    an zufälligen Stellen in einem 3×3-Raster auf, antippen bevor sie
    verschwindet. Die Schwierigkeit bestimmt nur das Tempo.
  - **Tier-Sound-Quiz** - ein Klang spielt ab, aus mehreren Bildern das
    passende antippen (z.B. Kuh-Bild zu Muh-Ton). Feste Bild+Ton-Paare, frei
    unter Einstellungen → Spiel anlegbar (inkl. optionaler, nur intern
    sichtbarer Bezeichnung).
  - **Sound-Memory** - wie Memory, aber es werden Klangpaare statt Bildpaare
    per Gehör gesucht: Karte antippen spielt einen kurzen Klang ab, die
    zweite Karte mit demselben Klang finden.

  Die Bild- und Klang-Pools lassen sich alle frei unter Einstellungen →
  Spiel hochladen/löschen (JPG/PNG/WebP bzw. gängige Audioformate); mit
  weniger Inhalten als eine gewählte Schwierigkeit verlangt wird die jeweilige
  Runde einfach entsprechend kleiner statt einen Fehler zu zeigen.
- **Physische Bedienung**: zwei Taster (vor/zurück - kurz drücken springt zum
  nächsten/vorherigen Track, gedrückt halten spult stattdessen im aktuellen
  Track vor/zurück) + Dreh-Encoder (drehen = Lautstärke, drücken = Play/Pause,
  lang drücken = herunterfahren) + zweiter Dreh-Encoder (drehen = Helligkeit).
  Lautstärke ganz runter drehen (0%) pausiert automatisch, wieder hochdrehen
  setzt die Wiedergabe fort - egal ob per Encoder oder Web-Regler.
- **Automatischer Ruhemodus (schlafende Eule)**: bleibt eine Geschichte eine
  konfigurierbare Zeit lang pausiert - egal ob per Play/Pause-Taste/-Chip oder
  weil die Lautstärke auf 0 gedreht wurde - zeigt das Display eine schlafende
  Eule statt der Now-Playing-Ansicht. Aufwecken (Track läuft exakt an der
  Pausenstelle weiter): Lautstärke erhöhen, Play/Pause drücken oder einen
  RFID-Chip auflegen. Dauer unter Einstellungen konfigurierbar, 0 schaltet es ab.
- **Weckmodus**: startet täglich zur eingestellten Uhrzeit automatisch eine
  frei wählbare Geschichte - die Lautstärke steigt dabei über eine
  einstellbare Einblendzeit sanft von 0 auf die eingestellte Lautstärke, statt
  abrupt in voller Lautstärke loszulegen. Greift nur, wenn gerade nichts läuft
  (z.B. über Nacht pausiert oder noch kein Chip aufgelegt) - eine bereits
  laufende Geschichte wird dadurch nie unterbrochen. Einmal pro Tag, unter
  Einstellungen → Audio konfigurierbar (an/aus, Uhrzeit, Geschichte,
  Einblendzeit).
- **Web-Verwaltung** (`/admin`, mit Benutzername+Passwort **oder** einem
  hinterlegten RFID-Chip geschützt, sechs Unterseiten):
  - **Home** - "Jetzt läuft"-Anzeige (groß, wie auf dem Display, inkl. WLAN-Empfang) als erste
    Seite nach dem Login, zusätzlich als Fernbedienung nutzbar: Zurück/Play-Pause/Weiter sowie
    Shuffle/Wiederholung für die gerade laufende Geschichte direkt bedienbar (wirkt sofort auf die
    Wiedergabe, kein Umweg über die Bibliothek nötig), dazu Lautstärke- und Helligkeits-Regler,
    ohne den echten Taster/Encoder anzufassen.
    Fortschrittsanzeige zeigt links die bereits gespielte und rechts die verbleibende Zeit,
    ein Klick auf die Leiste spult direkt zur angeklickten Stelle im Track.
  - **Bibliothek** - Geschichten verwalten: Chip zuweisen/entfernen, Shuffle, Wiederholung (Aus/ganzen Ordner in
    Dauerschleife/nur den aktuellen Track wiederholen - ohne Wiederholung geht die Geschichte nach dem letzten
    Track einfach aus), Track-Reihenfolge, löschen;
    Hörstatistik (Wiedergaben insgesamt, Gesamt-Hördauer, Meistgehört-Liste, pro Geschichte/Ordner/Livestream
    wie oft und wie lange gehört sowie zuletzt gespielt). Jeder Titel hat eine Checkbox - eine oder
    mehrere ausgewählte (auch über mehrere Geschichten hinweg gemischt) lassen sich über eine
    einblendende Leiste am unteren Rand direkt zu einer neuen Playlist zusammenfassen, ohne den
    Umweg über Hinzufügen.
  - **Hinzufügen** - einzelne Dateien, einen ganzen Ordner oder eine Livestream-URL (Internetradio o.ä.)
    hochladen/anlegen, Cover/Titel wird aus dem Ordner erkannt. Vierte Option „Playlist aus
    Bibliothek“: eine neue Geschichte aus bereits hochgeladenen Titeln anderer Geschichten
    zusammenstellen (durchsuchbar, eigene Reihenfolge per ▲/▼) - ohne erneutes Hochladen und ohne
    doppelten Speicherbedarf (Hardlinks auf dieselben Dateien), danach ganz normal wie jede andere
    Geschichte einem Chip zuweisbar. Wird die Quell-Geschichte (oder einzeln einer ihrer Titel)
    später gelöscht, verschwindet der jeweilige Titel automatisch auch aus jeder Playlist, die ihn
    enthält - der Rest der Playlist bleibt bestehen.
  - **RFID-Tags** - Eltern-Chips anlegen (z.B. "Vater"/"Mutter", dienen als Login-Chip),
    Funktions-Chips anlegen, Übersicht aller Story-Chips.
  - **Einstellungen** - Zugangsdaten ändern; Design (4 Standard- plus 4 Sonderedition-Themes und ein
    frei einstellbares eigenes Design - Weihnachten mit einem Adventskranz, dessen Kerzen automatisch
    je nach aktuellem Advent nacheinander angezündet werden (plus Geschenke am 24.12.), Ostern mit
    einem Osterkörbchen samt Gras und Eiern, Winter (Sonderedition) mit dunklem Eisblau, Silvester mit
    einem Feuerwerk am Himmel - alles als Standbild statt laufender Animation, um die Kiosk-Anzeige
    nicht unnötig zu belasten; das Standard-Thema "Winter" bekommt dafür ein statisches Schneeflocken-Muster.
    Für Kiosk-Anzeige und Web-UI, inkl. unterschiedlicher Balken-Optik; drei der Standard-Themes
    stehen zusätzlich für die kalendarischen Jahreszeiten (Frühling/Sommer/Herbst), sodass zusammen
    mit den Sonderedition-Fenstern (1.-26.12. Weihnachten, 31.12.-1.1. Silvester, 27.12.-19.3. Winter,
    9 Tage vor bis 1 Tag nach Ostern) das ganze Jahr automatisch abgedeckt ist - jedes einzelne Theme
    lässt sich für sich abschalten, statt nur alles auf einmal; das eigene Design erlaubt jede Farbe
    (Hintergrund, Fläche, Akzent, Text, Rahmen u.a.) frei per Farbwähler einzustellen); Lautstärke
    (aktuelle Lautstärke, Maximum, Schrittweite);
    Akustisches Feedback (Töne beim Scannen/Hoch-/Herunterfahren an/aus); Helligkeit (aktuelle Helligkeit, sowie ein
    einstellbarer Minimal-/Maximalwert, der den Schieberegler hier und den Helligkeits-Encoder am
    Gerät begrenzt); Automatischer Ruhemodus (Minuten bis zur schlafenden Eule nach dem Pausieren,
    0 = aus); Einschlaf-Timer (Schnellauswahl 15/30/45/60 Min. oder eigene Dauer, pausiert
    automatisch nach Ablauf, mit sanftem Ausblenden); Weckmodus (an/aus, tägliche Weckzeit,
    Geschichte, Einblendzeit der Lautstärke, siehe oben); Spiel (Bild- und Klang-Pools fürs
    Spiele-Menü hochladen/löschen, siehe oben); WLAN (Status, an/aus, nach Netzwerken suchen
    und verbinden); Pi neu starten/herunterfahren.
  - **Info** - Systeminfos: Hardware-Modell, Betriebssystem, Laufzeit, CPU-Temperatur,
    Speicher-/RAM-Belegung, Bibliotheks-Statistik, OwlBox-Version; Wochenrückblick (Hördauer und
    Lieblingsgeschichte der letzten 7 Tage); Bibliotheks-Backup als ZIP-Download; Software-Update
    per Klick (`git pull` + Neustart des Diensts).

  Beim ersten Besuch führt ein Einrichtungsassistent durchs Anlegen des
  Admin-Kontos. Die Now-Playing-Anzeige (`/`) für den Touchscreen selbst
  bleibt bewusst ohne Login, da das Display keine Tastatur hat.
- **Fallback-Hotspot bei WLAN-Ausfall**: ist WLAN an, aber eine Weile mit
  keinem Netzwerk verbunden, macht der Pi automatisch seinen eigenen
  Access Point auf (SSID/Passwort werden auf Kiosk-Display und im
  Admin-Bereich angezeigt) - damit einwählen und die echten WLAN-Zugangsdaten
  unter Einstellungen neu setzen, ganz ohne Monitor/Tastatur am Pi (siehe
  docs/hardware.md).
- **Eltern-Modus mit QR-Login**: legt ein Elternteil seinen Chip auf, zeigt das
  Display statt der Now-Playing-Anzeige einen QR-Code zur Login-Seite - per
  Handy scannen und einloggen, ohne dass Kinder je einen QR-Code oder eine
  Login-Seite zu sehen bekommen. Story- und Funktions-Chips zeigen davon
  nichts an.
- **AirPlay (optional)**: `sudo ./scripts/install.sh airplay` installiert
  [shairport-sync](https://github.com/mikebrady/shairport-sync) als eigenen
  Dienst, damit ein iPhone/iPad/Mac eigene Musik über denselben HiFiBerry-
  Lautsprecher abspielen kann, ganz ohne Chip aufzulegen. Eine laufende
  Geschichte wird für die Dauer der AirPlay-Wiedergabe automatisch pausiert
  und danach wieder fortgesetzt (nie umgekehrt gestartet); auf dem
  Kiosk-Display erscheint währenddessen unten rechts ein „📡 AirPlay“-
  Abzeichen. Bewusst kein Kernbestandteil der Installation - siehe
  docs/hardware.md.
- **Simulationsmodus**: läuft ohne echte Hardware (RFID/GPIO/mpv) für
  Entwicklung und Tests - die Admin-UI bekommt dann einen "Chip simulieren"-
  Knopf.

## Architektur

Ein einziger Python-Prozess (`owlbox.main`) vereint:

- `owlbox/engine.py` - Zustandsmaschine: reagiert auf RFID-Scans, Taster/
  Encoder, merkt sich die Wiedergabeposition pro Chip in SQLite.
- `owlbox/player.py` - steuert `mpv` über dessen JSON-IPC-Socket;
  Lautstärke läuft über den ALSA-Hardware-Mixer (`amixer`), nicht über
  mpv-Software-Volume, weil der HiFiBerry Hardware-Lautstärke kann.
- `owlbox/rfid/` - RC522-Anbindung (SPI) mit austauschbarem
  Simulations-Backend.
- `owlbox/controls/` - Taster/Encoder über `gpiozero`.
- `owlbox/web/` - Flask-App: `/` (Now-Playing-Anzeige fürs Display, per
  Polling aktualisiert), `/admin` (Bibliotheksverwaltung), `/api/*` (REST).

Das Now-Playing-Display läuft als ganz normale Webseite, die im Kiosk-Modus
in Chromium auf dem DSI-Touch-Display angezeigt wird (`scripts/kiosk.sh`) -
kein separates GUI-Toolkit nötig, funktioniert offline und ist deutlich
genügsamer als z.B. Kivy oder Qt. Das Display braucht eine eigene
`dtoverlay=`-Zeile in `config.txt` (kein separater Treiber-Installer nötig,
aber die Overlay-Zeile selbst ist Pflicht - siehe docs/hardware.md) - Touch
ist am Board vorhanden, wird von der Oberfläche aktuell aber noch nicht
ausgewertet.

## Schnellstart (Entwicklung, ohne Pi-Hardware)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp config/config.example.yaml config/config.yaml
# in config.yaml: simulate: true setzen

pytest

python -m owlbox.main
# -> http://localhost:5000/       Now-Playing-Anzeige
# -> http://localhost:5000/admin  Verwaltung (inkl. "Chip simulieren")
```

Im Simulationsmodus wird RFID/GPIO/mpv durch Software-Stubs ersetzt, siehe
`owlbox/rfid/simulated.py` und `owlbox/player.py` (`StubPlayer`).

## Installation auf dem Raspberry Pi

Empfohlenes Basis-Image: **Raspberry Pi OS Lite, 64-bit** - Bookworm mit dem
modernen KMS-Grafiktreiber (Standard, bleibt aktiv - anders als bei dem
früher hier verbauten 3.5"-SPI-Display, das den alten Grafiktreiber
brauchte), aber bewusst *ohne* Desktop-Umgebung, da der Kiosk-Autostart X
nur für Chromium selbst startet (kein lightdm/LXDE, das beim Boot nur
unnötig Zeit kosten würde).

Für die Standardhardware (Pi 5, HiFiBerry Amp2 über eigene Adapter-Platine
statt direkt gestapelt, DSI-Touch-Display, RC522, Taster/Encoder auf den
Standard-Pins - siehe
[docs/hardware.md](docs/hardware.md)) läuft die Einrichtung **gestaffelt**,
und zwar nicht nur beim erstmaligen Testen, sondern als das Installations-
Skript selbst: `scripts/install.sh` kennt vier unabhängige Stufen (`sound`,
`display`, `rfid`, `controls`), die jede für sich nur die Pakete/
`config.txt`-Zeilen installieren, die genau diese eine Hardware braucht -
**beliebig oft, in beliebiger Reihenfolge und jederzeit erneut ausführbar**,
ohne dass eine schon eingerichtete Stufe dabei angetastet wird. Erst
Sound anschließen und einrichten, dann Display, dann RFID, dann Taster/
Encoder - jede Stufe sofort mit einem eigenen Testwerkzeug überprüfbar,
statt alles auf einmal anzuschließen und danach zu raten, woran ein Problem
liegt. Vollständig beschrieben in
[docs/staged-setup.md](docs/staged-setup.md); kurz zusammengefasst:

```bash
sudo apt update && sudo apt install -y git   # frisches Raspberry Pi OS Lite hat kein git vorinstalliert
git clone https://github.com/Botmaster3/OwlBox owlbox
cd owlbox
sudo ./scripts/install.sh sound
```

Installiert Systempakete (mpv, ALSA), aktiviert die HiFiBerry-Amp2-Overlays
in `config.txt` sowie ein paar Stufen-unabhängige Grundlagen, die jede Stufe
gemeinsam braucht (Systembenutzer, Python-venv, App-Code, deaktivierte
ungenutzte Dienste/Boot-Wartezeiten - siehe docs/hardware.md) - der Pi
startet am Ende von selbst neu (jede Stufe, die `config.txt`/`cmdline.txt`
ändert, tut das; `sound` und `display` tun es, `rfid` und `controls` nicht).

**Nach dem Neustart denselben Befehl erneut ausführen** (`sudo owlbox-install
sound` - ein stabiler Befehl, den der erste Durchlauf selbst anlegt,
funktioniert ab da von jedem Verzeichnis aus statt `cd owlbox && sudo
./scripts/install.sh`, was leicht danebengeht, siehe Kasten unten). Jetzt ist
die HiFiBerry-Soundkarte aktiv - `owlbox.service` wird dabei bewusst **nicht**
gestartet, das ist Aufgabe des zweiten, davon komplett getrennten Werkzeugs:

```bash
sudo owlbox-stage sound
```

Prüft Soundkarte/Mixer automatisch und zeigt Testbefehle. Ist das sauber:
Display anschließen, `sudo owlbox-install display` (+ erneut nach dem
automatischen Neustart), dann `sudo owlbox-stage display`. Danach RC522
anschließen, `sudo owlbox-install rfid`, `sudo owlbox-stage rfid` (startet
ein eigenständiges Scan-Testwerkzeug, kein Browser nötig). Zuletzt Taster/
Encoder anschließen, `sudo owlbox-install controls`, `sudo owlbox-stage
controls` (eigenes Tastendruck-Testwerkzeug) - das ist gleichzeitig die
letzte Stufe und aktiviert sowohl `owlbox.service` als auch
`owlbox-kiosk.service` dauerhaft (der Kiosk-Bildschirm startet ab jetzt auch
nach einem Neustart automatisch). Komplette Anleitung inkl. was bei jeder
Stufe schiefgehen kann: [docs/staged-setup.md](docs/staged-setup.md).

Wer nicht stufenweise vorgehen will: `sudo ./scripts/install.sh` bzw. `sudo
owlbox-install` ganz ohne Stufenname macht alle vier auf einmal - die
klassische Ein-Kommando-Installation. **Wichtig:** auch das startet/aktiviert
`owlbox.service`/`owlbox-kiosk.service` bewusst noch nicht (gleicher Grund
wie oben) - `sudo owlbox-stage sound && sudo owlbox-stage display && sudo
owlbox-stage rfid && sudo owlbox-stage controls` (bei schon komplett
verkabelter Standardhardware ohne weitere Wartezeit direkt hintereinander
ausführbar) muss auch bei der Ein-Kommando-Variante noch einmal folgen, sonst
bleibt der Kiosk nach dem nächsten Neustart schwarz.

> **Hinweis:** `cd owlbox` von *innerhalb* eines bereits ausgecheckten Repos
> landet nicht wieder im Repo-Root, sondern eine Ebene zu tief im
> gleichnamigen Python-Paket-Unterordner `owlbox/owlbox` - `./scripts/install.sh`
> meldet dann „command not found“, ohne dass das Skript selbst je startet.
> `sudo owlbox-install` vermeidet das komplett, da es unabhängig vom
> aktuellen Verzeichnis funktioniert.

Jede Stufe ist für sich beliebig oft wiederholbar (idempotent) - jeder
Schritt prüft zuerst, ob er schon erledigt ist, und jede Stufe schreibt nur
in ihren eigenen, klar markierten Abschnitt von `config.txt` (siehe
docs/staged-setup.md), ohne andere Stufen oder deren Reihenfolge
vorauszusetzen. `owlbox-stage` lässt eine bereits abgeschlossene
Hardware-Konfiguration (RFID/Taster-Encoder/Backlight) bei einem erneuten
`owlbox-install`-Lauf unangetastet. Nach der gestaffelten Einrichtung bleibt
nur noch eins wirklich manuell, weil kein Skript es übernehmen kann:
`http://<pi-ip>:5000/admin` öffnen und die Ersteinrichtung (Benutzername/
Passwort) durchlaufen - aus Sicherheitsgründen bewusst ohne automatisch
gesetztes Standardpasswort.

Abweichende Hardware (andere HiFiBerry-Variante, anderes Display) lässt sich
weiterhin ganz nach [docs/hardware.md](docs/hardware.md) von Hand einrichten -
die dort beschriebenen Schritte sind genau das, was das Skript für die
Standardhardware automatisch erledigt.

Komplett von einer leeren SD-Karte bis zur fertig eingerichteten Box (inkl.
Raspberry Pi OS flashen, `raspi-config`, Verkabelungsreihenfolge, erste
Einrichtung im Browser) - siehe **OwlBox-Installation.pdf**, mitgeliefert
unter `owlbox/web/static/docs/` bzw. herunterladbar über die Verwaltung
(Info → Dokumentation), sobald einmal ein `owlbox`-Dienst läuft.

## Bedienkonzept

| Aktion                          | Wirkung                                    |
|----------------------------------|--------------------------------------------|
| Chip auflegen (bekannt)          | Playlist lädt, Wiedergabe ab letzter Position |
| Chip auflegen (unbekannt)        | Anzeige "Unbekannter Chip", Scan wird geloggt (im Admin-UI direkt zuweisbar) |
| Chip abnehmen                    | Wiedergabe läuft weiter, Position wird laufend gespeichert |
| Taster "Zurück"                  | Neustart des Tracks, oder vorheriger Track wenn <3s gespielt |
| Taster "Weiter"                  | nächster Track                              |
| Encoder drehen                   | Lautstärke rauf/runter                      |
| Encoder drücken                  | Play/Pause                                  |
| Encoder lang drücken (4s)        | Pi sicher herunterfahren                    |
| Zweiter Encoder drehen (optional) | Helligkeit rauf/runter                      |

## Konfiguration

Alle Einstellungen (GPIO-Pins, SPI, ALSA-Device/Mixer, Ports,
Lautstärkeschritte, …) liegen in `config/config.yaml`
(Vorlage: `config/config.example.yaml`, kommentiert). Diese Datei ist
bewusst `.gitignore`t, da sie gerätespezifisch ist. Das Admin-Konto
(Benutzername/Passwort) wird separat über den Einrichtungsassistenten beim
ersten `/admin`-Besuch angelegt und liegt (als Hash) in der SQLite-Datenbank,
änderbar über `/admin/settings`.

## Inhalte hochladen

1. `/admin/add` öffnen (im lokalen Netz, z.B. `http://owlbox.local:5000/admin/add`).
2. Titel eingeben, Cover (optional) und entweder einzelne Audiodateien
   (mp3/m4a/ogg/flac/wav/opus) oder über "Ganzer Ordner" gleich einen
   kompletten Ordner auswählen - die enthaltenen Audiodateien werden
   alphabetisch sortiert übernommen, ein Cover-Bild im Ordner (z.B.
   `cover.jpg`) automatisch erkannt, der Titel aus dem Ordnernamen
   vorausgefüllt. "Anlegen" klicken.
3. Auf der Bibliotheksseite bei der neuen Geschichte auf "Chip zuweisen"
   klicken und den gewünschten RFID-Chip an den Leser halten - die
   Zuordnung passiert automatisch.
4. Fertig: Chip auflegen, Geschichte spielt.

## Tests

```bash
pytest
```

Die Tests laufen komplett im Simulationsmodus (kein echtes GPIO/RFID/mpv
nötig) und decken Datenbank-Repository, Player-Stub und die
Engine-Zustandsmaschine (Chip auflegen/abnehmen, Positionsspeicherung,
Lautstärke) ab.
