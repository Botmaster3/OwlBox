import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[2]
from functools import partial

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, PageBreak, ListFlowable, ListItem

from pdf_common import (
    PAGE_W, PAGE_H, MARGIN, ACCENT_DARK,
    S_H1, S_H2, S_H3, S_BODY, S_BULLET, S_MONO,
    spec_table, note_box, cover_page, draw_header_footer,
    make_toc, TocDocTemplate, style,
)

OUT = str(REPO_ROOT / "owlbox/web/static/docs/OwlBox-Verkabelung.pdf")
TITLE = "OwlBox – Verkabelung"

story = []
S_CODE_BLOCK = style("CodeBlock", fontName="DejaVuSansMono", fontSize=8.3, leading=12,
                      textColor=ACCENT_DARK, backColor=None, spaceAfter=6, leftIndent=8)


def h1(t):
    story.append(PageBreak())
    story.append(Paragraph(t, S_H1))


def h2(t):
    story.append(Paragraph(t, S_H2))


def h3(t):
    story.append(Paragraph(t, S_H3))


def p(t, style=S_BODY):
    story.append(Paragraph(t, style))


def bullets(items, style=S_BULLET):
    story.append(ListFlowable(
        [ListItem(Paragraph(i, style), bulletColor=ACCENT_DARK) for i in items],
        bulletType="bullet", start="•", leftIndent=14,
    ))
    story.append(Spacer(1, 6))


def code(lines):
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    from pdf_common import LIGHT_BG, RULE
    txt = "<br/>".join(l.replace("&", "&amp;").replace("<", "&lt;") for l in lines)
    t = Table([[Paragraph(txt, S_CODE_BLOCK)]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))


# ============================================================ Titelseite
story.append(PageBreak())

# ============================================================ Inhalt
toc = make_toc()
story.append(Paragraph("Inhalt", S_H1))
story.append(toc)

# ============================================================ 1. Zielhardware
h1("1. Zielhardware")
bullets([
    "Raspberry Pi 3B+",
    "HiFiBerry Amp2 (I2S-Verstärker-HAT, TAS5756M-Chip)",
    "RC522 RFID-Modul (SPI, 13,56 MHz)",
    "Offizielles Raspberry Pi 7″ Touch Display (erste Generation - DSI-Flachbandkabel für Bild "
    "und Touch, plus 4 Jumperkabel für Strom/I2C, siehe unten). Ersetzt das früher hier "
    "dokumentierte 3,5″-SPI-Display (tft35a/MHS-35-Klon); dessen Anleitung ist noch in der "
    "Git-Historie dieser Datei zu finden, falls je wieder gebraucht.",
    "2 Taster (vor/zurück)",
    "1 Dreh-Encoder mit Druckschalter (Lautstärke/Play-Pause)",
    "1 weiterer Dreh-Encoder ohne Taster (Helligkeit, s.u. - auf dieser Hardware aktuell ohne "
    "Wirkung, s. Kapitel 6)",
])
p("Alle Pin-Angaben sind BCM-Nummerierung und entsprechen den Standardwerten in "
  "config/config.example.yaml. Wer andere Pins verdrahtet, passt einfach die gpio:/rfid:-Sektion "
  "in config.yaml an.")
story.append(note_box(
    "Referenzgrafiken liegen zusätzlich zu dieser PDF im Projekt unter docs/: "
    "owlbox-wiring-diagram.svg (Gesamtaufbau), owlbox-gpio-pinout.svg (kompletter 40-Pin-Header), "
    "owlbox-adapter-layout.svg (Platinenlayout-Vorschlag) und hat-wiring.html (kompletter "
    "Schaltplan, im Browser öffnen)."
))

