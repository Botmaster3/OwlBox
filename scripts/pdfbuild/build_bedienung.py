import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[2]
from functools import partial

from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph, Spacer, PageBreak, ListFlowable, ListItem, Table, TableStyle, KeepTogether,
)

from pdf_common import (
    PAGE_W, PAGE_H, MARGIN, ACCENT, ACCENT_DARK, DARK, TEXT, MUTED, RULE, LIGHT_BG,
    S_H1, S_H2, S_H3, S_BODY, S_BODY_TIGHT, S_SMALL, S_BULLET, S_LABEL, S_MONO,
    spec_table, note_box, control_block, cover_page, draw_header_footer,
    make_toc, TocDocTemplate,
)

OUT = str(REPO_ROOT / "owlbox/web/static/docs/OwlBox-Bedienungsanleitung.pdf")
TITLE = "OwlBox – Bedienungsanleitung"

story = []


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


def ctrl(name, control_desc, effect_desc, extra=None):
    story.append(control_block(name, control_desc, effect_desc, extra))


# ============================================================ Titelseite
story.append(PageBreak())

# ============================================================ Inhalt
toc = make_toc()
story.append(Paragraph("Inhalt", S_H1))
story.append(toc)

# ============================================================ 1. Überblick
h1("1. Überblick")
p(
    "OwlBox ist eine Toniebox-ähnliche Musik-/Hörspielbox für den Raspberry Pi: ein RFID-Chip "
    "wird auf die Box gelegt, die zugehörige Geschichte startet automatisch dort, wo sie beim "
    "letzten Mal aufgehört hat. Inhalte werden bequem über eine Weboberfläche hochgeladen und "
    "einem Chip zugewiesen - eine App-Installation ist nicht nötig, jeder Browser im selben "
    "Netzwerk reicht."
)
p(
    "Diese Anleitung beschreibt <b>jede</b> Bedienmöglichkeit im Detail: alle physischen "
    "Bedienelemente am Gerät, das Kiosk-Display und jede Seite der Web-Verwaltung mitsamt jedem "
    "einzelnen Regler, Schalter und Button. Sie setzt eine bereits installierte, laufende Box "
    "voraus - für den kompletten Weg von der leeren SD-Karte bis hierhin siehe "
    "<i>OwlBox-Installation.pdf</i>, für den schnellen Einstieg danach <i>OwlBox-Schnellstart.pdf</i>, "
    "für den Hardwareaufbau <i>OwlBox-Verkabelung.pdf</i>."
)
h2("Grundprinzip")
story.append(spec_table(
    [
        ["Aktion", "Wirkung"],
        ["Bekannter Chip auflegen", "Zugehörige Playlist lädt, Wiedergabe startet ab der zuletzt gespeicherten Position."],
        ["Unbekannter Chip auflegen", "Anzeige „Unbekannter Chip“, der Scan wird geloggt und kann in der Bibliothek direkt einer Geschichte zugewiesen werden."],
        ["Chip abnehmen", "Wiedergabe läuft normal weiter - erst ein anderer Chip wechselt, was gerade läuft. Die Position wird währenddessen laufend gespeichert."],
        ["Funktions-Chip auflegen", "Löst statt einer Geschichte eine Aktion aus, z.B. Play/Pause, Lauter/Leiser, WLAN an/aus (volle Liste in Kapitel 9)."],
        ["Eltern-Chip auflegen", "Aktiviert den Eltern-Modus: Display zeigt einen QR-Code zur Login-Seite, damit Eltern sich per Handy einloggen, ohne dass Kinder Zugangsdaten sehen."],
    ],
    col_widths=[55 * mm, 105 * mm],
))

# ============================================================ 2. Erste Einrichtung
h1("2. Erste Einrichtung")
h2("2.1 Setup-Assistent")
p(
    "Beim allerersten Aufruf von <font face=\"DejaVuSansMono\" size=\"9\">/admin</font> (oder "
    "jeder anderen Verwaltungsseite) leitet OwlBox automatisch auf die Einrichtungsseite um, "
    "solange noch kein Verwaltungskonto existiert."
)
ctrl("Benutzername", "Textfeld", "Legt den Benutzernamen für den Zugriff auf die gesamte Verwaltung fest.")
ctrl("Passwort / Passwort wiederholen", "zwei Passwortfelder",
     "Beide Eingaben müssen übereinstimmen; das Passwort wird gehasht in der Datenbank gespeichert, nie im Klartext.")
p("Nach dem Absenden ist die Einrichtung abgeschlossen - jeder weitere Aufruf jeder Seite verlangt fortan diesen Login.")

h2("2.2 Login-Seite")
ctrl("Benutzername / Passwort", "Textfeld + Passwortfeld", "Klassischer Login mit den beim Setup festgelegten Zugangsdaten.")
ctrl("„Mit RFID-Chip anmelden“", "Button",
     "Startet einen Scan-Modus (Overlay „Halte den Login-Chip jetzt an die Box…“) - wird ein Eltern-Chip "
     "aufgelegt, ist die Anmeldung ohne Passworteingabe erfolgreich. „Abbrechen“ beendet den Scan-Modus wieder.",
     extra="Nur Eltern-Chips (siehe Kapitel 9.1) funktionieren hier, keine Story- oder Funktions-Chips.")

