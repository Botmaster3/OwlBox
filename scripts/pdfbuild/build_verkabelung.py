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
    "Raspberry Pi 5 (4GB) mit aktiver Kühlung (siehe Kapitel 2). Ersetzt das früher hier "
    "dokumentierte Pi 3B+; dessen vollständig verifiziertes Setup ist noch in der Git-Historie "
    "dieser Datei zu finden. Noch NICHT an echter Hardware verifiziert.",
    "HiFiBerry Amp2 (I2S-Verstärker-HAT, TAS5756M-Chip) - sitzt wegen des Kühlkörpers NICHT mehr "
    "direkt gestapelt auf dem 40-Pin-Header, sondern hängt über eine eigene Adapter-Platine dran, "
    "per Jumperkabel wie RC522/Taster/Encoder auch (siehe Kapitel 2). Noch NICHT an echter "
    "Hardware verifiziert.",
    "RC522 RFID-Modul (SPI, 13,56 MHz)",
    "Waveshare 5″ DSI Capacitive Touch Display (Modell 5-DSI-TOUCH-A, 720×1280, DSI-Flachbandkabel "
    "für Bild und Touch, plus 4 Jumperkabel für Strom/I2C, siehe unten). Ersetzt das früher hier "
    "dokumentierte offizielle Raspberry-Pi-7″-Touch-Display (800×480); dessen Anleitung ist noch "
    "in der Git-Historie dieser Datei zu finden, falls je wieder gebraucht. Noch NICHT an echter "
    "Hardware verifiziert, siehe Kapitel 1.1.",
    "2 Taster (vor/zurück)",
    "1 Dreh-Encoder mit Druckschalter (Lautstärke/Play-Pause)",
    "1 weiterer Dreh-Encoder ohne Taster (Helligkeit, s.u. - auf dieser Hardware aktuell ohne "
    "Wirkung, s. Kapitel 6)",
])
p("Alle Pin-Angaben sind BCM-Nummerierung und entsprechen den Standardwerten in "
  "config/config.example.yaml. Wer andere Pins verdrahtet, passt einfach die gpio:/rfid:-Sektion "
  "in config.yaml an.")
story.append(note_box(
    "Referenzgrafik zusätzlich zu dieser PDF im Projekt: docs/owlbox-gpio-pinout.svg "
    "(kompletter 40-Pin-Header, direkte Jumperkabel wie in dieser PDF). Für eine eigene, separat "
    "verdrahtete Adapter-Platine statt direkter Jumperkabel (optional, nicht Teil des "
    "Standardaufbaus): docs/owlbox-wiring-diagram.svg (Gesamtaufbau), "
    "docs/owlbox-adapter-layout.svg (Platinenlayout-Vorschlag) und docs/hat-wiring.html "
    "(kompletter Schaltplan, im Browser öffnen) - alle drei aktuell für RC522 auf "
    "Hardware-SPI0/CE0; die Display-Zeilen zeigen nur die generischen Strom-/I2C-Adern, nicht die "
    "produktspezifische Overlay-/Auflösungs-Konfiguration (siehe unten)."
))