h2("Anschluss: offizielles 7″ Touch Display (DSI)")
p(
    "Anders als das frühere 3,5″-SPI-Display sitzt dieses Display <b>nicht</b> auf dem 40-Pin-"
    "Header - Bild und Touch laufen komplett über das mitgelieferte DSI-Flachbandkabel (eigener "
    "Steckplatz auf dem Pi, neben den HDMI-Buchsen). <b>Damit entfällt die frühere "
    "Steckplatz-Kollision mit dem HiFiBerry komplett</b> - der HiFiBerry sitzt normal direkt auf "
    "dem 40-Pin-Header, das Display hängt separat am DSI-Steckplatz."
)
p(
    "Die kleine Adapter-/Power-Platine auf der Rückseite des Displays braucht trotzdem 4 "
    "Jumper-/Dupont-Kabel zum Pi, weil DSI selbst weder Strom noch die I2C-Leitung fürs Touch "
    "mitführt:"
)
story.append(spec_table(
    [
        ["Display-Adapterplatine", "Pi-Pin (BCM)", "Zweck"],
        ["5V", "Pin 2 oder Pin 4", "Stromversorgung"],
        ["GND", "Pin 6 (oder jeder andere GND-Pin)", "Masse"],
        ["SDA", "Pin 3 (GPIO2)", "I2C-Datenleitung (Touch-Controller)"],
        ["SCL", "Pin 5 (GPIO3)", "I2C-Taktleitung (Touch-Controller)"],
    ],
    col_widths=[55 * mm, 55 * mm, 50 * mm],
))
story.append(note_box(
    "Kein Konflikt mit dem HiFiBerry, obwohl GPIO2/3 dieselben Pins sind, die er für seine eigene "
    "I2C-Steuerung nutzt: I2C ist ein echter Mehrgeräte-Bus, mehrere Chips teilen sich Takt-/"
    "Datenleitung problemlos, solange sie unterschiedliche Adressen haben - der Touch-Controller "
    "des Displays und der HiFiBerry-Chip (Adresse 0x4d, per i2cdetect -y 1 bestätigt) sitzen auf "
    "unterschiedlichen Adressen."
))
p(
    "Falls der HiFiBerry bereits vollflächig auf dem 40-Pin-Header aufgesteckt ist und die Pins "
    "dadurch von oben nicht mehr mit Dupont-Kabeln erreichbar sind: ein GPIO-Stacking-Header "
    "(Extra-Höhe, mit durchgeführten Pins) zwischen Pi und HiFiBerry löst das, ohne den HiFiBerry "
    "selbst umverkabeln zu müssen."
)
story.append(note_box(
    "Kein Treiber-Installer nötig, aber ein eigener Overlay ist Pflicht: dtoverlay=vc4-kms-v3d "
    "allein (Standard seit Bookworm) reicht nicht - das aktiviert nur den generellen "
    "KMS-Grafiktreiber, kennt aber die Timings/das Panel dieses konkreten Displays nicht. Ohne "
    "den zusätzlichen, displayspezifischen Overlay dtoverlay=vc4-kms-dsi-7inch bindet der Treiber "
    "gar kein Panel, Bildschirm bleibt komplett schwarz. Details und Bild-/Touch-Rotation siehe "
    "Kapitel 8; install.sh trägt den Overlay automatisch ein."
))

h2("GPIO-Belegung im Überblick")
story.append(spec_table(
    [
        ["Funktion", "BCM-Pin", "Genutzt von"],
        ["I2S BCLK", "18", "HiFiBerry"],
        ["I2S LRCLK", "19", "HiFiBerry"],
        ["I2S DIN", "20", "HiFiBerry"],
        ["I2S DOUT", "21", "HiFiBerry"],
        ["I2C SDA", "2", "HiFiBerry (Amp-Steuerung) und Display-Touch-Controller - gemeinsam am "
         "selben I2C-Bus, kein Konflikt (unterschiedliche Adressen), s.o."],
        ["I2C SCL", "3", "HiFiBerry (Amp-Steuerung) und Display-Touch-Controller, s.o."],
        ["SPI0 SCLK/MOSI/MISO/CE0/CE1", "11 / 10 / 9 / 8 / 7", "frei (das DSI-Display braucht "
         "kein SPI0 mehr; RC522 bleibt trotzdem auf Software-SPI, s. Kapitel 3)"],
        ["RC522 SCK (Software-SPI)", "4", "RC522 (rfid.sck_pin)"],
        ["RC522 MOSI (Software-SPI)", "16", "RC522 (rfid.mosi_pin)"],
        ["RC522 MISO (Software-SPI)", "15", "RC522 (rfid.miso_pin)"],
        ["RC522 SDA/CS (Software-SPI)", "14", "RC522 (rfid.cs_pin)"],
        ["RC522 RST", "26", "RC522 (rfid.reset_pin)"],
        ["Taster Weiter", "5", "Taster"],
        ["Taster Zurück", "6", "Taster"],
        ["Encoder CLK", "1", "Lautstärke-Encoder (17 wäre jetzt auch wieder frei, s. Kapitel 5)"],
        ["Encoder DT", "27", "Lautstärke-Encoder"],
        ["Encoder SW", "22", "Lautstärke-Encoder"],
        ["Display-Backlight", "-", "läuft über Sysfs, kein GPIO mehr - Backlight-Dimmen aktuell "
         "nicht angeschlossen, s. Kapitel 6"],
        ["Helligkeits-Encoder CLK", "23", "Helligkeits-Encoder (aktuell ohne Wirkung, s. Kapitel 6)"],
        ["Helligkeits-Encoder DT", "12", "Helligkeits-Encoder (aktuell ohne Wirkung, s. Kapitel 6)"],
    ],
    col_widths=[62 * mm, 28 * mm, 70 * mm],
))