# ============================================================ 3. Physische Bedienelemente
h1("3. Physische Bedienelemente am Gerät")
p("Alle Taster und Dreh-Encoder, mit denen sich die Box bedienen lässt, ohne einen Bildschirm anzufassen.")
story.append(spec_table(
    [
        ["Element", "Kurze Aktion", "Lange Aktion"],
        ["Taster „Zurück“", "Vorheriger Track. Liefen vom aktuellen Track schon mehr als 3 Sekunden, "
         "startet er stattdessen neu von vorn.", "Gehalten (ab 0,4s): spult im aktuellen Track zurück, "
         "in 10-Sekunden-Schritten, solange der Taster gedrückt bleibt - kein Trackwechsel währenddessen."],
        ["Taster „Weiter“", "Nächster Track.", "Gehalten (ab 0,4s): spult im aktuellen Track vor, "
         "in 10-Sekunden-Schritten."],
        ["Lautstärke-Encoder, drehen", "Jede Rastung ändert die Lautstärke um die eingestellte "
         "Schrittweite (Standard 4%).", "–"],
        ["Lautstärke-Encoder, drücken", "Play/Pause umschalten.", "Ab 4 Sekunden gehalten: fährt den Pi "
         "sicher herunter - praktisch als Not-Aus ohne Terminalzugriff."],
        ["Helligkeits-Encoder, drehen", "Jede Rastung ändert die Display-Helligkeit um die eingestellte "
         "Schrittweite (Standard 5%).", "kein Taster an diesem Encoder"],
    ],
    col_widths=[38 * mm, 66 * mm, 56 * mm],
))
story.append(note_box(
    "Es gibt bewusst kein automatisches Abdimmen des Displays - die Helligkeit bleibt exakt so, wie "
    "sie zuletzt eingestellt wurde, bis sie erneut geändert wird."
))
story.append(note_box(
    "Alle Zahlenwerte (Schrittweiten, Haltezeiten) lassen sich in <font face=\"DejaVuSansMono\" "
    "size=\"9\">config.yaml</font> anpassen - siehe OwlBox-Verkabelung.pdf, Abschnitt Konfiguration."
))

# ============================================================ 4. Kiosk-Display
h1("4. Kiosk-Display (3,5″-Touchscreen)")
p(
    "Die unauthentifizierte „Jetzt läuft“-Anzeige, die im Vollbild-Kiosk-Modus permanent auf dem "
    "am Gerät verbauten Display läuft. Touch ist an diesem Aufbau bewusst deaktiviert (siehe "
    "OwlBox-Verkabelung.pdf) - die Anzeige ist reine Information, bedient wird über die physischen "
    "Elemente aus Kapitel 3 oder über die Web-Verwaltung."
)
story.append(spec_table(
    [
        ["Anzeige-Element", "Erscheint wann", "Zeigt"],
        ["Splash-Screen", "Direkt nach dem Hochfahren, bis der erste Chip erkannt wird", "Eulen-Symbol + „OwlBox“"],
        ["WLAN-Balken (oben rechts)", "Immer", "4-stufige Signalstärke-Balken + Prozentwert bzw. „Aus“/„Getrennt“"],
        ["CPU-Temperatur (oben links)", "Immer", "Aktuelle Prozessortemperatur des Pi in °C - färbt sich gelb/rot, "
         "wenn er in Richtung der automatischen Drosselschwelle (ca. 80°C) läuft"],
        ["Helligkeits-Overlay", "Kurz nach jeder Änderung am Helligkeits-Encoder", "Sonnensymbol, Balken und aktueller Prozentwert"],
        ["Hotspot-Banner", "Solange der Notfall-Hotspot aktiv ist (siehe Kapitel 10.5)", "SSID, Passwort und die Verwaltungs-URL im Hotspot"],
        ["„Jetzt läuft“-Ansicht", "Sobald ein Story-Chip aufliegt bzw. weiterläuft", "Cover, Titel, aktueller Track, VU-Meter-Animation, "
         "Fortschritt, Lautstärkebalken, die nächsten 3 kommenden Tracks"],
        ["Shuffle-/Wiederholungs-Anzeige", "Solange Shuffle bzw. Ordner-/Track-Wiederholung für die laufende "
         "Geschichte aktiv ist", "Kleine Markierungen unter dem Titel - egal ob per Funktions-Chip "
         "(Kapitel 9.2) oder über die Web-Verwaltung (Kapitel 6.2) eingeschaltet"],
        ["Einschlaf-Timer-Badge", "Solange ein Timer läuft", "Verbleibende Zeit bis zum automatischen Ausblenden/Pausieren"],
        ["„Unbekannter Chip“-Banner", "Nach dem Auflegen eines nicht zugewiesenen Chips", "Hinweis, den Chip im Admin-Bereich zuzuweisen"],
        ["Schlafmodus-Anzeige", "Nach der eingestellten Pause-Dauer im automatischen Ruhemodus (Kapitel 10.3)", "Schlafende Eule + Hinweis, wie man sie weckt"],
        ["Eltern-Modus / QR-Code", "Solange ein Eltern-Chip aufliegt", "QR-Code zur Login-Seite, damit sich Eltern per Handy einloggen können"],
    ],
    col_widths=[42 * mm, 58 * mm, 60 * mm],
))