h2("Anschluss: 5″ Waveshare DSI Touch Display")
story.append(note_box(
    "Dieser Abschnitt ist noch NICHT an echter Hardware verifiziert - anders als der Rest dieser "
    "PDF. Das Display (Waveshare 5-DSI-TOUCH-A, 720×1280, kapazitiver Touch, Aluminiumgehäuse) "
    "löst das bisherige offizielle 7″-Touch-Display (800×480) ab; dessen vollständig verifizierte "
    "Anleitung bleibt in der Git-Historie dieser Datei erhalten.",
    kind="warn",
))
p(
    "Wie beim bisherigen Display sitzt es <b>nicht</b> auf dem 40-Pin-Header - Bild und Touch "
    "laufen über das DSI-Flachbandkabel (eigener Steckplatz auf dem Pi, neben den HDMI-Buchsen), "
    "keine Steckplatz-Kollision mit dem HiFiBerry (der auf diesem Aufbau ohnehin nicht mehr direkt "
    "auf dem 40-Pin-Header sitzt, sondern über eine Adapter-Platine läuft, siehe Kapitel 2)."
)
p(
    "Die Adapter-/Power-Platine des Displays braucht vermutlich weiterhin 4 Jumper-/Dupont-Kabel "
    "zum Pi (Strom + I2C für den Touch-Controller), analog zum bisherigen Display:"
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
    "Bitte gegen das Waveshare-eigene Handbuch/Wiki prüfen, sobald das Display da ist - diese "
    "Tabelle ist vom bisherigen Display übernommen (gleiches Funktionsprinzip: DSI + separate "
    "Stromversorgung + I2C-Touch), aber nicht produktspezifisch bestätigt.",
    kind="warn",
))
story.append(note_box(
    "Kein Konflikt mit dem HiFiBerry, obwohl GPIO2/3 dieselben Pins sind, die er für seine eigene "
    "I2C-Steuerung nutzt: I2C ist ein echter Mehrgeräte-Bus, mehrere Chips teilen sich Takt-/"
    "Datenleitung problemlos, solange sie unterschiedliche Adressen haben - vorausgesetzt, der "
    "Touch-Controller dieses Displays sitzt tatsächlich auch auf I2C."
))
p(
    "(Hinweis aus dem früheren, direkt gestapelten Aufbau, hier nur noch der Vollständigkeit "
    "halber: säße der HiFiBerry doch einmal wieder direkt auf dem 40-Pin-Header und die Pins "
    "dadurch von oben nicht mehr mit Dupont-Kabeln erreichbar, würde ein GPIO-Stacking-Header "
    "[Extra-Höhe, mit durchgeführten Pins] zwischen Pi und HiFiBerry das lösen. Auf dem aktuellen "
    "Aufbau nicht relevant, da der HiFiBerry ohnehin über die Adapter-Platine läuft, s. Kapitel 2.)"
)
story.append(note_box(
    "Overlay laut Waveshare-Wiki (waveshare.com/wiki/5-DSI-TOUCH-A - nicht direkt erreichbar "
    "geprüft, nur über Suchergebnisse, bitte gegenlesen): dtparam=i2c_arm=on plus "
    "dtoverlay=vc4-kms-dsi-waveshare-panel-v2,5_0_inch_a. NICHT der bisherige "
    "dtoverlay=vc4-kms-dsi-7inch (spezifisch fürs alte Display) und NICHT das ähnlich klingende "
    "vc4-kms-dsi-waveshare-panel,5_0_inch ohne \"-v2\"/\"_a\" (andere Waveshare-5″-Modelle). "
    "install.sh trägt den Overlay automatisch ein. Rotation/Ausrichtung bewusst nicht "
    "konfiguriert - wird laut Auftraggeber beim physischen Einbau gelöst, nicht per Software; "
    "Details siehe Kapitel 8.",
    kind="warn",
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
        ["SPI0 SCLK/MOSI/MISO/CE0", "11 / 10 / 9 / 8", "RC522 (Hardware-SPI, s. Kapitel 3)"],
        ["SPI0 CE1", "7", "frei (nicht genutzt - der RC522 braucht nur CE0)"],
        ["RC522 RST", "26", "RC522 (rfid.reset_pin)"],
        ["Taster Weiter", "5", "Taster"],
        ["Taster Zurück", "6", "Taster"],
        ["Encoder CLK", "1", "Lautstärke-Encoder (17 ist inzwischen wieder belegt, s.u.)"],
        ["Encoder DT", "27", "Lautstärke-Encoder"],
        ["Encoder SW", "22", "Lautstärke-Encoder"],
        ["Display-Backlight", "-", "läuft über Sysfs, kein GPIO mehr - ob eine Helligkeitsänderung "
         "per Encoder unten physisch etwas bewirkt, ist noch offen, s. Kapitel 6"],
        ["Helligkeits-Encoder CLK", "23", "Helligkeits-Encoder"],
        ["Helligkeits-Encoder DT", "12", "Helligkeits-Encoder"],
        ["Helligkeits-Encoder SW", "17", "Helligkeits-Encoder - Nachtmodus-Umschalter "
         "(gpio.brightness_encoder_switch), s.u."],
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
    "Auf dem Pi 5 stattdessen dtoverlay=hifiberry-dacplus-std - ein kernelseitiger Probe-Fix, "
    "spezifisch für die BCM2712-SoC/RP1-Kombination des Pi 5 (laut HiFiBerry und dem "
    "raspberrypi/linux-Issue-Tracker). Noch NICHT an echter Pi-5-Hardware verifiziert. "
    "install.sh wählt das automatisch anhand des erkannten Boards (/proc/device-tree/model).",
    kind="warn",
))
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

