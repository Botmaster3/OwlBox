import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[2]
from functools import partial

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, PageBreak, ListFlowable, ListItem

from pdf_common import (
    PAGE_W, PAGE_H, MARGIN, ACCENT_DARK,
    S_H1, S_H2, S_BODY, S_BULLET,
    spec_table, note_box, cover_page, draw_header_footer,
    make_toc, TocDocTemplate,
)

OUT = str(REPO_ROOT / "owlbox/web/static/docs/OwlBox-Komponenten.pdf")
TITLE = "OwlBox – Komponenten"

story = []


def h1(t):
    story.append(PageBreak())
    story.append(Paragraph(t, S_H1))


def h2(t):
    story.append(Paragraph(t, S_H2))


def p(t, style=S_BODY):
    story.append(Paragraph(t, style))


def bullets(items, style=S_BULLET):
    story.append(ListFlowable(
        [ListItem(Paragraph(i, style), bulletColor=ACCENT_DARK) for i in items],
        bulletType="bullet", start="•", leftIndent=14,
    ))
    story.append(Spacer(1, 6))


def parts_table(rows):
    story.append(spec_table(
        [["Bauteil", "Spezifikation", "Menge"]] + rows,
        col_widths=[60 * mm, 88 * mm, 22 * mm],
    ))
    story.append(Spacer(1, 4))


# ============================================================ Titelseite
story.append(PageBreak())

# ============================================================ Inhalt
toc = make_toc()
story.append(Paragraph("Inhalt", S_H1))
story.append(toc)

story.append(note_box(
    "Diese Liste ergänzt OwlBox-Verkabelung.pdf und die Grafik docs/owlbox-gpio-pinout.svg "
    "(bzw. OwlBox-GPIO-Pinout.pdf) - dort steht, WIE alles verdrahtet wird, hier steht, WAS "
    "dafür beschafft werden muss. Angaben zu Typ/Menge/Spezifikation, bewusst ohne Preise oder "
    "konkrete Händlerlinks - die schwanken zu schnell, um sie in einem Dokument zu pflegen. Bei "
    "allen mit „Noch nicht an echter Hardware verifiziert“ markierten Positionen gilt "
    "dieselbe Einschränkung wie in docs/hardware.md: vor dem Kauf gegen das jeweilige Datenblatt "
    "prüfen."
))

# ============================================================ 1. Zentraleinheit
h1("1. Zentraleinheit")
parts_table([
    ["Raspberry Pi 5 (4GB)", "Quad-Core Cortex-A76, 40-Pin-GPIO-Header, DSI- und CSI-Anschluss. "
     "Ersetzt das früher verbaute Pi 3B+.", "1×"],
    ["GeeekPi Low-Profile Plus CPU Cooler", "Aluminium-Kühlkörper mit Lüfter, steckt auf den "
     "eigenen 4-Pin-JST-Lüfteranschluss des Pi 5 (kein GPIO, keine config.txt-Zeile nötig).", "1×"],
    ["USB-C-PD-Netzteil", "5V/5A (27W, offizielles Raspberry-Pi-Netzteil empfohlen) - ein "
     "schwächeres 5V/2,5-3A-Netzteil reicht bei Amp2 unter Last plus Lüfter nicht sicher aus.", "1×"],
    ["microSD-Karte", "Mind. 16GB, empfohlen 32GB+, Class 10 / A2 für flüssiges Booten und die "
     "Hörspiel-/Spiele-Bibliothek.", "1×"],
])
story.append(note_box(
    "Kein separates Gehäuse in dieser Liste - die Box ist ein Eigenbau-Gehäuse um die "
    "Lautsprecher/das Display herum, keine Standard-Pi-Hülle."
))

# ============================================================ 2. Audio
h1("2. Audio")
parts_table([
    ["HiFiBerry Amp2", "I2S-Verstärker-HAT, TAS5756M-Chip, Class-D, 2× Kanal. Sitzt wegen des "
     "Kühlkörpers nicht mehr direkt auf dem 40-Pin-Header, sondern hängt per Jumperkabel an der "
     "Adapter-Platine (s. Kapitel 5).", "1×"],
    ["Passivlautsprecher", "Impedanz/Belastbarkeit gegen das Amp2-Datenblatt prüfen (typ. 4-8Ω). "
     "Geometrie (Durchmesser/Abstand) bestimmt die Frontplatten-Aussparungen, siehe "
     "docs/owlbox-gpio-pinout.svg-Umfeld/CAD-Vorlage.", "2×"],
    ["Lautsprecherkabel, 2-adrig", "Querschnitt ≥ 0,75mm² / AWG18 (reicht für 15W/4Ω); bei "
     "Kabelwegen über 3-5m eher 1,0-1,5mm² nehmen. Für die Federklemmen des Amp2, kein Cinch/"
     "Klinke.", "nach Bedarf"],
])