# ============================================================ 5. Navigation
h1("5. Web-Verwaltung: Navigation")
p("Nach dem Login stehen sechs Seiten zur Verfügung, erreichbar über das Menü am oberen Seitenrand:")
bullets([
    "<b>Home</b> - reine „Jetzt läuft“-Ansicht mit allen Wiedergabe-Reglern (Kapitel 6).",
    "<b>Bibliothek</b> - alle Geschichten verwalten, Chips zuweisen, Hörstatistik (Kapitel 7).",
    "<b>Hinzufügen</b> - neue Geschichten/Livestreams anlegen (Kapitel 8).",
    "<b>RFID-Tags</b> - Eltern-Chips und Funktions-Chips verwalten (Kapitel 9).",
    "<b>Einstellungen</b> - Konto, Design, Audio, Anzeige, Netzwerk, System (Kapitel 10).",
    "<b>Info</b> - Systeminfos, Bibliotheks-Statistik, Backup, Update (Kapitel 11).",
])
p("Der Button „Abmelden“ rechts oben in der Kopfzeile beendet die angemeldete Sitzung sofort.")
story.append(note_box(
    "Der Button „Hilfe“ links daneben blendet unter jedem Regler und Eingabefeld auf allen sechs "
    "Seiten eine kurze Erklärung ein, was eine Änderung bewirkt - genau die Inhalte dieses "
    "Kapitels 6-11, direkt am jeweiligen Steuerelement. Einmal aktiviert, bleibt die Einstellung "
    "auch nach dem Navigieren zwischen Seiten erhalten, bis sie wieder ausgeschaltet wird; "
    "ausgeschaltet sieht jede Seite genauso aus wie ohne dieses Kapitel gelesen zu haben."
))

# ============================================================ 6. Home
h1("6. Web-Verwaltung: Home („Jetzt läuft“)")
p("Erste Seite nach dem Login - großformatige Wiedergabeanzeige mit direktem Zugriff auf alle Wiedergabe-Regler.")

h2("6.1 Anzeige")
bullets([
    "Cover-Bild bzw. Platzhalter-Eule, Titel der Geschichte, aktueller Track.",
    "VU-Meter (rein optische Animation, keine echte Pegelmessung, da mpv keine Live-Pegel über die "
    "Steuerverbindung liefert).",
    "Fortschrittsbalken mit verstrichener und verbleibender Zeit - anklickbar, um direkt an eine "
    "Stelle im Track zu springen (bei Livestreams ausgeblendet, da nicht spulbar).",
    "Einschlaf-Timer-Badge bzw. Schlafmodus-Hinweis, sobald aktiv.",
    "Liste kommender Tracks der aktuellen Geschichte.",
])

h2("6.2 Wiedergabe-Regler")
ctrl("Shuffle-Button", "Umschalter (aktiv/inaktiv farblich hervorgehoben)",
     "Schaltet die Zufallswiedergabe für die aktuelle Geschichte an/aus. Deaktiviert (ausgegraut), "
     "solange kein Chip mit lokalen Tracks aufliegt - bei einem Livestream gibt es nichts zu mischen.")
ctrl("„Zurück“", "Button", "Wie der physische Taster „Zurück“ (Kapitel 3): vorheriger Track bzw. Trackneustart.")
ctrl("Play/Pause-Button", "Button, wechselt Symbol/Beschriftung automatisch",
     "Zeigt ein Pause-Symbol, solange gerade etwas läuft (Klick pausiert), sonst ein Play-Symbol (Klick "
     "spielt ab) - die Beschriftung zeigt also immer die Aktion, die der nächste Klick auslöst.")
ctrl("„Weiter“", "Button", "Wie der physische Taster „Weiter“.")
ctrl("„Stop“-Button", "Button, deaktiviert solange kein Chip aufliegt",
     "Beendet die aktuelle Geschichte ganz, statt nur zu pausieren - die Anzeige geht zurück auf "
     "„Kein Chip aufgelegt“. Die Position bleibt dabei gespeichert: der nächste Start (Chip "
     "auflegen oder „Abspielen“ in der Bibliothek, Kapitel 7.2) setzt trotzdem genau dort fort.")
ctrl("Wiederholung: „Aus“ / „Ordner“ / „Track“", "Drei-Wege-Auswahl (nur eine Option gleichzeitig aktiv)",
     "„Ordner“ wiederholt die ganze Geschichte in Dauerschleife, „Track“ wiederholt nur den gerade "
     "laufenden Titel endlos, „Aus“ deaktiviert beides - die Geschichte endet dann nach dem letzten Track.",
     extra="Ebenfalls deaktiviert bei einem Livestream oder wenn gerade kein Chip aufliegt.")
ctrl("Lautstärke-Regler", "Schieberegler (0-100%)",
     "Ändert die Lautstärke sofort - technisch identisch mit dem Regler unter Einstellungen → Audio "
     "und dem Lautstärke-Encoder am Gerät; alle drei zeigen denselben Wert.")
ctrl("Helligkeits-Regler", "Schieberegler",
     "Ändert die Display-Helligkeit sofort, begrenzt auf den unter Einstellungen → Anzeige "
     "festgelegten Min/Max-Bereich.")

# ============================================================ 7. Bibliothek
h1("7. Web-Verwaltung: Bibliothek")

h2("7.1 Hörstatistik")
bullets([
    "<b>Wiedergaben insgesamt</b> - Anzahl aller bisherigen Chip-Auflegevorgänge über alle Geschichten/Streams.",
    "<b>Gesamt-Hördauer</b> - aufsummierte tatsächliche Hörzeit.",
    "Top-Liste der meistgehörten Geschichten/Streams mit jeweiliger Wiedergabezahl und Hördauer.",
])

h2("7.2 Geschichten-Liste")
ctrl("Suche", "Textfeld über der Liste", "Filtert die Liste live nach Titel (nur die Anzeige, "
     "ändert nichts an den Geschichten selbst) - hilfreich, sobald die Bibliothek zu groß für einen "
     "schnellen Überblick auf einen Blick wird.")