h2("2.1 Aktive Kühlung (Pi 5)")
story.append(note_box(
    "Dieser komplette Abschnitt ist noch NICHT an echter Hardware verifiziert - die "
    "Software-Anpassungen sind vorbereitet, aber dieses Projekt lief zum Zeitpunkt des Schreibens "
    "noch auf einem Pi 3B+.",
    kind="warn",
))
p(
    "Verbaut: GeeekPi Low-Profile Plus CPU Cooler (Aluminium-Kühlkörper mit Lüfter, für Pi 5 "
    "4GB/8GB/16GB). Steckt wie der offizielle Raspberry-Pi-„Active Cooler“ auf den eigenen "
    "4-Pin-JST-Lüfteranschluss des Pi 5 (rechts oben, zwischen 40-Pin-Header und den USB-2-Ports) "
    "- <b>kein GPIO-Pin, keine config.txt-Zeile nötig</b>. Die Drehzahl regelt die Pi-5-Firmware "
    "selbst temperaturabhängig (Stufen bei ca. 60°C/67,5°C/75°C), unabhängig vom Betriebssystem. "
    "Damit ist die Kühlung für dieses Projekt reine Mechanik - sie taucht in keiner GPIO-Tabelle "
    "auf und braucht keine eigene config.yaml-Einstellung."
)
story.append(note_box(
    "Nur falls stattdessen doch einmal ein anderer, GPIO-verdrahteter Lüfter verbaut wird (nicht "
    "der hier tatsächlich verbaute, nur zur Einordnung): das bräuchte einen zusätzlichen freien "
    "BCM-Pin plus einen eigenen Fan-Overlay/eine eigene Steuerlogik - für den GeeekPi-Kühler oben "
    "nicht relevant, der läuft komplett über den festen 4-Pin-Anschluss."
))
story.append(note_box(
    "Stromversorgung: Der Pi 5 empfiehlt offiziell ein 5V/5A-USB-C-PD-Netzteil (27W) - mit "
    "HiFiBerry Amp2 (kann bei Zimmerlautstärke durchaus über 1A aus der 5V-Schiene ziehen) und "
    "aktivem Lüfter zusammen an einem schwächeren Netzteil (z.B. die alten 5V/2,5-3A-Netzteile "
    "vom Pi-3B+-Aufbau) drohen Unterspannungswarnungen/-drosselung. Für diesen Aufbau (Amp2 unter "
    "Last plus Lüfter) das offizielle 27W-Netzteil verwenden.",
    kind="warn",
))