# ============================================================ 2. HiFiBerry
h1("2. HiFiBerry Amp2")
p(
    "Der HiFiBerry belegt die I2S-Pins (BCM 18/19/20/21) sowie I2C (BCM 2/3) zur "
    "Verstärkersteuerung. In /boot/firmware/config.txt (bzw. /boot/config.txt auf älteren Images):"
)
code(["dtparam=audio=off", "dtoverlay=hifiberry-dacplus"])
story.append(note_box(
    "An echter Hardware bestätigt: Der Amp2 hat einen TAS5756M-Chip - dieselbe PCM512x-Chipfamilie "
    "wie die DAC+ Pro, ein komplett anderer Chip als der TAS5713 des älteren Amp/Amp+. "
    "dtoverlay=hifiberry-amp ist speziell für den TAS5713 und funktioniert mit dem Amp2 nicht: der "
    "Kernel spricht dann die falsche I2C-Adresse an, aplay -l zeigt „no soundcards found“ - äußert "
    "sich als Lautstärke, die sich nie ändert (bleibt bei 0). Zum Nachprüfen, welcher Chip verbaut "
    "ist: i2cdetect -y 1 - Adresse 0x4d antwortet beim TAS5756M/Amp2 (hifiberry-dacplus), Adresse "
    "0x1b beim TAS5713 vom Amp/Amp+ (hifiberry-amp).",
))
p("Nach einer Overlay-Änderung neu starten - dabei verschiebt sich meist auch die Kartennummer.")
p(
    "Danach mit <font face=\"DejaVuSansMono\" size=\"9\">aplay -l</font> die Kartennummer der "
    "HiFiBerry ermitteln (z.B. „card 2: ...“) und mit "
    "<font face=\"DejaVuSansMono\" size=\"9\">amixer -c &lt;Kartennummer&gt; scontrols</font> den "
    "Mixer-Namen prüfen - beides in config.yaml eintragen: audio.alsa_device "
    "(\"hw:&lt;Kartennummer&gt;,0\"), audio.mixer_control (Amp/Amp2 nutzen meist „Digital“, manche "
    "Boards „PCM“ oder „Master“) <b>und audio.mixer_card</b> (nur die Kartennummer, ohne hw:/,0)."
)
story.append(note_box(
    "Alle drei müssen zur selben Karte passen - install.sh trägt sie bei der automatischen "
    "Erkennung mittlerweile alle drei ein, aber wer das von Hand einträgt, vergisst leicht "
    "mixer_card: bleibt die auf ihrem Standardwert \"0\" stehen während die HiFiBerry tatsächlich "
    "auf einer anderen Kartennummer läuft, zielt jede Lautstärkeabfrage/-änderung ins Leere - "
    "äußert sich als „eingestellte Lautstärke wird nie gespeichert, zeigt immer 0“.",
    kind="warn",
))
h2("Wichtig: vc4-kms-v3d braucht ,noaudio")
p(
    "Der vc4-kms-v3d-Grafiktreiber-Overlay registriert standardmäßig zusätzlich eine eigene "
    "HDMI-Audio-ALSA-Karte (taucht in aplay -l als „card N: vc4hdmi“ auf), auch wenn HDMI-Audio "
    "in diesem Projekt nie genutzt wird (Anzeige läuft über DSI, Ton ausschließlich über den "
    "HiFiBerry)."
)
story.append(note_box(
    "An echter Hardware bestätigt, Ursache eines tagelangen „Wiedergabe knackt/fragmentiert "
    "trotz digital korrektem Signalweg“-Rätsels: Diese HDMI-Audio-Registrierung kollidiert "
    "offenbar mit dem I2S-Pfad des HiFiBerry (beide laufen letztlich über denselben "
    "VC4-I2S/Audio-Hardwareblock) - äußert sich als digital sauber ankommende, aber physisch "
    "knacksende/fragmentierte Wiedergabe, dazu wiederkehrende pcm512x-I2C-Fehler im Kernel-Log. "
    "Keins der naheliegenden Gegenmittel (Auto Mute an/aus, Bluetooth deaktivieren, "
    "Runtime-Power-Management-Sysfs-Override, selbst ein komplett frisches SD-Karten-Image) "
    "behebt das, weil keins davon die eigentliche Ursache anfasst.",
    kind="warn",
))
p("Der Fix: ,noaudio an den Overlay anhängen, damit vc4-kms-v3d sich aus der Audio-Seite dieses "
  "gemeinsam genutzten Hardwareblocks komplett heraushält:")