p("Für jede angelegte Geschichte bzw. jeden Livestream steht eine Zeile mit folgenden Elementen zur Verfügung:")
ctrl("„▶️ Abspielen“", "Button", "Startet diese Geschichte sofort, genau wie das Auflegen ihres Chips - "
     "auch wenn ihr (noch) gar kein Chip zugewiesen ist. Setzt an der zuletzt gespeicherten Position "
     "fort, egal ob diese über einen Chip-Scan oder einen früheren Klick auf „Abspielen“ zustande kam.")
ctrl("„Chip zuweisen“", "Button", "Öffnet ein Overlay „Halte den gewünschten Chip jetzt an die Box…“ - "
     "der nächste erkannte Chip wird sofort mit dieser Geschichte verknüpft. „Abbrechen“ bricht ab, ohne etwas zu ändern.")
ctrl("„Chip entfernen“", "Button (nur sichtbar, wenn ein Chip zugewiesen ist)",
     "Löst die Verknüpfung zwischen Chip und Geschichte, ohne die Geschichte selbst zu löschen.")
ctrl("„+ Weitere Tracks“", "Button (nicht bei Livestreams)", "Öffnet den Dateidialog und hängt die "
     "ausgewählten Audiodateien hinten an diese Geschichte an, statt eine neue anzulegen - praktisch "
     "für ein Hörbuch auf mehreren CDs: jede CD einzeln über diesen Button nachladen, alle Titel "
     "landen in derselben Geschichte, in der Reihenfolge des Hinzufügens weitergezählt.")
ctrl("Shuffle-Button", "Umschalter", "Identisch zum Shuffle-Button auf der Home-Seite (Kapitel 6.2), hier "
     "pro Geschichte direkt in der Liste erreichbar. Bei einem Livestream nicht vorhanden.")
ctrl("Wiederholung: „Aus“ / „Ordner“ / „Track“", "Drei-Wege-Auswahl", "Identisch zur Home-Seite - wirkt sich "
     "sofort auf die laufende Wiedergabe aus, falls diese Geschichte gerade aktiv ist.")
ctrl("„Löschen“", "Button (mit Bestätigungs-Dialog)", "Entfernt die Geschichte inklusive aller zugehörigen "
     "Audiodateien unwiderruflich.")
ctrl("Track-Liste", "Liste mit Checkbox, ▲/▼-Buttons und einem Löschen-Symbol pro Track",
     "▲/▼ verschieben einen Track in der Abspielreihenfolge. Das Löschen-Symbol entfernt ihn aus der "
     "Geschichte und löscht die Datei - auch aus jeder Playlist, die diesen Titel enthält (Kapitel 8). "
     "Die Checkbox markiert einen Titel für eine neue Playlist, auch über mehrere Geschichten hinweg "
     "kombinierbar - siehe „Auswahlleiste“ direkt im Anschluss.")

h2("7.3 Playlist direkt aus der Bibliothek erstellen")
p(
    "Alternative zum Titel-Picker auf der Hinzufügen-Seite (Kapitel 8): Titel lassen sich auch "
    "direkt hier per Checkbox auswählen, ohne die Seite zu wechseln oder etwas zu suchen."
)
ctrl("Auswahlleiste", "Leiste am unteren Bildschirmrand, erscheint automatisch sobald mindestens "
     "ein Titel angehakt ist", "Zeigt die Anzahl ausgewählter Titel. „Auswahl aufheben“ hakt alle "
     "wieder ab, ohne etwas anzulegen. „+ Playlist erstellen“ fragt nach einem Namen und erstellt "
     "sofort eine neue Geschichte aus genau den ausgewählten Titeln, in der Reihenfolge, in der sie "
     "angehakt wurden - technisch identisch zur „Playlist aus Bibliothek“ auf der Hinzufügen-Seite "
     "(Hardlink, kein doppelter Speicherbedarf).",
     extra="Die Auswahl bleibt beim Navigieren zwischen anderen Aktionen auf dieser Seite erhalten, "
     "wird aber automatisch bereinigt, falls ein ausgewählter Titel zwischenzeitlich gelöscht wurde.")

# ============================================================ 8. Hinzufügen
h1("8. Web-Verwaltung: Hinzufügen")
p("Legt eine neue Geschichte, Musiksammlung, Playlist oder einen Livestream-Chip an.")
ctrl("Quelle", "Vier-Wege-Auswahl: „Einzelne Dateien“ / „Ganzer Ordner“ / „Livestream-URL“ / "
     "„Playlist aus Bibliothek“",
     "Bestimmt, welches Eingabefeld darunter erscheint - siehe die folgenden Einträge.")
ctrl("Titel", "Textfeld (Pflichtfeld)", "Name der Geschichte, wie er später überall in der Verwaltung "
     "und auf dem Kiosk-Display erscheint.")
ctrl("Cover-Bild", "Datei-Upload (optional)", "Funktioniert in den Modi Einzelne Dateien, Ganzer "
     "Ordner und Livestream-URL. Wird kein Cover hochgeladen und ein Ordner ausgewählt, übernimmt "
     "OwlBox automatisch ein im Ordner liegendes Bild (z.B. cover.jpg), falls vorhanden. Im Modus "
     "„Playlist aus Bibliothek“ gibt es kein eigenes Cover-Feld - dort wird automatisch das Cover "
     "der Geschichte übernommen, aus der der erste ausgewählte Titel stammt (falls vorhanden).")
