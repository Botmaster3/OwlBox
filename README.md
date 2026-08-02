# OwlBox 🦉

Eine Toniebox-ähnliche Musik-/Hörspielbox für den Raspberry Pi: RFID-Chip
auflegen, Geschichte/Musik spielt automatisch weiter genau dort, wo sie beim
letzten Mal aufgehört hat. Inhalte werden bequem über eine Web-Oberfläche auf
den Pi geladen und einem Chip zugewiesen.

## Funktionen

- **RFID-gesteuerte Wiedergabe**: Chip auflegen → zugehörige Playlist startet
  (mit gemerkter Position), Chip abnehmen → pausiert automatisch.
- **3.5" SPI-Display**: reine Anzeige (Cover, Geschichte, aktueller
  Kapitel-/Track-Titel, Fortschritt, Lautstärke) - kein Touch, Bedienung
  läuft ausschließlich über Taster/Encoder (siehe docs/hardware.md).
- **Physische Bedienung**: zwei Taster (vor/zurück) + Dreh-Encoder
  (drehen = Lautstärke, drücken = Play/Pause, lang drücken = herunterfahren).
- **Web-Verwaltung** (`/admin`): Hörspiele/Musik hochladen (mehrere Dateien +
  Cover), einem gescannten Chip zuweisen, Titel-Reihenfolge ändern,
  Shuffle/Repeat pro Geschichte, löschen. Optional passwortgeschützt.
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

```bash
git clone <dieses-repo> owlbox
cd owlbox
sudo ./scripts/install.sh
```

Das Skript installiert Systempakete (mpv, ALSA, Chromium, …), aktiviert SPI,
legt einen `owlbox`-Systembenutzer an, richtet ein Python-venv ein und
startet den `owlbox.service`. Was danach noch manuell zu tun ist (HiFiBerry-
Overlay, Verkabelung, Kiosk-Autostart), steht am Ende der Skriptausgabe und
ausführlich in [docs/hardware.md](docs/hardware.md).

## Bedienkonzept

| Aktion                          | Wirkung                                    |
|----------------------------------|--------------------------------------------|
| Chip auflegen (bekannt)          | Playlist lädt, Wiedergabe ab letzter Position |
| Chip auflegen (unbekannt)        | Anzeige "Unbekannter Chip", Scan wird geloggt (im Admin-UI direkt zuweisbar) |
| Chip abnehmen                    | Pause, Position wird gespeichert            |
| Taster "Zurück"                  | Neustart des Tracks, oder vorheriger Track wenn <3s gespielt |
| Taster "Weiter"                  | nächster Track                              |
| Encoder drehen                   | Lautstärke rauf/runter                      |
| Encoder drücken                  | Play/Pause                                  |
| Encoder lang drücken (4s)        | Pi sicher herunterfahren                    |

## Konfiguration

Alle Einstellungen (GPIO-Pins, SPI, ALSA-Device/Mixer, Ports, Admin-Passwort,
Lautstärkeschritte, …) liegen in `config/config.yaml`
(Vorlage: `config/config.example.yaml`, kommentiert). Diese Datei ist
bewusst `.gitignore`t, da sie gerätespezifisch ist.

## Inhalte hochladen

1. `/admin` öffnen (im lokalen Netz, z.B. `http://owlbox.local:5000/admin`).
2. Titel eingeben, Cover (optional) und eine oder mehrere Audiodateien
   (mp3/m4a/ogg/flac/wav/opus) auswählen, "Anlegen" klicken.
3. Bei der neu angelegten Geschichte auf "Chip zuweisen" klicken und den
   gewünschten RFID-Chip an den Leser halten - die Zuordnung passiert
   automatisch.
4. Fertig: Chip auflegen, Geschichte spielt.

## Tests

```bash
pytest
```

Die Tests laufen komplett im Simulationsmodus (kein echtes GPIO/RFID/mpv
nötig) und decken Datenbank-Repository, Player-Stub und die
Engine-Zustandsmaschine (Chip auflegen/abnehmen, Positionsspeicherung,
Lautstärke) ab.