code(["dtoverlay=vc4-kms-v3d,noaudio"])
p("install.sh trägt das automatisch so ein.")
story.append(note_box(
    "Zweite Falle, an echter Hardware bestätigt: Der Fix wirkt nur, wenn er die EINZIGE "
    "dtoverlay=vc4-kms-v3d-Zeile in der Datei ist. Ein frisches Raspberry Pi OS Bookworm-Image "
    "bringt in config.txt bereits eine eigene, unkommentierte dtoverlay=vc4-kms-v3d-Zeile mit "
    "(ohne ,noaudio). Anders als dtparam=-Zeilen sind dtoverlay=-Zeilen "
    "KEINE Key/Value-Overrides - jede einzelne wendet den Overlay unabhängig an. Stehen beide "
    "Zeilen in der Datei, registriert die erste trotzdem ihre eigene vc4hdmi-Karte, und das "
    "Knacksen bleibt bestehen. Kontrolle: grep -n dtoverlay=vc4-kms-v3d config.txt sollte genau "
    "einen Treffer zeigen (den mit ,noaudio); aplay -l sollte keine vc4hdmi-Karte mehr auflisten. "
    "install.sh passt die vorbestehende Zeile jetzt automatisch direkt an Ort und Stelle an "
    "(statt sie zu löschen und eine eigene Kopie ans Dateiende anzuhängen) - auf einer schon "
    "länger laufenden Installation reicht dafür ein erneutes "
    "sudo owlbox-install plus Neustart. Wichtig: dafür wirklich owlbox-install verwenden (ein "
    "stabiler Befehl, den das Skript bei seinem ersten erfolgreichen Durchlauf selbst unter "
    "/usr/local/bin anlegt), nicht cd owlbox && sudo ./scripts/install.sh - cd owlbox von "
    "innerhalb eines bereits ausgecheckten Repos landet nicht im Repo-Root, sondern eine Ebene "
    "zu tief im gleichnamigen Python-Paket-Unterordner, und ./scripts/install.sh meldet dann "
    "nur „command not found“, ohne dass irgendetwas vom Skript tatsächlich läuft.",
    kind="warn",
))
story.append(note_box(
    "Dritte Falle, ebenfalls an echter Hardware bestätigt: dtparam=audio=on muss aus demselben "
    "Grund verschwinden, nicht nur auskommentiert oder von einem späteren dtparam=audio=off "
    "\"überschrieben\" werden. Ein frisches Bookworm-Image bringt standardmäßig eine eigene, "
    "unkommentierte dtparam=audio=on-Zeile mit. Die naheliegende Annahme - dtparam=-Zeilen "
    "seien Key/Value-Overrides, bei denen die letzte Zeile gewinnt, also würde install.sh's "
    "eigenes, weiter unten stehendes dtparam=audio=off automatisch siegen - hat sich an echter "
    "Hardware NICHT zuverlässig bestätigt: die onboard „bcm2835 Headphones“-ALSA-Karte tauchte "
    "trotz korrekt zuletzt stehendem dtparam=audio=off über mehrere Neustarts hinweg immer "
    "wieder in aplay -l auf. install.sh kommentiert seit dieser Erkenntnis die vorbestehende "
    "dtparam=audio=on-Zeile automatisch direkt an Ort und Stelle aus (#dtparam=audio=on), statt "
    "sich auf Override-Semantik zu verlassen - derselbe sudo owlbox-install plus Neustart wie "
    "oben behebt beides in einem Rutsch.",
    kind="warn",
))
h2("Lautsprecher anschließen")
p(
    "Der HiFiBerry Amp2 hat dafür keine Stecker (kein Cinch/Klinke), sondern zwei 2-polige "
    "Federklemmen direkt auf der Platine (eine pro Kanal, jeweils +/-). Angeschlossen wird ganz "
    "normales 2-adriges Lautsprecherkabel:"
)
bullets([
    "Querschnitt ≥ 0,75 mm² (AWG 18) reicht für 15W/4Ω locker; bei längeren Kabelwegen (&gt; 3-5m) "
    "eher 1,0-1,5 mm² nehmen.",
    "Enden abisolieren (~10mm); bei feindrähtiger Litze verzinnen oder Aderendhülsen verwenden, "
    "damit die Federklemme sauber greift.",
    "Polarität an beiden Lautsprechern konsistent anschließen (+ zu + und Minus zu Minus) - sonst "
    "laufen sie gegenphasig und Bass/Stereo-Ortung leiden.",
    "Am Lautsprecher selbst hängt der Anschluss vom jeweiligen Modell ab (blanker Draht, "
    "Flachsteckhülsen/Bananas oder Lötfahnen).",
])