ctrl("Audio-Dateien", "Mehrfach-Datei-Upload (Modus „Einzelne Dateien“)",
     "Die Auswahlreihenfolge im Dateidialog bestimmt die spätere Abspielreihenfolge - nachträglich "
     "änderbar über die ▲/▼-Buttons in der Bibliothek (Kapitel 7.2).")
ctrl("Ordner", "Ordner-Upload (Modus „Ganzer Ordner“)",
     "Alle enthaltenen Audiodateien werden alphabetisch sortiert übernommen.")
ctrl("Livestream-URL", "Textfeld (Modus „Livestream-URL“)",
     "Direkte Adresse eines Audio-Streams (Internetradio o.ä.), beginnend mit http:// oder https://. "
     "Ein zugehöriger Chip verbindet beim Auflegen immer live - es gibt weder eine gespeicherte "
     "Position noch Vor-/Zurückspulen noch Shuffle/Wiederholung.")
ctrl("Titel suchen", "Suchfeld (Modus „Playlist aus Bibliothek“)",
     "Filtert die Liste darunter live nach Titel- oder Geschichtenname. Livestream-Chips tauchen "
     "hier nicht auf, da sie keine einzelnen Titel haben.")
ctrl("Verfügbare Titel / Playlist", "Liste mit „+ Hinzufügen“ je Titel, darunter eine geordnete "
     "Liste mit ▲/▼ und „Entfernen“ (Modus „Playlist aus Bibliothek“)",
     "Baut eine neue Geschichte aus bereits hochgeladenen Titeln anderer Geschichten zusammen, ohne "
     "erneutes Hochladen - die Reihenfolge in der unteren Liste ist die spätere Abspielreihenfolge. "
     "Die Originaldateien werden nicht dupliziert (Hardlink auf dieselbe Datei). Wird die "
     "Quell-Geschichte oder einzeln einer ihrer Titel später gelöscht, verschwindet der jeweilige "
     "Titel automatisch auch aus jeder Playlist, die ihn enthält - der Rest der Playlist bleibt "
     "bestehen.")
ctrl("„Anlegen“", "Button", "Lädt alles hoch bzw. verknüpft die gewählten Titel und legt die "
     "Geschichte/Playlist an. Ein Chip wird anschließend in der Bibliothek zugewiesen (Kapitel 7.2).")

# ============================================================ 9. RFID-Tags
h1("9. Web-Verwaltung: RFID-Tags")

h2("9.1 Eltern-Chips")
p(
    "Ein Chip, der beim Auflegen automatisch in die Verwaltung einloggt und auf dem Kiosk-Display "
    "einen QR-Code zur Login-Seite zeigt - Eltern können sich damit per Handy anmelden, ohne dass "
    "Kinder je den QR-Code oder die Login-Seite zu Gesicht bekommen."
)
ctrl("Bezeichnung", "Textfeld", "Freier Name zur Wiedererkennung, z.B. „Vater“ oder „Mutter“.")
ctrl("„Chip auflegen und speichern“", "Button", "Startet den Scan-Modus - der nächste erkannte Chip wird "
     "als Eltern-Chip mit der eingetragenen Bezeichnung gespeichert.")

h2("9.2 Funktions-Chips")
p(
    "Chips, die beim Auflegen eine Aktion auslösen statt eine Geschichte abzuspielen - praktisch als "
    "„Bedienkarten“, ohne einen Taster anfassen zu müssen."
)
ctrl("Aktion", "Auswahlliste", "Legt fest, welche Aktion der neue Chip auslöst - volle Liste unten.")
ctrl("„Chip auflegen und speichern“", "Button", "Startet den Scan-Modus für den gewählten Aktionstyp.")

story.append(spec_table(
    [
        ["Aktion", "Wirkung"],
        ["Play / Pause / Play/Pause umschalten", "Steuert die Wiedergabe direkt."],
        ["Weiter / Zurück", "Wie die physischen Taster (Kapitel 3)."],
        ["Lauter / Leiser", "Ändert die Lautstärke um die eingestellte Schrittweite."],
        ["WLAN an / WLAN aus", "Schaltet das WLAN-Funkmodul komplett ein/aus."],
        ["Shuffle an/aus", "Schaltet die Zufallswiedergabe der zuletzt geladenen Geschichte um - "
         "erstes Auflegen aktiviert Shuffle, Abnehmen und erneutes Auflegen desselben Chips "
         "deaktiviert es wieder."],
        ["Wiederholung Ordner an/aus", "Schaltet die Ordner-Wiederholung der zuletzt geladenen Geschichte "
         "um (gleiches Ein-/Aus-Prinzip wie Shuffle oben). Ist gerade Track-Wiederholung aktiv, "
         "wechselt dieser Chip direkt zu Ordner-Wiederholung, statt sie abzuschalten."],
        ["Wiederholung Track an/aus", "Wie oben, für die Track-Wiederholung eines einzelnen Titels."],
        ["Einschlaf-Timer 15/30/45/60 Min", "Startet einen Einschlaf-Timer mit der jeweiligen Dauer "
         "(siehe Kapitel 10.3)."],
        ["Einschlaf-Timer abbrechen", "Bricht einen laufenden Einschlaf-Timer sofort ab."],
        ["Pi neu starten / Pi herunterfahren", "Fährt den Raspberry Pi neu bzw. sicher herunter - die "
         "aktuelle Wiedergabeposition wird vorher gespeichert."],
    ],
    col_widths=[62 * mm, 98 * mm],
))
story.append(note_box(
    "Shuffle-/Wiederholungs-Chips wirken immer auf die Geschichte, die zuletzt tatsächlich geladen "
    "wurde - auch nachdem deren eigener Story-Chip schon wieder abgenommen wurde. Ohne jemals zuvor "
    "geladene Geschichte (z.B. direkt nach dem Systemstart) haben sie keine Wirkung."
))

