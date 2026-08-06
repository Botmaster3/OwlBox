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
  letzten 60s sanft aus statt hart abzuschneiden) oder abbrechen, Pi neu
  starten/herunterfahren. Praktisch als "Bedienkarten" ohne Taster anfassen zu
  müssen. Die Shuffle-/Wiederholungs-Chips wirken auf die zuletzt geladene
  Geschichte, auch nachdem deren eigener Chip schon wieder abgenommen wurde,
  und schalten beim ersten Auflegen ein und beim erneuten Auflegen wieder aus.
- **Akustisches Feedback**: kurzer, unterschiedlicher Ton für Chip erkannt /
  unbekannter Chip / Funktions-Chip sowie beim Hochfahren und beim
  Herunterfahren/Neustart - läuft über `aplay` parallel zur laufenden
  Geschichte, unterbricht sie also nicht. Spielt immer bei einer festen,
  leisen Lautstärke (Standard 15% der maximalen Lautstärke), egal wie laut
  die Geschichte gerade eingestellt ist. In Einstellungen abschaltbar.
- **3.5" SPI-Display**: reine Anzeige (Cover, Geschichte, aktueller
  Kapitel-/Track-Titel, verbleibende Zeit im Track, Track-Liste der Geschichte mit
  hervorgehobenem aktuellen Titel, Lautstärke, WLAN-Empfang) - kein Touch, Bedienung
  läuft ausschließlich über Taster/Encoder/Funktions-Chips (siehe docs/hardware.md).
  Helligkeit ausschließlich manuell regelbar (Regler unter Einstellungen/Home
  oder ein zweiter Dreh-Encoder am Gerät) - kein automatisches Dimmen; jede
  Änderung blendet den neuen Wert kurz auf dem Display ein. Braucht dafür die
  Backlight-Verkabelung per Software-PWM statt fest an 3.3V (siehe docs/hardware.md).
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
    einem Feuerwerk am Himmel - alles als Standbild statt laufender Animation, um den Pi 3B+ nicht
    unnötig zu belasten; das Standard-Thema "Winter" bekommt dafür ein statisches Schneeflocken-Muster.
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
    automatisch nach Ablauf, mit sanftem Ausblenden); WLAN (Status, an/aus, nach Netzwerken suchen
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
in Chromium auf dem 3.5"-SPI-Display angezeigt wird (`scripts/kiosk.sh`) -
kein separates GUI-Toolkit nötig, funktioniert offline und ist auf einem
Pi 3B+ mit 1 GB RAM deutlich genügsamer als z.B. Kivy oder Qt. Das Display
selbst braucht dafür den passenden Kernel-Treiber/Overlay (siehe
docs/hardware.md) - Touch ist am Board zwar vorhanden, wird aber bewusst
nicht aktiviert.

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

Empfohlenes Basis-Image: **Raspberry Pi OS (Legacy) Lite, 64-bit** - Bookworm
mit dem alten Grafiktreiber (Pflicht für `fbcp`), aber bewusst *ohne*
Desktop-Umgebung, da der Kiosk-Autostart X nur für Chromium selbst startet
(kein lightdm/LXDE, das beim Boot nur unnötig Zeit kosten würde).

Für die Standardhardware (Pi 3B+, HiFiBerry Amp2, 3.5" SPI-Display der
tft35a/MHS-35-Familie, RC522, Taster/Encoder auf den Standard-Pins - siehe
[docs/hardware.md](docs/hardware.md)) genügt es, das Skript **zweimal mit
einem Neustart dazwischen** laufen zu lassen:

```bash
git clone <dieses-repo> owlbox
cd owlbox
sudo ./scripts/install.sh
```

**1. Durchlauf:** installiert Systempakete (mpv, ALSA, Chromium, minimaler
X-Stack, …), aktiviert SPI, deaktiviert ungenutzte Dienste und
Boot-Wartezeiten (Bluetooth, Netzwerk-Wartezeit, Boot-Splash - siehe
docs/hardware.md), legt einen `owlbox`-Systembenutzer an, richtet ein
Python-venv ein, trägt den HiFiBerry- und Display-Overlay automatisch in
`config.txt` ein, baut und installiert `fbcp`, lädt und startet den
Display-Treiber (`goodtft/LCD-show`) - der Pi startet am Ende von selbst neu.

**Danach das Skript einmal erneut ausführen** (`sudo ./scripts/install.sh`):
jetzt ist die HiFiBerry-Soundkarte aktiv, das Skript erkennt automatisch das
richtige ALSA-Gerät/den Mixer und trägt es in `config/config.yaml` ein,
entfernt die vom Display-Treiber gesetzte Touch-Overlay-Zeile wieder (Touch
bleibt bewusst aus), richtet den Kiosk-Autostart ein (eigener systemd-Dienst,
startet X direkt ohne Desktop-Umgebung) und startet `owlbox.service`.

Das Skript ist beliebig oft wiederholbar (idempotent) - jeder Schritt prüft
zuerst, ob er schon erledigt ist. Danach bleiben nur zwei Dinge wirklich
manuell, weil kein Skript sie übernehmen kann:

1. RC522-RFID-Leser (an CE1, nicht CE0), Taster und Dreh-Encoder verkabeln -
   siehe [docs/hardware.md](docs/hardware.md) bzw. **OwlBox-Verkabelung.pdf**.
2. `http://<pi-ip>:5000/admin` öffnen und die Ersteinrichtung (Benutzername/
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