h2("2.2 Nicht mehr direkt aufgesteckt: Anschluss über Adapter-Platine")
story.append(note_box(
    "Dieser Abschnitt ist noch NICHT an echter Hardware verifiziert.",
    kind="warn",
))
p(
    "Wegen des Kühlkörpers auf dem Pi 5 sitzt der Amp2 nicht mehr direkt gestapelt auf dem "
    "40-Pin-Header, sondern hängt über Jumperkabel an einer eigenen, separat verdrahteten "
    "Adapter-Platine - demselben Eigenbau-Muster (Lochraster + Jumperkabel), das dieses Projekt "
    "für RC522/Taster/Encoder schon einsetzt (docs/hat-wiring.html, dort aber noch nicht auf "
    "diesen Aufbau aktualisiert). Der Amp2 selbst bleibt unverändert - es ändert sich nur, wie "
    "seine Pins den Pi erreichen."
)
story.append(spec_table(
    [
        ["HiFiBerry Amp2", "Pi-Pin (BCM)", "Zweck"],
        ["BCLK", "GPIO18", "I2S-Bit-Clock"],
        ["LRCLK/WS", "GPIO19", "I2S-Wortauswahl (links/rechts)"],
        ["DIN", "GPIO20", "I2S-Audiodaten"],
        ["DOUT", "GPIO21", "I2S (vom Amp2 ungenutzt für reine Wiedergabe, trotzdem verbinden)"],
        ["SDA", "GPIO2", "I2C-Datenleitung (Verstärkersteuerung)"],
        ["SCL", "GPIO3", "I2C-Taktleitung (Verstärkersteuerung)"],
    ],
    col_widths=[45 * mm, 40 * mm, 75 * mm],
))
story.append(spec_table(
    [
        ["HiFiBerry Amp2", "Pi-Pin (physisch)", "Zweck"],
        ["5V", "Pin 2 UND Pin 4", "Versorgung des kompletten Verstärkers inkl. Lautsprecherausgang"],
        ["GND", "mind. 1-2 GND-Pins (z.B. 6, 9, 14)", "Masse"],
    ],
    col_widths=[45 * mm, 55 * mm, 60 * mm],
))
story.append(note_box(
    "Wichtig, unabhängig von echter Hardware ableitbar (Elektrotechnik, nicht projektspezifisch "
    "getestet): Anders als bei RC522/Tastern/Encodern, die nur Milliampere-Signalpegel führen, "
    "zieht der Amp2 seine komplette Lautsprecher-Ausgangsleistung direkt aus der 5V-Schiene "
    "(Class-D-Verstärker) - bei Zimmerlautstärke können das ohne Weiteres über 1A sein, "
    "kurzzeitig bei Bässen/hoher Lautstärke auch mehr. Für diese eine Verbindung NICHT dieselben "
    "dünnen Jumper-/Dupont-Kabel wie für RC522/Taster/Encoder verwenden (typischerweise nur für "
    "&lt; 1A ausgelegt): beide 5V-Pins UND mehrere GND-Pins parallel nutzen, wenn möglich kurze, "
    "dickere Leitungen (z.B. AWG 20 oder dicker) für genau diese beiden Adern. Nach dem "
    "Zusammenbau prüfen: vcgencmd get_throttled sollte 0x0 zeigen (keine Unterspannung); bei "
    "hörbarem Verzerren/Aussetzern unter Last zuerst hier ansetzen. Kein 3.3V-Pin nötig - der "
    "Amp2 hat kein ID_SD/ID_SC-EEPROM (der Overlay wird manuell eingetragen, s.o.). Die genaue "
    "Stromaufnahme steht im Datenblatt des Amp2 (HiFiBerry-eigene Seite) - vor dem endgültigen "
    "Verkabeln dort noch einmal gegenprüfen.",
    kind="warn",
))

# ============================================================ 3. RC522
h1("3. RC522 RFID-Leser (Hardware-SPI0)")
story.append(note_box(
    "Der RC522 hängt an SPI0, dem Hardware-SPI-Bus des Pi (/dev/spidev0.0, CE0). Grund, warum das "
    "möglich ist: SPI1 liegt auf GPIO18-21, exakt den Pins, die der HiFiBerry für I2S-Ton braucht "
    "- SPI0 ist mit dem aktuellen DSI-Touch-Display aber frei (anders als beim früheren "
    "SPI-Display, dessen Overlay beide Chip-Selects von SPI0 belegte)."
))
story.append(spec_table(
    [
        ["RC522-Pin", "Raspberry Pi", "Config-Feld"],
        ["VCC", "3.3V (nicht 5V!)", "-"],
        ["GND", "GND", "-"],
        ["RST", "GPIO26", "rfid.reset_pin"],
        ["SDA (CS)", "GPIO8 (SPI0 CE0)", "-"],
        ["SCK", "GPIO11 (SPI0 SCLK)", "-"],
        ["MOSI", "GPIO10 (SPI0 MOSI)", "-"],
        ["MISO", "GPIO9 (SPI0 MISO)", "-"],
        ["IRQ", "nicht verbunden", "-"],
    ],
    col_widths=[45 * mm, 55 * mm, 45 * mm],
))
p(
    "Die mfrc522-Python-Bibliothek spricht den Bus direkt über spidev an, kein Bit-Banging mehr "
    "nötig. SPI selbst muss aktiviert bleiben (macht scripts/install.sh bereits via "
    "raspi-config nonint do_spi 0, alternativ sudo raspi-config → Interface Options → SPI)."
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
    "An echter Hardware bestätigt: Der RC522-Reset-Pin läuft über lgpio (owlbox/rfid/"
    "lgpio_compat.py), nicht über RPi.GPIO - obwohl die mfrc522-Bibliothek intern eigentlich fest "
    "auf RPi.GPIO setzt (wird per unittest.mock.patch umgeleitet, nur für diesen einen Pin - die "
    "SPI-Datenleitungen selbst laufen über den Kernel-spidev-Treiber). Grund: gpiozero "
    "(Taster/Encoder) braucht auf aktuellen Kerneln zwingend lgpio, weil RPi.GPIOs eigene "
    "Kantenerkennung dort mit „Failed to add edge detection“ abbricht - RPi.GPIO zeigte in diesem "
    "Prozess außerdem selbst für unbenutzte Pins sofort „already in use“-Warnungen. Deshalb läuft "
    "die komplette GPIO-Ansteuerung dieses Projekts konsistent über lgpio, nirgends mehr über "
    "RPi.GPIO."
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
    "Gehört zum Standardaufbau - dasselbe KY-040-Modul wie beim Lautstärke-Encoder, diesmal "
    "<b>mit</b> Taster (anders als früher - der Taster wird jetzt für den Nachtmodus gebraucht, "
    "s.u.)."
)
story.append(spec_table(
    [["Encoder-Pin", "Raspberry Pi"], ["CLK", "GPIO23"], ["DT", "GPIO12"],
     ["SW", "GPIO17 (gpio.brightness_encoder_switch)"], ["+", "3.3V"], ["GND", "GND"]],
    col_widths=[100 * mm, 60 * mm],
))
p("Drehen ändert die Helligkeit (Schrittweite gpio.brightness_step, Standard 5%), sofort und rein "
  "manuell - es gibt kein automatisches Dimmen. Diese Box nutzt bewusst nicht die eigene "
  "Touch-Helligkeitsregelung, die das Waveshare-Display selbst laut Auftraggeber mitbringt - "
  "ausschließlich Encoder und Web-UI.")