h2("9.3 Story-Chips (Übersicht)")
p(
    "Reine Übersichtsliste, welche Geschichte an welchem Chip hängt - die Zuweisung selbst geschieht "
    "in der Bibliothek (Kapitel 7.2), hier lässt sie sich nur einsehen."
)

# ============================================================ 10. Einstellungen
h1("10. Web-Verwaltung: Einstellungen")
p("Über die Sprungleiste am oberen Seitenrand direkt zu einem Abschnitt springen: Konto, Design, "
  "Audio, Anzeige, Netzwerk, System.")

h2("10.1 Konto")
ctrl("Benutzername", "Textfeld", "Ändert den Login-Namen für die gesamte Verwaltung.")
ctrl("Neues Passwort / Wiederholen", "zwei Passwortfelder (leer lassen = unverändert)",
     "Setzt ein neues Passwort; beide Felder müssen übereinstimmen.")
ctrl("Aktuelles Passwort", "Passwortfeld (Pflicht)", "Bestätigung zur Sicherheit - ohne korrektes "
     "aktuelles Passwort wird nichts gespeichert.")

h2("10.2 Design")
p(
    "Gilt für die komplette Oberfläche - Kiosk-Anzeige genauso wie jede Verwaltungsseite. OwlBox "
    "unterscheidet drei Kategorien von Designs: die vier <b>Standard</b>-Designs (Frühling, Sommer, "
    "Herbst, Winter), <b>Sonderedition</b>-Designs zu Anlässen (Weihnachten, Ostern, Schnee, "
    "Silvester) sowie ein frei einstellbares <b>Eigenes Design</b>."
)
ctrl("Automatische Auswahl nach Datum", "Eine Checkbox pro Design",
     "Ist ein Design angehakt, wählt OwlBox es automatisch, sobald der kalendarische Zeitraum dieses "
     "Designs beginnt (z.B. Frühling ab dem 20. März) - und fällt danach automatisch auf das "
     "nächstniedrigere aktive Design bzw. den manuell gewählten Favoriten zurück. Ein abgehaktes "
     "Design wird nie automatisch gewählt, bleibt aber weiter unten manuell auswählbar.")
story.append(spec_table(
    [
        ["Design", "Kategorie", "Automatisches Zeitfenster"],
        ["Frühling", "Standard", "20. März bis 20. Juni"],
        ["Sommer", "Standard", "21. Juni bis 22. September"],
        ["Herbst", "Standard", "23. September bis 20. Dezember"],
        ["Winter", "Standard", "kein automatisches Zeitfenster (Basis-Design außerhalb der anderen Fenster)"],
        ["Weihnachten", "Sonderedition", "1. bis 26. Dezember"],
        ["Ostern", "Sonderedition", "9 Tage vor bis 1 Tag nach Ostersonntag"],
        ["Schnee", "Sonderedition", "27. Dezember bis 19. März"],
        ["Silvester", "Sonderedition", "31. Dezember bis 1. Januar"],
        ["Eigenes Design", "Eigenes Design", "kein automatisches Zeitfenster, nur manuell wählbar"],
    ],
    col_widths=[38 * mm, 40 * mm, 82 * mm],
))
ctrl("Design-Kacheln", "Klickbare Vorschau-Kacheln, gruppiert nach Kategorie",
     "Ein Klick wählt das Design sofort aus und setzt es als manuellen Favoriten - dieser gilt "
     "automatisch immer dann, wenn gerade kein automatisches Design aktiv ist.")
ctrl("Eigenes Design: Farbfelder", "Neun Farbwähler (Hintergrund, Fläche/Panel, Akzentfarbe, "
     "Akzentfarbe gedämpft, Text, Text gedämpft, Rahmen, Eingabefeld-Hintergrund, Text auf Akzentfläche)",
     "Jede der neun Grundfarben der Oberfläche ist frei wählbar - zusammen ergeben sie ein "
     "vollständig eigenes Farbschema.")
ctrl("Rundung der Balken", "Auswahlliste (0px, 4px, 6px, 8px, 10px, 999px)",
     "Bestimmt, wie stark Buttons und Leisten abgerundet sind - 999px ergibt vollständig runde "
     "(„Pill“-förmige) Elemente.")
ctrl("„Eigenes Design speichern & aktivieren“", "Button",
     "Speichert alle neun Farben plus die Balken-Rundung und aktiviert das eigene Design sofort als "
     "aktuelles Design.")

h2("10.3 Audio")
h3("Lautstärke")
ctrl("Aktuelle Lautstärke", "Schieberegler (0-100%)", "Identisch zum Regler auf der Home-Seite - ändert "
     "die Lautstärke sofort.")
ctrl("Maximale Lautstärke", "Zahlenfeld (1-100%, Standard 100)", "Obergrenze, über die die Lautstärke - "
     "egal ob per Regler, Encoder oder Funktions-Chip - nicht hinausgehen kann.")
ctrl("Schrittweite pro Tastendruck/Encoder-Schritt", "Zahlenfeld (1-50%, Standard 4)",
     "Um wie viel Prozent sich die Lautstärke bei „Lauter“/„Leiser“ (Funktions-Chip) bzw. pro Rastung "
     "des Lautstärke-Encoders ändert.")