# ============================================================ 3. RC522
h1("3. RC522 RFID-Leser (Software-SPI auf freien GPIOs)")
story.append(note_box(
    "Anders als in den meisten RC522-Anleitungen im Netz hängt der RC522 hier NICHT an einem der "
    "beiden Hardware-SPI-Busse des Pi, sondern an vier per Software angesteuerten GPIOs. Grund: "
    "SPI1 liegt auf GPIO18-21, exakt den Pins, die der HiFiBerry für I2S-Ton braucht - SPI0 ist "
    "inzwischen zwar frei (das offizielle 7″-DSI-Touch-Display beansprucht es anders als das "
    "frühere SPI-Display nicht mehr), die RC522-Verdrahtung bleibt hier aber trotzdem auf "
    "Software-SPI, um nicht mehr als nötig gleichzeitig umzustellen. Der RC522 hat keine "
    "Mindesttaktrate, Software-SPI funktioniert daher zuverlässig, nur etwas langsamer als "
    "Hardware-SPI - für einen Chip-Scan völlig ausreichend."
))
story.append(spec_table(
    [
        ["RC522-Pin", "Raspberry Pi", "Config-Feld"],
        ["VCC", "3.3V (nicht 5V!)", "-"],
        ["GND", "GND", "-"],
        ["RST", "GPIO26", "rfid.reset_pin"],
        ["SDA (CS)", "GPIO14", "rfid.cs_pin"],
        ["SCK", "GPIO4", "rfid.sck_pin"],
        ["MOSI", "GPIO16", "rfid.mosi_pin"],
        ["MISO", "GPIO15", "rfid.miso_pin"],
        ["IRQ", "nicht verbunden", "-"],
    ],
    col_widths=[45 * mm, 55 * mm, 45 * mm],
))
p(
    "Alle vier GPIOs (4/14/15/16) sind sonst von nichts in diesem Projekt belegt. SPI selbst muss "
    "trotzdem aktiviert bleiben, weil der RC522 Software-SPI über lgpio braucht (macht "
    "scripts/install.sh bereits via raspi-config nonint do_spi 0, alternativ sudo raspi-config → "
    "Interface Options → SPI)."
)
story.append(note_box(
    "Historischer Hintergrund zum Lautstärke-Encoder auf GPIO1 statt GPIO17: Das frühere "
    "SPI-Display beanspruchte zusätzlich zu SPI0/CE0/CE1 auch GPIO17 als Interrupt-Pin "
    "(„pendown“) für den (nie verdrahteten) Touch-Controller - fest im damaligen Overlay "
    "einprogrammiert, unabhängig davon, ob Touch physisch angeschlossen war. Deshalb liegt der "
    "Lautstärke-Encoder-CLK auf GPIO1 (ID_SC, konventionell für ein HAT-ID-EEPROM reserviert, "
    "hier aber echt frei, da der HiFiBerry ohnehin per manueller dtoverlay-Zeile statt "
    "EEPROM-Erkennung konfiguriert wird). Mit dem neuen DSI-Display ist GPIO17 jetzt wieder frei "
    "- die Verkabelung bleibt hier trotzdem auf GPIO1, um nicht ohne Grund vom dokumentierten "
    "Standard abzuweichen; wer umverkabeln will, kann gpio.encoder_clk in config.yaml frei auf "
    "GPIO17 umstellen."
))
p(
    "An echter Hardware bestätigt: Sowohl das Software-SPI als auch der RC522-Reset-Pin laufen "
    "über lgpio (owlbox/rfid/lgpio_compat.py), nicht über RPi.GPIO - obwohl die mfrc522-"
    "Bibliothek intern eigentlich fest auf RPi.GPIO setzt (wird per unittest.mock.patch "
    "umgeleitet). Grund: gpiozero (Taster/Encoder) braucht auf aktuellen Kerneln zwingend lgpio, "
    "weil RPi.GPIOs eigene Kantenerkennung dort mit „Failed to add edge detection“ abbricht - "
    "RPi.GPIO zeigte in diesem Prozess außerdem selbst für unbenutzte Pins sofort „already in "
    "use“-Warnungen. Deshalb läuft die komplette GPIO-Ansteuerung dieses Projekts konsistent "
    "über lgpio, nirgends mehr über RPi.GPIO."
)

# ============================================================ 4. Taster
h1("4. Taster (vor/zurück)")
p(
    "Als Taster kommen Cherry-MX-Switches (3-Pin-Variante) zum Einsatz - elektrisch ganz normale "
    "Momentary-Schalter (schließt nur beim Drücken, öffnet sonst)."
)
bullets([
    "Von den 3 Pins sind nur die beiden Metall-Pins die elektrischen Kontakte (diagonal "
    "gegenüberliegend); der dritte, meist aus Kunststoff, ist nur ein mechanischer Halteclip ohne "
    "elektrische Funktion und muss nirgends angeschlossen werden.",
    "Jeweils einer der beiden Metall-Pins an GPIO, der andere an GND. Kein externer Widerstand "
    "nötig, der interne Pull-up wird von gpiozero aktiviert.",
    "Da Cherry-MX-Switches (anders als billige Blechtaster) sehr sauber prellen, reicht die "
    "Standard-Entprellzeit (gpio.bounce_time, 50ms) komfortabel aus.",
])
story.append(spec_table(
    [["Funktion", "BCM-Pin"], ["Zurück", "6"], ["Weiter", "5"]],
    col_widths=[100 * mm, 60 * mm],
))
p(
    "Kurz drücken springt zum vorherigen/nächsten Track. Gedrückt halten (länger als "
    "gpio.seek_hold_seconds, Standard 0,4s) spult stattdessen im aktuellen Track vor/zurück, in "
    "Schritten von gpio.seek_step_seconds (Standard 10s) - kein Trackwechsel, solange gehalten wird."
)

# ============================================================ 5. Encoder
h1("5. Dreh-Encoder mit Taster (KY-040)")
story.append(spec_table(
    [["Encoder-Pin", "Raspberry Pi"], ["CLK", "GPIO1 (nicht 17, siehe Kapitel 3)"], ["DT", "GPIO27"],
     ["SW", "GPIO22"], ["+", "3.3V"], ["GND", "GND"]],
    col_widths=[100 * mm, 60 * mm],
))
p(
    "Das KY-040-Modul bringt eigene Pull-up-Widerstände für CLK/DT mit; die zusätzlich von gpiozero "
    "aktivierten Pull-ups des Pi stören dabei nicht (einfach parallel). Für den Taster (SW) hat das "
    "Modul in der Regel keinen eigenen Pull-up - das übernimmt gpiozero.Button(pull_up=True) im "
    "Code, hier also nichts weiter nötig."
)
p(
    "Drehen ändert die Lautstärke (Schrittweite audio.volume_step), Drücken schaltet Play/Pause um. "
    "Ein langer Druck (gpio.shutdown_hold_seconds, Standard 4s) fährt den Pi sicher herunter - "
    "praktisch für ein Kindergerät ohne Zugriff auf ein Terminal. Auf 0 setzen, um das abzuschalten."
)