story.append(note_box(
    "Noch nicht an echter Hardware verifiziert: ob eine Helligkeitsänderung per Encoder/Software "
    "auf diesem Display überhaupt sichtbar etwas bewirkt - siehe Kapitel 6, Status dort schon "
    "länger unklar, unabhängig vom Nachtmodus-Feature hier.",
    kind="warn",
))
p(
    "<b>Nachtmodus:</b> Ein Druck auf den Taster (SW) schaltet zwischen der normalen "
    "(\"Tag\"-)Helligkeit und einer separat konfigurierbaren, oft deutlich dunkleren "
    "Nachtmodus-Helligkeit um - konfigurierbar in Einstellungen → Anzeige (night_brightness, "
    "Standard 5%). Anders als die normale Helligkeit darf die Nachtmodus-Helligkeit bewusst unter "
    "die dort eingestellte Minimal-Helligkeit gehen, das ist der ganze Zweck. Kein Zeitplan - "
    "bleibt aktiv, bis erneut gedrückt wird, außer über einen Neustart hinweg (startet immer im "
    "Tag-Modus). Ändert sich die Helligkeit während des Nachtmodus direkt (Schieberegler, Drehen "
    "an demselben Encoder), beendet das den Nachtmodus automatisch, statt den neuen Wert beim "
    "nächsten Tastendruck wieder zu verwerfen. gpio.brightness_encoder_switch auf null setzen, um "
    "den Taster unverdrahtet zu lassen und die Funktion nur über die Web-UI nutzbar zu machen."
)
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
    "Noch nicht an echter Hardware verifiziert, welchen Mechanismus dieses Display für die "
    "Helligkeit anbietet: eine per GPIO/PWM ansteuerbare LED-Leitung wie beim alten SPI-Display, "
    "eine interne Linux-Backlight-Sysfs-Schnittstelle (/sys/class/backlight/.../brightness, "
    "angesteuert vom Power-Chip auf der Display-Adapterplatine) - oder nur die eigene, laut "
    "Auftraggeber vorhandene Touch-Helligkeitsregelung des Displays, die diese Box bewusst nicht "
    "verwendet (siehe Kapitel 5). Falls es tatsächlich Sysfs ist: kein gpio.backlight_pin, kein "
    "Transistor/MOSFET nötig, aber owlbox/backlight.py müsste dafür erst auf die Sysfs-"
    "Schnittstelle umgestellt werden - aktuell nutzt es noch GPIO-PWM.",
    kind="warn",
))
p(
    "Software-seitig ist der zweite Encoder trotzdem vollständig verdrahtet und angebunden (CLK/DT "
    "fürs Drehen, SW für den Nachtmodus-Taster, siehe Kapitel 5) - jede Helligkeitsänderung über "
    "Encoder, Web-Oberfläche oder Nachtmodus-Taster ändert den intern gespeicherten "
    "brightness-Wert zuverlässig und blendet ihn kurz auf dem Display ein. Ob sich davon auch die "
    "tatsächliche Display-Helligkeit sichtbar ändert, hängt vom oben noch offenen Mechanismus ab "
    "und ist erst an echter Hardware zu klären."
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
h1("8. DSI-Display: kein separater Treiber-Installer nötig")
p(
    "Im Gegensatz zum früheren 3,5″-SPI-Display (das einen virtuellen-HDMI-Trick, fbcp und den "
    "alten Legacy-Grafiktreiber brauchte, um überhaupt ein Bild zu zeigen) kommt das aktuelle "
    "DSI-Display an einem normalen Raspberry Pi OS Bookworm-Image ohne Treiber-Installer, ohne "
    "Extra-Paket aus - nur die eine dtoverlay=-Zeile unten ist nötig, sonst nichts. Empfohlenes "
    "Basis-Image bleibt Raspberry Pi OS Lite, 64-bit (ohne Desktop-Umgebung) - der Kiosk startet X "
    "selbst nur für Chromium (siehe Kapitel 9), eine mitinstallierte Desktop-Umgebung (lightdm, "
    "LXDE) würde beim Boot nur unnötig Zeit kosten. Wichtig ist nur: der moderne KMS-Grafiktreiber "
    "(vc4-kms-v3d) bleibt aktiv (Bookworm-Standard) - er wurde beim alten SPI-Display extra "
    "deaktiviert, das ist mit einem DSI-Display nicht mehr nötig und würde die GPU-Beschleunigung "
    "sogar wieder kosten."
)
story.append(note_box(
    "Noch NICHT an echter Hardware verifiziert. Laut Waveshare-Wiki "
    "(waveshare.com/wiki/5-DSI-TOUCH-A): dtoverlay=vc4-kms-v3d,noaudio allein aktiviert nur den "
    "generellen KMS-Treiber, kennt aber die Timings dieses konkreten Panels nicht - zusätzlich "
    "braucht es dtoverlay=vc4-kms-dsi-waveshare-panel-v2,5_0_inch_a (NICHT das bisherige "
    "dtoverlay=vc4-kms-dsi-7inch, das war spezifisch für das alte offizielle Display). Beim alten "
    "Display äußerte sich ein fehlender displayspezifischer Overlay als komplett schwarzer "
    "Bildschirm (dmesg: „[drm] Cannot find any crtc or sizes“) - für dieses Display noch nicht "
    "bestätigt, aber vermutlich vergleichbar. install.sh trägt beide Zeilen automatisch in "
    "/boot/firmware/config.txt ein:",
    kind="warn",
))
code(["dtparam=i2c_arm=on", "dtoverlay=vc4-kms-v3d,noaudio",
      "dtoverlay=vc4-kms-dsi-waveshare-panel-v2,5_0_inch_a"])

h2("Drehung/Ausrichtung: bewusst nicht konfiguriert")
p(
    "Das Panel ist nativ 720×1280 (Hochformat) - anders als das bisherige, physisch auf dem Kopf "
    "verbaute 800×480-Display wird die Ausrichtung hier über den physischen Einbau gelöst, nicht "
    "per Software. Falls sich das nach dem Einbau doch als nötig herausstellt, zwei Dinge, die "
    "beim alten Display an echter Hardware mühsam herausgefunden wurden und vermutlich weiter "
    "gelten:"
)
bullets([
    "<b>Bild selbst:</b> gehört als Kernel-Boot-Parameter in cmdline.txt (nicht config.txt!): "
    "video=DSI-1:&lt;Modus&gt;,rotate=&lt;Grad&gt;. NICHT über xrandr oder display_lcd_rotate "
    "versuchen - an echter Hardware bestätigt (beim alten Display): xrandr --output DSI-1 --rotate "
    "wird zwar anstandslos angenommen, das Panel zeichnet aber nie tatsächlich neu, selbst nach "
    "einem erzwungenen Modeset. display_lcd_rotate/lcd_rotate ist unter KMS ebenfalls wirkungslos.",
    "<b>Touch-Koordinaten:</b> bei 180° hat sich beim alten Display gezeigt, dass X11/libinput die "
    "Touch-Koordinaten am gedrehten Ausgang automatisch mitkorrigiert, zusätzlich gesetztes "
    "invx/invy hat das nochmal drübergedreht. Bei 90°/270° ist das noch nicht getestet - anders "
    "als bei 180° vertauschen 90°/270° die X/Y-Achsen, ob das automatisch mitkorrigiert wird oder "
    "invx/invy/swapxy von Hand nötig sind, muss an echter Hardware geprüft werden.",
])

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
    "owlbox-kiosk.service läuft bewusst mit niedrigerer CPU-/IO-Priorität als owlbox.service "
    "(Nice=15, IOSchedulingClass=best-effort, IOSchedulingPriority=7). Grund: Chromium läuft "
    "auf dieser Hardware komplett softwaregerendert (keine GPU-Beschleunigung verfügbar) - ohne "
    "Prioritätsdifferenz konkurrieren Chromium und mpv (läuft in owlbox.service) mit exakt "
    "gleicher Priorität um die knappe CPU eines Pi 3B+. Ein positiver Nice-Wert braucht keine "
    "besonderen Rechte - install.sh trägt das automatisch ein und startet owlbox-kiosk.service "
    "bei Bedarf neu, damit die neue Priorität auch ohne kompletten Neustart greift.",
))
story.append(note_box(
    "Hinweis für den Pi 5: Der komplette Rest dieses Abschnitts (Nice-Fix, die folgenden "
    "Korrekturen/Vermutungen zum Knacken, die entfernten Dauerschleifen) wurde ausschließlich an "
    "einem Pi 3B+ untersucht - \"die knappe CPU eines Pi 3B+\" trifft auf einen Pi 5 (deutlich "
    "schnellere CPU, zudem echte GPU-Beschleunigung für Chromium grundsätzlich möglich) so "
    "womöglich gar nicht mehr zu. Die Priorisierung selbst bleibt harmlos, ob sie auf einem Pi 5 "
    "überhaupt noch etwas bewirkt ist offen - noch nicht an echter Pi-5-Hardware verifiziert.",
    kind="warn",
))
story.append(note_box(
    "Korrektur, an echter Hardware geprüft: Dieser Nice-Fix allein hat ein durchgehendes "
    "Knacken bei Wiedergabe NICHT behoben - mit dem Fix aktiv knackte es an echter Hardware "
    "weiterhin. vcgencmd get_throttled zeigte 0x0 (keine Unterspannung/Drosselung), top zeigte "
    "im knackenden Zustand noch 62.5% CPU im Leerlauf (Load Average 0.52) und dmesg keinerlei "
    "ALSA-/I2S-Fehler - die CPU war im klassischen Sinn nie wirklich ausgelastet. Die "
    "Priorisierung bleibt trotzdem bestehen (kostet nichts), war aber nicht die vollständige "
    "Lösung. Aktuelle, noch nicht an echter Hardware verifizierte Vermutung: kontinuierliches "
    "Repaint im Kiosk selbst (unendlich laufende CSS-Animation für lange Story-Titel als "
    "Laufschrift, sowie ein setInterval alle 450ms für die VU-Meter-Balken) erzeugte auf dem "
    "softwaregerenderten Chromium regelmäßige kurze Lastspitzen, die in einer top-Momentaufnahme "
    "nicht auffallen, aber mpvs Audio-Thread gelegentlich einen Scheduling-Slot gekostet haben "
    "könnten. Beide Dauerschleifen wurden entfernt (Laufschrift durch einfaches Abschneiden mit "
    "\"...\" ersetzt, VU-Balken randomisieren nur noch einmal beim Start der Wiedergabe) - "
    "dieser Fix ist Stand jetzt noch nicht an echter Hardware getestet.",
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
        ["rfid:", "reader, reset_pin, poll_interval"],
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
    subtitle=["Vollständige Hardware-Referenz:", "Pinbelegung, DSI-Display, HiFiBerry, Netzwerk-Fallback."],
    meta_lines=["Hardware-Aufbau Raspberry Pi 5", "Schnelleinstieg: OwlBox-Schnellstart.pdf"],
)
on_page = partial(draw_header_footer, title=TITLE)

doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
print("wrote", OUT)