h3("Akustisches Feedback")
ctrl("Lautstärke der Hinweistöne", "Zahlenfeld (0-100% der maximalen Lautstärke, Standard 15) + "
     "„Testen“-Button", "Legt fest, wie laut die kurzen Bestätigungstöne relativ zur maximalen "
     "Lautstärke sind - unabhängig von der gerade eingestellten Wiedergabelautstärke. „Testen“ spielt "
     "sofort mit dem aktuell eingetragenen Wert, auch ohne vorher zu speichern.")
ctrl("Welche Töne sollen abgespielt werden?", "Fünf Checkboxen mit je einem „▶ Testen“-Button "
     "(Chip erkannt, Unbekannter Chip, Funktions-Chip, Hochfahren, Herunterfahren/Neustart)",
     "Jeder Ereignistyp lässt sich einzeln stummschalten, ohne die anderen zu beeinflussen.")
ctrl("„Speichern“", "Button", "Speichert Lautstärke und aktivierte Töne.")
story.append(note_box(
    "Hinweistöne laufen über aplay parallel zur laufenden Geschichte und unterbrechen sie nicht - "
    "dafür wird alsa-utils sowie idealerweise ALSA-dmix benötigt (sonst ggf. stumm, falls das "
    "Audiogerät gerade exklusiv von mpv belegt ist)."
))
h3("Automatischer Ruhemodus")
ctrl("Nach dieser Pause-Dauer schläft die Eule ein", "Zahlenfeld in Minuten (0-480, 0 = aus, Standard 20)",
     "Greift, sobald eine Geschichte pausiert ist - egal ob über Play/Pause-Taste/-Chip oder weil die "
     "Lautstärke auf 0 gedreht wurde. Aufwecken (Track läuft an derselben Stelle weiter): Lautstärke "
     "erhöhen, Play/Pause drücken oder einen beliebigen RFID-Chip auflegen.")
h3("Einschlaf-Timer")
ctrl("Schnellauswahl 15/30/45/60 Min", "vier Buttons", "Startet sofort einen Timer mit der gewählten Dauer.")
ctrl("Eigene Dauer", "Zahlenfeld in Minuten (1-480) + „Timer starten“-Button",
     "Startet einen Timer mit frei gewählter Länge.")
ctrl("„Timer abbrechen“", "Button (nur sichtbar bei laufendem Timer)", "Bricht den aktiven Timer sofort ab.")
story.append(note_box(
    "In den letzten 60 Sekunden vor Ablauf blendet der Timer die Lautstärke sanft aus, statt hart "
    "abzuschneiden (einstellbar über config.yaml → playback.sleep_fade_seconds, 0 = sofortige "
    "Hart-Pause)."
))

h2("10.4 Anzeige")
ctrl("Helligkeit", "Schieberegler (0-100%)", "Identisch zum Regler auf der Home-Seite.")
ctrl("Minimale Helligkeit", "Zahlenfeld (0-99%, Standard 0)", "Untere Grenze für den Regler und den "
     "Helligkeits-Encoder.")
ctrl("Maximale Helligkeit", "Zahlenfeld (1-100%, Standard 100)", "Obere Grenze für Regler und Encoder.")
ctrl("Schrittweite pro Tastendruck/Encoder-Schritt", "Zahlenfeld (1-50%, Standard 5)",
     "Änderung pro Rastung des Helligkeits-Encoders.")
story.append(note_box(
    "Die Helligkeit wird ausschließlich manuell geregelt (Regler hier oder Helligkeits-Encoder am "
    "Gerät) - es gibt kein automatisches Dimmen. Der Regler braucht die Hintergrundbeleuchtung auf "
    "einem eigenen GPIO statt fest an 3,3V verdrahtet (siehe OwlBox-Verkabelung.pdf) - ohne diese "
    "Verkabelung bleibt er ohne sichtbare Wirkung."
))

h2("10.5 Netzwerk (WLAN)")
ctrl("WLAN an/aus", "Umschalter-Button", "Schaltet das WLAN-Funkmodul komplett ein/aus.")
ctrl("„Netzwerke suchen“", "Button", "Scannt nach WLAN-Netzwerken in Reichweite und zeigt sie als Liste "
     "zur Auswahl an.")
ctrl("Passwort-Feld + „Verbinden“", "Passwortfeld + Button (erscheint nach Auswahl eines Netzwerks)",
     "Verbindet mit dem gewählten Netzwerk.")
ctrl("Bekannte Netzwerke", "Liste bereits einmal verbundener Zugangspunkte",
     "Erlaubt, ohne erneute Passworteingabe zu einem früher genutzten Netzwerk zu wechseln oder es "
     "aus der Liste zu entfernen.")
story.append(note_box(
    "Ist WLAN eingeschaltet, aber länger als 60 Sekunden mit keinem Netzwerk verbunden, spannt der Pi "
    "automatisch einen eigenen Notfall-Hotspot auf (Standard-SSID „OwlBox-Setup“) - Name/Passwort "
    "werden dann auf dem Kiosk-Display und hier oben als Banner angezeigt. Sobald eine echte "
    "Verbindung klappt, beendet sich der Hotspot von selbst.",
))
story.append(note_box(
    "Das voreingestellte Hotspot-Passwort steht offen im Quellcode und ist damit öffentlich bekannt - "
    "für den Einsatz dort, wo Fremde in Funkreichweite kommen könnten, unbedingt ein eigenes Passwort "
    "in config.yaml setzen.",
    kind="warn",
))