# ============================================================ 3. Display
h1("3. Display")
story.append(note_box(
    "Dieser Abschnitt ist noch NICHT an echter Hardware verifiziert (siehe docs/hardware.md).",
    kind="warn",
))
parts_table([
    ["Waveshare 5″ DSI Capacitive Touch Display", "Modell 5-DSI-TOUCH-A, 720×1280, kapazitiver "
     "Touch, Aluminiumgehäuse. Bild+Touch über eigenes DSI-Flachbandkabel (Lieferumfang), "
     "zusätzlich 4 Jumperkabel für Strom/I2C (s.u.).", "1×"],
    ["Jumperkabel, Dupont female-female", "Für Display-Strom (5V, GND) und I2C-Touch (SDA, SCL) "
     "zwischen Display-Adapterplatine und Pi-GPIO-Header.", "4×"],
])

# ============================================================ 4. RFID
h1("4. RFID")
parts_table([
    ["RC522-Modul", "SPI-RFID-Leser, 13,56 MHz, läuft am Pi über Hardware-SPI0/CE0.", "1×"],
    ["Jumperkabel, Dupont female-female", "Für SPI (SCLK/MOSI/MISO/CE0), RST und 3,3V/GND - "
     "VCC ausdrücklich an 3,3V, nicht 5V.", "7×"],
    ["RFID-Chips/Tags", "13,56 MHz, Mifare-kompatibel (Karte, Sticker oder Schlüsselanhänger) - "
     "je ein Chip pro Hörspiel/Funktion, plus optional je einer pro Nutzer-Login.", "nach Bedarf"],
])

# ============================================================ 5. Bedienelemente
h1("5. Bedienelemente")
parts_table([
    ["Taster (Cherry MX oder kompatibel)", "3-Pin-Bauform, nur 2 Metallpins aktiv genutzt - "
     "vor/zurück.", "2×"],
    ["KY-040 Dreh-Encoder-Modul, mit Druckschalter", "Lautstärke/Play-Pause; langer Druck fährt "
     "den Pi sicher herunter.", "1×"],
    ["KY-040 Dreh-Encoder-Modul, mit Druckschalter", "Helligkeit; Druckschalter schaltet den "
     "Nachtmodus um.", "1×"],
])

# ============================================================ 6. Verkabelung / Adapter-Platine
h1("6. Verkabelung & Adapter-Platine")
parts_table([
    ["Lochraster-Platine", "Trägt die 40-Pin-Buchsenleiste für den Amp2 plus die "
     "Jumperkabel-Anschlüsse für RC522/Taster/Encoder - eigenverdrahtet, kein fertiges Produkt.", "1×"],
    ["40-Pin-Buchsenleiste (2×20, 2,54mm), zum Auflöten", "Nimmt den Amp2 als vollständiges "
     "40-Pin-HAT auf - anders als RC522/Taster/Encoder lässt sich der Amp2 nicht einzeln per "
     "Jumperkabel verdrahten.", "1×"],
    ["Jumperkabel, Dupont male-female", "Verbindet die 40-Pin-Buchsenleiste der Adapter-Platine "
     "mit dem 40-Pin-Header des Pi.", "40×"],
    ["Litze, AWG20 oder dicker (für 5V/GND des Amp2)", "Der Amp2 zieht seine komplette "
     "Lautsprecher-Ausgangsleistung direkt aus der 5V-Schiene (Class-D) - bei Zimmerlautstärke "
     "durchaus über 1A. Dünne Standard-Jumperkabel sind dafür nicht ausgelegt.", "kurz, je 2×"],
])
story.append(note_box(
    "Nach dem Zusammenbau prüfen: vcgencmd get_throttled sollte 0x0 zeigen (keine "
    "Unterspannung) - bei Verzerren/Aussetzern unter Last zuerst hier ansetzen."
))

# ============================================================ 7. Werkzeug (optional)
h1("7. Werkzeug (nicht Teil der Stückliste, aber sinnvoll)")
bullets([
    "Lötkolben + Lötzinn (für die 40-Pin-Buchsenleiste auf der Adapter-Platine)",
    "Abisolierzange (für die Lautsprecher- und Netzteil-Adern)",
    "Multimeter (Polaritäts-/Kurzschlussprüfung vor dem ersten Einschalten)",
    "microSD-Kartenleser (zum Flashen des OS-Images, falls nicht schon vorhanden)",
])

# ---------------------------------------------------------------- build
doc = TocDocTemplate(
    OUT, pagesize=(PAGE_W, PAGE_H),
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22 * mm, bottomMargin=20 * mm,
    title="OwlBox Komponenten", author="OwlBox",
)

on_cover = partial(
    cover_page,
    kicker="OWLBOX",
    title=["Komponenten"],
    subtitle=["Stückliste zur Hardware-Referenz:", "was beschafft werden muss, bevor verdrahtet wird."],
    meta_lines=["Hardware-Aufbau Raspberry Pi 5", "Siehe auch: OwlBox-Verkabelung.pdf, OwlBox-GPIO-Pinout.pdf"],
)
on_page = partial(draw_header_footer, title=TITLE)

doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
print("wrote", OUT)