h2("Zweiter Dreh-Encoder für Helligkeit (KY-040)")
p(
    "Gehört zum Standardaufbau - dasselbe KY-040-Modul, diesmal ohne den Taster zu verdrahten "
    "(kein eigener Klick, nur Drehen). <b>Auf dieser Hardware aktuell ohne Wirkung</b> (siehe "
    "Kapitel 6) - der Encoder selbst kann so lange unverdrahtet bleiben."
)
story.append(spec_table(
    [["Encoder-Pin", "Raspberry Pi"], ["CLK", "GPIO23"], ["DT", "GPIO12"], ["+", "3.3V"], ["GND", "GND"]],
    col_widths=[100 * mm, 60 * mm],
))
p("Drehen ändert die Helligkeit (Schrittweite gpio.brightness_step, Standard 5%), sofort und rein "
  "manuell - es gibt kein automatisches Dimmen.")
story.append(note_box(
    "Damit Shutdown/Neustart (auch über die Web-UI oder einen Funktions-Chip) sowie der "
    "Update-Button auf der Info-Seite ohne Passwortabfrage funktionieren, braucht der Service-User "
    "owlbox passwortloses sudo dafür. install.sh richtet das automatisch ein "
    "(/etc/sudoers.d/owlbox, syntaxgeprüft vor dem Einspielen) - hier nur zur Referenz:"
))
code(["owlbox ALL=(ALL) NOPASSWD: /sbin/shutdown, /usr/bin/nmcli, \\", "  /usr/bin/systemctl restart --no-block owlbox"])
story.append(note_box(
    "Die Argumente müssen exakt wie oben dastehen (inklusive --no-block) - sudo "
    "vergleicht die komplette Befehlszeile. Fehlt --no-block, meldet der Update-Button "
    "auf der Info-Seite beim Neustart „sudo: a password is required“.",
    kind="warn",
))

# ============================================================ 6. Backlight
h1("6. Display-Hintergrundbeleuchtung")
story.append(note_box(
    "Wichtiger Unterschied zum alten Display: Dieses Display hat keine per GPIO/PWM ansteuerbare "
    "LED-Leitung wie das alte SPI-Display - die Helligkeit wird stattdessen intern über eine "
    "Linux-Backlight-Sysfs-Schnittstelle geregelt "
    "(/sys/class/backlight/.../brightness), angesteuert vom Power-Chip auf der "
    "Display-Adapterplatine selbst. Es gibt daher keine eigene Verkabelung mehr für diesen "
    "Punkt - kein Transistor, kein MOSFET, keine LED-Leitung, kein gpio.backlight_pin."
))
p(
    "Die GPIO13-Transistor-Schaltung und gpio.backlight_pin aus der alten Verkabelung entfallen "
    "damit ersatzlos - <b>das Backlight-Dimmen über den zweiten Dreh-Encoder ist auf dieser "
    "Hardware aktuell nicht angeschlossen</b>, das müsste in owlbox/controls/gpio_controls.py "
    "erst auf die Sysfs-Schnittstelle umgestellt werden. Der zweite Encoder (Kapitel 5) kann so "
    "lange unverdrahtet bleiben - jede Helligkeitsänderung über die Web-Oberfläche blendet den "
    "neuen Wert zwar kurz auf dem Display ein, die eigentliche Backlight-Steuerung greift aber "
    "noch nicht."
)

# ============================================================ 7. Fallback-Hotspot
h1("7. Fallback-Hotspot (WLAN-Recovery)")
p(
    "Ist WLAN eingeschaltet, aber für network.hotspot_after_seconds (Standard 60s) mit keinem "
    "Netzwerk verbunden - z.B. weil das Heimnetz sein Passwort geändert hat oder der Pi an einen "
    "neuen Ort umgezogen ist - macht der Pi automatisch seinen eigenen Access Point auf (nmcli "
    "device wifi hotspot), statt komplett unerreichbar zu bleiben."
)
p(
    "SSID und Passwort (aus config.yaml unter network:, Standard „OwlBox-Setup“ / „owlbox-setup“) "
    "werden auf dem Kiosk-Display und im Admin-Bereich angezeigt, inklusive der URL, unter der die "
    "Einstellungen im Hotspot erreichbar sind (normalerweise http://10.42.0.1:5000/admin - "
    "NetworkManagers Standard-Adresse für einen geteilten Access Point)."
)
p(
    "Ablauf: mit einem Laptop/Handy in dieses WLAN einwählen, die angezeigte URL öffnen, unter "
    "Einstellungen → WLAN das eigentliche Netzwerk auswählen/verbinden. Sobald das klappt, beendet "
    "der Pi den Hotspot von selbst wieder."
)
story.append(note_box(
    "Das Standardpasswort „owlbox-setup“ steht so im Quellcode und ist damit öffentlich bekannt - "
    "für den Einsatz in einer Umgebung, in der Fremde in Funkreichweite kommen könnten, unbedingt "
    "in config.yaml ein eigenes Passwort setzen.",
    kind="warn",
))