h2("10.6 System")
ctrl("„Pi neu starten“", "Button", "Startet den Raspberry Pi neu - die aktuelle Wiedergabeposition wird "
     "vorher automatisch gespeichert.")
ctrl("„Pi herunterfahren“", "Button", "Fährt den Raspberry Pi sicher herunter.")

# ============================================================ 11. Info
h1("11. Web-Verwaltung: Info")
h2("11.1 Gerät")
p("Hardware-Bezeichnung, Betriebssystem, Laufzeit seit dem letzten Start sowie ein Balken für die "
  "aktuelle CPU-Temperatur.")
h2("11.2 Speicher")
p("Zwei Balken für die Belegung des Datenträgers (Medien-Verzeichnis) sowie des Arbeitsspeichers.")
h2("11.3 Bibliothek")
p("Drei Kacheln: Anzahl Geschichten, Anzahl Titel insgesamt, Anzahl mit einem Chip verknüpfter Geschichten.")
h2("11.4 Wochenrückblick")
p("Kurze Zusammenfassung der Hörgewohnheiten der letzten sieben Tage inklusive der meistgehörten Titel.")
h2("11.5 Software")
p("Aktuelle OwlBox-Version samt Datum des zugehörigen Software-Stands („Installiert am“) sowie "
  "Betriebsmodus (Normalbetrieb oder Simulationsmodus ohne echte Hardware).")
h2("11.6 Wartung")
ctrl("„Backup herunterladen“", "Link/Download", "Lädt Datenbank plus alle Mediendateien als ZIP herunter - "
     "die einzige Möglichkeit, die Bibliothek wiederherzustellen, falls die SD-Karte einmal ausfällt.")
ctrl("„Nach Updates suchen“", "Button", "Prüft per git fetch, ob eine neuere Version im Repository "
     "verfügbar ist - läuft automatisch beim Öffnen dieser Seite und lässt sich hier jederzeit "
     "erneut anstoßen. Ändert nichts am installierten Stand, zeigt nur, ob es etwas Neues gibt. Wird "
     "keine neuere Version gefunden, meldet die Seite ausdrücklich, dass bereits die aktuellste "
     "Version installiert ist (samt Versionsnummer und Datum).")
ctrl("„Update installieren“", "Button (erscheint nur, wenn ein Update gefunden wurde)",
     "Holt den neuen Softwarestand per git pull, installiert bei Bedarf neue Abhängigkeiten und "
     "startet danach nur den OwlBox-Dienst neu (nicht den ganzen Pi). Erscheint erst nach einer "
     "positiven Prüfung und wird nur auf ausdrücklichen Klick hin ausgeführt.")
h2("11.7 Dokumentation")
p("Direkter Download-Zugriff auf alle drei Dokumente, die auch dieser PDF-Datei beiliegen: "
  "Schnellstart, diese Bedienungsanleitung sowie die Verkabelungsreferenz.")

# ============================================================ 12. Fehlerbehebung
h1("12. Fehlerbehebung")
story.append(spec_table(
    [
        ["Problem", "Lösungsansatz"],
        ["Chip wird nicht erkannt", "Nur passive 13,56-MHz-MIFARE-Chips werden unterstützt; Chip muss "
         "flach auf dem markierten Lesebereich liegen. Siehe auch OwlBox-Verkabelung.pdf, RC522-Verkabelung."],
        ["Kein Ton", "Lautstärke unter Einstellungen → Audio prüfen; ALSA-Gerät/Mixer in config.yaml "
         "gegen aplay -L / amixer scontrols abgleichen (OwlBox-Verkabelung.pdf)."],
        ["Display bleibt schwarz", "fbcp-Dienst prüfen (systemctl status owlbox-fbcp), legacy "
         "Grafiktreiber statt Wayland aktiv? Kiosk-Dienst prüfen (systemctl status owlbox-kiosk). "
         "Siehe OwlBox-Verkabelung.pdf."],
        ["Verwaltung im Browser nicht erreichbar", "IP-Adresse erneut prüfen; auf dem Kiosk-Display "
         "nachsehen, ob gerade der Notfall-Hotspot aktiv ist (Kapitel 10.5)."],
        ["Helligkeitsregler ohne Wirkung", "Backlight-Pin in config.yaml (gpio.backlight_pin) muss "
         "gesetzt und der Treibertransistor verkabelt sein - siehe OwlBox-Verkabelung.pdf."],
        ["Passwort vergessen", "Auf dem Pi direkt: Datenbankdatei (data/owlbox.db) sichern, Tabelle "
         "admin_user leeren und den Server neu starten - der Setup-Assistent (Kapitel 2.1) erscheint dann erneut."],
    ],
    col_widths=[52 * mm, 108 * mm],
))

# ---------------------------------------------------------------- build
doc = TocDocTemplate(
    OUT, pagesize=(PAGE_W, PAGE_H),
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22 * mm, bottomMargin=20 * mm,
    title="OwlBox Bedienungsanleitung", author="OwlBox",
)

on_cover = partial(
    cover_page,
    kicker="OWLBOX",
    title=["Bedienungsanleitung"],
    subtitle=["Jede Seite, jeder Regler, jedes Bedienelement -", "vom physischen Taster bis zum Farbeditor."],
    meta_lines=["Vollständiges Benutzerhandbuch", "Schnelleinstieg: OwlBox-Schnellstart.pdf"],
)
on_page = partial(draw_header_footer, title=TITLE)

doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
print("wrote", OUT)
