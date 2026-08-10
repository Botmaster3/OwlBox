import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[2]
from functools import partial

from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem,
)
from reportlab.lib import colors

from pdf_common import (
    PAGE_W, PAGE_H, MARGIN, ACCENT, ACCENT_DARK, DARK, TEXT, MUTED, RULE, LIGHT_BG,
    S_H1, S_H2, S_H3, S_BODY, S_BODY_TIGHT, S_SMALL, S_BULLET, S_LABEL, S_MONO,
    spec_table, note_box, cover_page, draw_header_footer,
)

OUT = str(REPO_ROOT / "owlbox/web/static/docs/OwlBox-Schnellstart.pdf")
TITLE = "OwlBox – Schnellstart"

story = []


def h1(t):
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


def step(number, title, text):
    num = Table([[Paragraph(str(number), S_LABEL)]], colWidths=[9 * mm], rowHeights=[9 * mm])
    num.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ROUNDEDCORNERS", [5, 5, 5, 5]),
    ]))
    text_cell = [Paragraph(title, S_H3), Paragraph(text, S_BODY)]
    row = Table([[num, text_cell]], colWidths=[13 * mm, PAGE_W - 2 * MARGIN - 13 * mm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(row)


# ---------------------------------------------------------------- cover
story.append(PageBreak())

h1("Was du brauchst")
p(
    "Diese Anleitung bringt eine fertig verkabelte, mit installierter Software laufende OwlBox "
    "in wenigen Minuten zum Laufen. Steht noch keine SD-Karte mit Raspberry Pi OS bereit oder ist "
    "die Software noch nicht installiert, siehe stattdessen zuerst <i>OwlBox-Installation.pdf</i> "
    "(kompletter Weg von der leeren SD-Karte bis hierhin) bzw. <i>OwlBox-Verkabelung.pdf</i> für "
    "den reinen Hardwareaufbau."
)
bullets([
    "Fertig verkabelte OwlBox (Raspberry Pi + Verstärker/Lautsprecher + RFID-Leser + Display), an Strom angeschlossen.",
    "Der Pi ist im selben WLAN/Netzwerk wie dein Handy, Tablet oder Laptop, oder per Netzwerkkabel verbunden.",
    "Ein Gerät mit Webbrowser zur Ersteinrichtung (Handy reicht).",
    "Mindestens eine Audiodatei oder ein Ordner mit Hörspiel-/Musikdateien (MP3, OGG, FLAC, WAV, ...).",
    "Ein oder mehrere leere RFID-Chips/-Karten (13,56 MHz, MIFARE-kompatibel), die dem RC522-Leser beiliegen oder separat erhältlich sind.",
])

h1("In 6 Schritten startklar")

step(1, "Box einschalten",
     "Netzteil anschließen. Auf dem Display erscheint kurz ein Eulen-Startbildschirm, "
     "danach die Anzeige „Kein Chip aufgelegt“ - die Box ist betriebsbereit.")

step(2, "Verwaltung im Browser öffnen",
     "IP-Adresse des Pi im Netzwerk herausfinden (z.B. am Router nachsehen oder "
     "<font face=\"DejaVuSansMono\" size=\"9\">hostname -I</font> direkt am Pi) und "
     "<font face=\"DejaVuSansMono\" size=\"9\">http://&lt;pi-ip&gt;:5000/admin</font> aufrufen. "
     "Beim allerersten Aufruf fragt OwlBox nach einem Benutzernamen und einem Passwort für die "
     "Verwaltung - das ab jetzt für jeden Zugriff nötig ist. Kein WLAN in Reichweite? Der Pi "
     "spannt nach kurzer Zeit automatisch einen eigenen Notfall-Hotspot auf (Name/Passwort stehen "
     "dann auf dem Display), über den die Verwaltung ebenfalls erreichbar ist.")

step(3, "Erste Geschichte hochladen",
     "Menüpunkt „Hinzufügen“ öffnen, Titel eintragen, entweder einzelne Audiodateien oder gleich "
     "einen ganzen Ordner auswählen (ein darin liegendes Cover-Bild wird automatisch übernommen). "
     "„Anlegen“ klicken.")

step(4, "Chip zuweisen",
     "In der „Bibliothek“ bei der neuen Geschichte auf „Chip zuweisen“ klicken und den "
     "gewünschten RFID-Chip an den Leser halten - die Zuordnung ist sofort gespeichert.")

step(5, "Auflegen und hören",
     "Chip auf die Box legen: die Wiedergabe startet automatisch. Chip wieder abnehmen "
     "unterbricht nichts - die Geschichte läuft weiter, nur die Position wird laufend "
     "gemerkt, sodass beim nächsten Auflegen genau dort weitergeht.")

step(6, "Lautstärke und Helligkeit einstellen",
     "Am Gerät: den Dreh-Encoder drehen (Lautstärke) bzw. drücken (Play/Pause), den zweiten "
     "Encoder für die Helligkeit des Displays. Aus der Ferne: in der Verwaltung unter "
     "„Einstellungen“ per Schieberegler.")

story.append(note_box(
    "Alle Details zu jedem einzelnen Regler, jeder Seite der Verwaltung und allen physischen "
    "Bedienelementen stehen in <i>OwlBox-Bedienungsanleitung.pdf</i>. Für den kompletten "
    "Hardware-Aufbau (Verkabelung aller Bauteile) siehe <i>OwlBox-Verkabelung.pdf</i>.",
))

h2("Die wichtigsten Bedienelemente direkt am Gerät")
story.append(spec_table(
    [
        ["Bedienelement", "Kurz drücken/drehen", "Lang halten"],
        ["Taster „Zurück“", "Vorheriger Track (oder Trackneustart, wenn schon > 3s liefen)", "Zurückspulen, solange gehalten"],
        ["Taster „Weiter“", "Nächster Track", "Vorspulen, solange gehalten"],
        ["Lautstärke-Encoder (drehen)", "Lautstärke rauf/runter", "–"],
        ["Lautstärke-Encoder (drücken)", "Play/Pause umschalten", "≥ 4s: Pi sicher herunterfahren"],
        ["Helligkeits-Encoder (drehen)", "Display-Helligkeit rauf/runter", "–"],
    ],
    col_widths=[45 * mm, 65 * mm, 45 * mm],
))

h2("Typische erste Stolpersteine")
bullets([
    "<b>Chip wird nicht erkannt:</b> Chip muss ein passiver 13,56-MHz-MIFARE-Typ sein (Karte oder "
    "Schlüsselanhänger) und flach auf dem markierten Lesebereich aufliegen.",
    "<b>Kein Ton:</b> unter Einstellungen → Audio die Lautstärke prüfen, sowie in "
    "<font face=\"DejaVuSansMono\" size=\"9\">config.yaml</font> das richtige ALSA-Gerät "
    "(siehe OwlBox-Verkabelung.pdf).",
    "<b>Display bleibt schwarz/Touch reagiert nicht:</b> normal - Touch ist bei diesem Aufbau "
    "bewusst deaktiviert, die Bedienung läuft über Taster/Encoder bzw. die Verwaltung im Browser.",
    "<b>Verwaltung nicht erreichbar:</b> IP-Adresse erneut prüfen, oder auf dem Display nachsehen, "
    "ob gerade der Notfall-Hotspot aktiv ist (Banner mit WLAN-Namen/Passwort).",
])

doc = SimpleDocTemplate(
    OUT, pagesize=(PAGE_W, PAGE_H),
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22 * mm, bottomMargin=20 * mm,
    title="OwlBox Schnellstart", author="OwlBox",
)

on_cover = partial(
    cover_page,
    kicker="OWLBOX",
    title=["Schnellstart"],
    subtitle=["In sechs Schritten von der verkabelten Box", "zur ersten laufenden Geschichte."],
    meta_lines=["Kurzanleitung", "Ausführliche Details: OwlBox-Bedienungsanleitung.pdf"],
)
on_page = partial(draw_header_footer, title=TITLE)

doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
print("wrote", OUT)