# ============================================================ 8. Display-Treiber
h1("8. 7″ Touch Display: kein Treiber-Setup nötig")
p(
    "Im Gegensatz zum früheren 3,5″-SPI-Display (das einen virtuellen-HDMI-Trick, fbcp und den "
    "alten Legacy-Grafiktreiber brauchte, um überhaupt ein Bild zu zeigen) ist das offizielle "
    "7″-Display an einem normalen Raspberry Pi OS Bookworm-Image komplett plug-and-play: Firmware "
    "erkennt es automatisch über das DSI-Kabel, keine dtoverlay=-Zeile, kein Treiber-Installer, "
    "kein Extra-Paket. Empfohlenes Basis-Image bleibt trotzdem Raspberry Pi OS Lite, 64-bit (ohne "
    "Desktop-Umgebung) - der Kiosk startet X selbst nur für Chromium (siehe Kapitel 9), eine "
    "mitinstallierte Desktop-Umgebung (lightdm, LXDE) würde beim Boot nur unnötig Zeit kosten. "
    "Wichtig ist nur: der moderne KMS-Grafiktreiber (vc4-kms-v3d) bleibt aktiv (Bookworm-Standard) "
    "- er wurde beim alten Display extra deaktiviert, das ist mit diesem Display nicht mehr nötig "
    "und würde die GPU-Beschleunigung sogar wieder kosten."
)
story.append(note_box(
    "Ein eigener Overlay ist trotzdem Pflicht: dtoverlay=vc4-kms-v3d,noaudio allein aktiviert nur "
    "den generellen KMS-Treiber, kennt aber die Timings dieses konkreten Panels nicht - "
    "zusätzlich braucht es dtoverlay=vc4-kms-dsi-7inch. Ohne diesen zweiten Overlay bindet der "
    "Treiber gar kein Panel (dmesg zeigt „[drm] Cannot find any crtc or sizes“, Bildschirm bleibt "
    "komplett schwarz, kein Fehler sonst irgendwo sichtbar). install.sh trägt beide Zeilen "
    "automatisch in /boot/firmware/config.txt ein:"
))
code(["dtoverlay=vc4-kms-v3d,noaudio", "dtoverlay=vc4-kms-dsi-7inch"])

h2("Drehung um 180° (falls das Display auf dem Kopf verbaut ist)")
p(
    "Zwei verschiedene Stellschrauben für zwei verschiedene Dinge, an echter Hardware mühsam "
    "herausgefunden:"
)
bullets([
    "<b>Bild selbst:</b> Der vc4-kms-dsi-7inch-Overlay hat KEINEN rotate=-Parameter "
    "(/boot/firmware/overlays/README listet nur sizex/sizey/invx/invy/swapxy/disable_touch/dsi0 - "
    "ein versuchsweise angehängtes rotate=180 wird stillschweigend ignoriert). Die Bild-Rotation "
    "läuft stattdessen über einen Kernel-Boot-Parameter in cmdline.txt (nicht config.txt!): ans "
    "Ende der einzeiligen Datei anhängen.",
    "<b>Touch-Koordinaten:</b> KEINE zusätzlichen invx/invy-Parameter am Overlay setzen. Sobald "
    "das Bild über den cmdline.txt-Parameter gedreht ist, korrigiert X11/libinput die "
    "Touch-Koordinaten am gedrehten Ausgang bereits von sich aus passend mit - zusätzlich "
    "gesetztes invx,invy dreht dann nochmal drüber und zeigt sich als auf beiden Achsen "
    "spiegelverkehrter Touch relativ zum (korrekt gedrehten) Bild.",
])
code(["video=DSI-1:800x480@60,rotate=180"])
story.append(note_box(
    "install.sh trägt das automatisch ein. Wichtig: nicht über xrandr oder display_lcd_rotate "
    "versuchen - an echter Hardware bestätigt: xrandr --output DSI-1 --rotate inverted wird zwar "
    "anstandslos angenommen (xrandr --query zeigt danach „inverted“), das Panel zeichnet aber nie "
    "tatsächlich neu, selbst nach einem erzwungenen --off/--auto-Modeset. Der ältere Parameter "
    "display_lcd_rotate/lcd_rotate ist unter KMS ebenfalls wirkungslos.",
    kind="warn",
))
p(
    "Einfach dtoverlay=vc4-kms-dsi-7inch ohne weitere Parameter reicht, der Touch-Controller ist "
    "ohnehin Teil desselben Overlays, kein separater rpi-ft5406-Eintrag nötig."
)

# ============================================================ 9. Kiosk-Autostart
h1("9. Kiosk-Autostart (Chromium fullscreen, ohne Desktop-Umgebung)")
p(
    "Da die Basis „Lite“ keine Desktop-Umgebung mitbringt, gibt es auch kein lightdm/LXDE, in das "
    "sich der Kiosk einhängen könnte. Stattdessen startet ein eigener systemd-Dienst "
    "(owlbox-kiosk.service) X direkt selbst (per startx), übernimmt dafür tty1 und lässt "
    "scripts/kiosk.sh (das Chromium im Kiosk-Modus startet) als einzigen „Client“ laufen - keine "
    "Fensterleiste, kein Dateimanager-Desktop, kein Panel. Mit aktivem KMS-Treiber findet X's "
    "eigener, automatisch gewählter „modesetting“-Treiber /dev/dri/card0 von selbst - keine "
    "eigene Xorg-Konfiguration nötig (anders als beim alten Display, das X explizit auf einen "
    "Framebuffer-Treiber zwingen musste)."
)
code([
    "# X ohne Display-Manager erlauben:",
    "cat > /etc/X11/Xwrapper.config <<'EOF'",
    "allowed_users=anybody",
    "needs_root_rights=yes",
    "EOF",
    "",
    "sudo cp /opt/owlbox/systemd/owlbox-kiosk.service /etc/systemd/system/",
    "sudo systemctl daemon-reload",
    "sudo systemctl enable --now owlbox-kiosk.service",
])
story.append(note_box(
    "owlbox-kiosk.service bringt Conflicts=getty@tty1.service schon mit, muss also "
    "getty@tty1.service nicht extra deaktiviert bekommen - läuft aber sauberer, wenn man es "
    "trotzdem tut (sudo systemctl disable getty@tty1.service), damit dort kein ungenutzter "
    "Login-Prompt mehr mitstartet."
))
p(
    "Läuft doch eine volle Desktop-Umgebung (z.B. weil bewusst die volle Variante statt Lite "
    "geflasht wurde), lässt sich der Kiosk alternativ ganz klassisch über deren Autostart-Datei "
    "einhängen: ~/.config/lxsession/LXDE-pi/autostart um die Zeile "
    "@/opt/owlbox/scripts/kiosk.sh ergänzen."
)
story.append(note_box(
    "An echter Hardware bestätigt: owlbox-kiosk.service läuft bewusst mit niedrigerer "
    "CPU-/IO-Priorität als owlbox.service (Nice=15, IOSchedulingClass=best-effort, "
    "IOSchedulingPriority=7). Grund: Chromium läuft auf dieser Hardware komplett "
    "softwaregerendert (keine GPU-Beschleunigung verfügbar) - ohne Prioritätsdifferenz "
    "konkurrieren Chromium und mpv (läuft in owlbox.service) mit exakt gleicher Priorität um "
    "die knappe CPU eines Pi 3B+. Das war die eigentliche Ursache eines \"Wiedergabe knackt "
    "durchgehend\"-Rätsels, das auch nach dem Beheben aller config.txt-Probleme (Kapitel 2) und "
    "dem Entfernen unnötiger Subprozess-Aufrufe aus dem App-Code bestehen blieb: ein reiner "
    "config.txt-Test direkt nach frischer Installation plus aplay/mpv im Terminal (ganz ohne "
    "laufenden Kiosk) spielte sauber ab, derselbe Aufbau mit laufendem Kiosk knackste weiterhin. "
    "Ein positiver Nice-Wert braucht keine besonderen Rechte - install.sh trägt das automatisch "
    "ein und startet owlbox-kiosk.service bei Bedarf neu, damit die neue Priorität auch ohne "
    "kompletten Neustart greift.",
    kind="warn",
))

# ============================================================ 10. Konfiguration
h1("10. Konfigurationsdatei (config.yaml)")
p(
    "Alle in dieser Anleitung genannten Werte (Pins, Schrittweiten, Zeiten) stehen gesammelt in "
    "config/config.yaml (aus config/config.example.yaml kopieren). Die wichtigsten Abschnitte:"
)
story.append(spec_table(
    [
        ["Abschnitt", "Wichtigste Werte"],
        ["audio:", "alsa_device, mixer_control, default_volume, volume_step, chime_enabled"],
        ["rfid:", "reader, sck_pin, mosi_pin, miso_pin, cs_pin, reset_pin, poll_interval"],
        ["gpio:", "button_next/prev, encoder_clk/dt/switch, backlight_pin, "
         "brightness_encoder_clk/dt, shutdown_hold_seconds, seek_hold_seconds"],
        ["playback:", "restart_track_after_seconds, position_save_interval, auto_sleep_minutes, "
         "sleep_fade_seconds"],
        ["network:", "hotspot_ssid, hotspot_password, hotspot_after_seconds"],
        ["web:", "host, port, secret_key"],
    ],
    col_widths=[35 * mm, 125 * mm],
))
story.append(note_box(
    "config/config.yaml ist in .gitignore eingetragen, damit lokale, gerätespezifische Werte "
    "(insb. das Session-Secret) nie versehentlich committet werden."
))

# ---------------------------------------------------------------- build
doc = TocDocTemplate(
    OUT, pagesize=(PAGE_W, PAGE_H),
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22 * mm, bottomMargin=20 * mm,
    title="OwlBox Verkabelung", author="OwlBox",
)

on_cover = partial(
    cover_page,
    kicker="OWLBOX",
    title=["Verkabelung"],
    subtitle=["Vollständige Hardware-Referenz:", "Pinbelegung, 7″-DSI-Display, HiFiBerry, Netzwerk-Fallback."],
    meta_lines=["Hardware-Aufbau Raspberry Pi 3B+", "Schnelleinstieg: OwlBox-Schnellstart.pdf"],
)
on_page = partial(draw_header_footer, title=TITLE)

doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
print("wrote", OUT)
