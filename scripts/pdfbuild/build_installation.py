import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).resolve().parent / "assets"
from functools import partial

from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, PageBreak, ListFlowable, ListItem,
)

from pdf_common import (
    PAGE_W, PAGE_H, MARGIN, ACCENT, ACCENT_DARK, DARK, TEXT, MUTED, RULE, LIGHT_BG,
    S_H1, S_H2, S_H3, S_BODY, S_BODY_TIGHT, S_SMALL, S_BULLET, S_LABEL, S_MONO,
    spec_table, note_box, cover_page, draw_header_footer,
    make_toc, TocDocTemplate, style,
    imager_window_mockup, imager_settings_mockup, terminal_mockup, browser_mockup,
    screenshot,
)

OUT = str(REPO_ROOT / "owlbox/web/static/docs/OwlBox-Installation.pdf")
TITLE = "OwlBox – Installation"

story = []
S_CODE_BLOCK = style("CodeBlock", fontName="DejaVuSansMono", fontSize=8.3, leading=12,
                      textColor=ACCENT_DARK, spaceAfter=6, leftIndent=8)


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


def step(number, title, *paragraphs):
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
    cell = [Paragraph(title, S_H3)] + [Paragraph(t, S_BODY) for t in paragraphs]
    row = Table([[num, cell]], colWidths=[13 * mm, PAGE_W - 2 * MARGIN - 13 * mm])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(row)


# ============================================================ Titelseite
story.append(PageBreak())

# ============================================================ Inhalt
toc = make_toc()
story.append(Paragraph("Inhalt", S_H1))
story.append(toc)

# ============================================================ 1. Voraussetzungen
h1("1. Was du brauchst")
h2("1.1 Hardware")
bullets([
    "Raspberry Pi 3B+",
    "microSD-Karte, mindestens 8 GB (16 GB oder mehr empfohlen), Class 10",
    "Passendes Netzteil (5V/2,5A für den Pi selbst; bei aktivem HiFiBerry-Verstärker eher 5V/3A)",
    "HiFiBerry Amp (I2S-Verstärker-HAT) + Lautsprecher",
    "RC522 RFID-Modul + mindestens ein RFID-Chip/-Karte (13,56 MHz, MIFARE-kompatibel)",
    "3,5″ SPI-Touchscreen, 480×320 (tft35a/MHS-35-Familie)",
    "2 Taster, 2 Dreh-Encoder (KY-040), 1 Transistor/MOSFET fürs Backlight-Dimmen - siehe "
    "OwlBox-Verkabelung.pdf für die genaue Bauteilliste",
    "PC oder Laptop mit SD-Kartenleser (zum Beschreiben der SD-Karte)",
    "Netzwerkkabel oder WLAN-Zugang für den Pi",
])
h2("1.2 Software (auf deinem PC)")
bullets([
    "Raspberry Pi Imager (kostenlos, für Windows/macOS/Linux) - "
    "<font face=\"DejaVuSansMono\" size=\"9\">raspberrypi.com/software</font>",
    "Ein SSH-fähiges Terminal (unter Windows z.B. die Windows Terminal App oder PuTTY, unter "
    "macOS/Linux das eingebaute Terminal)",
])
story.append(note_box(
    "Diese Anleitung führt vom leeren Raspberry Pi bis zur fertig eingerichteten, laufenden "
    "OwlBox. Für die reine Bedienung danach siehe OwlBox-Schnellstart.pdf und "
    "OwlBox-Bedienungsanleitung.pdf, für die komplette Verkabelungsreferenz "
    "OwlBox-Verkabelung.pdf - hierhin wird an den passenden Stellen verwiesen."
))

# ============================================================ 2. OS flashen
h1("2. Raspberry Pi OS auf die SD-Karte flashen")
p(
    "Raspberry Pi Imager herunterladen und installieren, SD-Karte in den PC stecken, Imager "
    "öffnen."
)
story.append(note_box(
    "Die Screenshots in diesem Kapitel zeigen den echten Raspberry Pi Imager. Hostname, "
    "Benutzername, Passwort und WLAN-Daten sind frei gewählte Beispielwerte zur Illustration - "
    "beim eigenen Durchlauf hier die eigenen Werte eintragen."
))
story.append(screenshot(str(ASSETS / "imager-main-window.png"),
                         "Der Raspberry Pi Imager nach dem Start."))
step(1, "Gerät wählen", "„CHOOSE DEVICE“ → Raspberry Pi 3.")
story.append(imager_window_mockup("device"))
step(2, "Betriebssystem wählen",
     "„CHOOSE OS“ → „Raspberry Pi OS (other)“ → <b>„Raspberry Pi OS (Legacy) Lite“</b>.",
     "Diese Variante basiert auf demselben aktuellen Debian Bookworm wie die Standard-Variante "
     "und bringt den alten Grafiktreiber statt Wayland/labwc mit - das braucht später <font "
     "face=\"DejaVuSansMono\" size=\"9\">fbcp</font> fürs SPI-Display (siehe Kapitel 6). Bewusst "
     "„Lite“ statt der vollen Desktop-Variante: OwlBox "
     "startet für den Kiosk selbst nur ein minimales X ohne Desktop-Umgebung (kein lightdm/LXDE) - "
     "„Lite“ bringt so eine Desktop-Umgebung gar nicht erst mit, die beim Boot nur unnötig Zeit "
     "kosten würde, ohne dass sie je zu sehen wäre.")
story.append(screenshot(str(ASSETS / "imager-os-list.png"),
                         "„CHOOSE OS“ - die oberste Auswahlebene."))
story.append(screenshot(str(ASSETS / "imager-os-legacy.png"),
                         "Nach Klick auf „Raspberry Pi OS (other)“ - hier „Raspberry Pi OS "
                         "(Legacy) Lite“ auswählen (weiter unten in der Liste)."))
story.append(screenshot(str(ASSETS / "imager-os-lite-selected.png"),
                         "„Raspberry Pi OS (Legacy) Lite“ ausgewählt."))
step(3, "Speicherziel wählen", "„CHOOSE STORAGE“ → die eingelegte SD-Karte auswählen. "
     "Vorsicht: alles darauf wird überschrieben.")
story.append(imager_window_mockup("storage"))
step(4, "Anpassungen vornehmen",
     "Nach Klick auf „NEXT“ fragt der Imager „Would you like to apply OS customisation "
     "settings?“ - <b>„EDIT SETTINGS“</b> wählen (bei älteren Imager-Versionen stattdessen vorher "
     "auf das Zahnrad-Symbol bzw. Strg+Umschalt+X klicken). Dort einstellen:")
bullets([
    "<b>Hostname</b>: z.B. „owlbox“ (damit später <font face=\"DejaVuSansMono\" size=\"9\">"
    "owlbox.local</font> statt einer IP-Adresse erreichbar ist)",
    "<b>Benutzername und Passwort</b> für den Pi selbst festlegen (nicht zu verwechseln mit dem "
    "OwlBox-Verwaltungslogin, das später separat im Browser eingerichtet wird)",
    "<b>WLAN konfigurieren</b> (SSID, Passwort, Land) - bei Netzwerkkabel diesen Punkt überspringen",
    "<b>SSH aktivieren</b> (Passwort-Authentifizierung reicht für den Einstieg)",
    "Zeitzone und Tastaturlayout passend setzen",
])
story.append(screenshot(str(ASSETS / "imager-settings-general.png"),
                         "Reiter „GENERAL“ - Hostname, Benutzer/Passwort und WLAN "
                         "(Beispielwerte)."))
story.append(screenshot(str(ASSETS / "imager-settings-services.png"),
                         "Reiter „SERVICES“ - SSH mit Passwort-Authentifizierung aktivieren."))
step(5, "Schreiben", "„SAVE“, dann „YES“/„WRITE“ bestätigen. Der Vorgang dauert je nach "
     "Kartengröße/-geschwindigkeit einige Minuten (Schreiben + Verifizieren). Danach die SD-Karte "
     "sicher auswerfen.")

# ============================================================ 3. Erster Start
h1("3. Erster Start und Verbindung zum Pi")
p(
    "SD-Karte in den Pi einsetzen. Für die allererste Inbetriebnahme reicht Strom + Netzwerk - "
    "die restliche Hardware (HiFiBerry, Display, RC522, Taster/Encoder) kommt erst in Kapitel 5 "
    "dazu, wenn die Software-Grundlage steht."
)
p(
    "Nach ca. 1-2 Minuten (erster Boot dauert etwas länger als spätere) per SSH verbinden. "
    "Funktioniert der Hostname nicht, stattdessen die IP-Adresse verwenden (z.B. aus der "
    "Router-Oberfläche abgelesen). System danach einmal komplett aktualisieren und neu starten:"
)
story.append(terminal_mockup("Terminal - ssh pi@owlbox.local", [
    (True, "ssh pi@owlbox.local"),
    (False, "pi@owlbox.local's password:"),
    (False, "Linux owlbox 6.12 ..."),
    (True, "sudo apt update && sudo apt full-upgrade -y"),
    (True, "sudo reboot"),
]))
story.append(note_box(
    "Falls owlbox.local nicht gefunden wird: manche Router/Netzwerke unterstützen mDNS "
    "(.local-Namen) nicht. Dann die IP-Adresse des Pi direkt verwenden - am Router nachsehen oder, "
    "falls ein Bildschirm+Tastatur direkt am Pi angeschlossen ist, dort <font "
    "face=\"DejaVuSansMono\" size=\"9\">hostname -I</font> ausführen."
))

# ============================================================ 4. Grundeinstellungen
h1("4. Grundeinstellungen prüfen")
p(
    "scripts/install.sh aktiviert SPI später automatisch - dieser Schritt ist nur zur Kontrolle "
    "bzw. für alle, die lieber vorher schon alles an einer Stelle einstellen:"
)
code(["sudo raspi-config"])
bullets([
    "<b>Interface Options → SPI → Enable</b> (für den RC522-RFID-Leser und das Display - falls "
    "hier schon „Enabled“ steht, ist nichts weiter zu tun).",
    "<b>Advanced Options → GL Driver</b>: sollte bei der „Legacy“-Variante aus Kapitel 2 bereits "
    "passend stehen; falls dort „OpenGL (Full KMS)“ oder „OpenGL (Fake KMS)“ ausgewählt ist, auf "
    "„Legacy“ umstellen - wichtig für das SPI-Display in Kapitel 6.",
    "Hostname/Zeitzone/Tastaturlayout, falls beim Flashen in Kapitel 2 nicht schon gesetzt.",
])
p("Menü mit „Finish“ verlassen, bei Aufforderung neu starten.")

# ============================================================ 5. Hardware verkabeln
h1("5. Hardware verkabeln")
p(
    "Jetzt den Pi <b>vom Strom trennen</b> und die komplette restliche Hardware verkabeln: "
    "HiFiBerry Amp (direkt aufgesteckt), RC522-RFID-Leser, beide Taster, beide Dreh-Encoder, "
    "Display (per Jumperkabeln, nicht aufgesteckt - Steckplatzkollision mit dem HiFiBerry) samt "
    "Backlight-Transistor."
)
story.append(note_box(
    "Die komplette, detaillierte Verkabelung (jeder Pin, jedes Bauteil, inkl. Schaltplan-Grafiken) "
    "steht in <b>OwlBox-Verkabelung.pdf</b> - diese Anleitung hier wiederholt sie bewusst nicht, "
    "um nicht an zwei Stellen unterschiedlich aktuell zu sein. Erst weiterlesen, wenn die Hardware "
    "fertig verkabelt ist."
))
p("Danach den Pi wieder mit Strom versorgen und erneut per SSH verbinden.")

# ============================================================ 6. Software installieren
h1("6. OwlBox-Software installieren")
h2("6.1 Code herunterladen")
story.append(terminal_mockup("Terminal - Code herunterladen", [
    (True, "git clone https://github.com/Botmaster3/owlbox.git"),
    (True, "cd owlbox"),
]))
h2("6.2 Installationsskript ausführen (1. Durchlauf)")
story.append(terminal_mockup("Terminal - 1. Durchlauf", [
    (True, "sudo ./scripts/install.sh"),
    (False, "[*] Installiere Systempakete ..."),
    (False, "[*] Baue fbcp ..."),
    (False, "[*] Starte Display-Treiber-Installer ..."),
    (False, "[*] Neustart erforderlich - starte neu ..."),
]))
p(
    "Für die in Kapitel 1 gelistete Standardhardware (HiFiBerry Amp/Amp2, 3,5″-SPI-Touchdisplay "
    "der tft35a/MHS-35-Familie) automatisiert das Skript inzwischen praktisch alles, was früher "
    "von Hand nachgetragen werden musste. Im ersten Durchlauf erledigt es:"
)
bullets([
    "Benötigte System-Pakete installieren (Python, mpv, alsa-utils, git, Chromium, cmake, "
    "libraspberrypi-dev, ein minimaler X-Stack für den Kiosk, ...)",
    "SPI aktivieren",
    "Ungenutzte Dienste und Boot-Wartezeiten abschalten, um den Bootvorgang zu verkürzen",
    "Einen eigenen Service-User „owlbox“ anlegen (mit Zugriff auf gpio/spi/audio/video/i2c)",
    "Die Anwendung nach <font face=\"DejaVuSansMono\" size=\"9\">/opt/owlbox</font> kopieren, eine "
    "Python-virtuelle-Umgebung anlegen und alle Abhängigkeiten installieren",
    "<font face=\"DejaVuSansMono\" size=\"9\">config/config.yaml</font> aus der Vorlage anlegen, "
    "falls noch nicht vorhanden",
    "HiFiBerry-Overlay (<font face=\"DejaVuSansMono\" size=\"9\">dtoverlay=hifiberry-amp</font>) "
    "und GL-Treiber (Legacy statt KMS/Fake-KMS) in config.txt eintragen",
    "<font face=\"DejaVuSansMono\" size=\"9\">fbcp</font> aus dem Quellcode bauen und installieren",
    "Den Display-Treiber-Installer (goodtft/LCD-show) automatisch herunterladen und starten - "
    "dieser bootet den Pi am Ende meist selbst neu",
])
story.append(note_box(
    "Läuft der Neustart nicht automatisch an, meldet das Skript das am Ende deutlich - dann "
    "einmal von Hand <font face=\"DejaVuSansMono\" size=\"9\">sudo reboot</font> ausführen. Auch "
    "wenn nur config.txt geändert wurde, fordert das Skript zu einem Neustart auf, bevor der "
    "zweite Durchlauf sinnvoll ist."
))
story.append(note_box(
    "Was konkret abgeschaltet wird: die Dienste bluetooth, hciuart, triggerhappy, ModemManager "
    "und dphys-swapfile (auf dieser Box ungenutzt), der Text-Login auf tty1 (der Kiosk übernimmt "
    "dieses Terminal direkt), das Warten auf eine Netzwerkverbindung beim Boot sowie der "
    "Boot-Splash-Bildschirm. Alles reine Boot-Zeit-Optimierungen ohne Funktionsverlust für OwlBox."
))
h2("6.3 Installationsskript erneut ausführen (2. Durchlauf, nach dem Neustart)")
p("Nach dem Neustart erneut per SSH verbinden und das Skript noch einmal starten:")
story.append(terminal_mockup("Terminal - 2. Durchlauf", [
    (True, "cd owlbox"),
    (True, "sudo ./scripts/install.sh"),
    (False, "[*] Erkenne ALSA-Gerät ... hw:0,0"),
    (False, "[*] Richte Kiosk-Autostart ein ..."),
    (False, "[OK] Alles eingerichtet."),
]))
p("Jetzt ist die Hardware aktiv, deshalb erledigt das Skript in diesem Durchlauf zusätzlich:")
bullets([
    "Das aktive ALSA-Gerät und den passenden Mixer-Namen automatisch erkennen (aplay -l / "
    "amixer scontrols) und in config.yaml eintragen",
    "Die vom Display-Installer gesetzte Touch-Zeile (dtoverlay=ads7846,...) wieder aus "
    "config.txt entfernen - Touch bleibt bei diesem Aufbau bewusst deaktiviert",
    "Den Kiosk-Autostart einrichten und aktivieren: ein eigener systemd-Dienst "
    "(<font face=\"DejaVuSansMono\" size=\"9\">owlbox-kiosk.service</font>) startet X direkt "
    "(kein Desktop, kein Login-Bildschirm) und darin Chromium im Vollbild",
    "Den systemd-Dienst <font face=\"DejaVuSansMono\" size=\"9\">owlbox.service</font> "
    "installieren, aktivieren und starten",
])
p(
    "Ist alles fertig, meldet das Skript das explizit. Bleibt danach noch eine Meldung zu einem "
    "weiteren nötigen Neustart übrig, das Skript einfach ein drittes Mal laufen lassen - es ist "
    "beliebig oft gefahrlos wiederholbar und bricht nichts, wenn ein Schritt schon erledigt ist."
)
story.append(note_box(
    "Abweichende Hardware (anderes HiFiBerry-Modell, anderes Display, kein Display)? Dann bitte "
    "OwlBox-Verkabelung.pdf zurate ziehen - dort steht jeder Schritt, den das Skript für die "
    "Standardhardware automatisch erledigt, einzeln zum manuellen Nachvollziehen und Anpassen."
))
story.append(note_box(
    "Mit <font face=\"DejaVuSansMono\" size=\"9\">sudo systemctl status owlbox</font> lässt sich "
    "jederzeit prüfen, ob der Dienst sauber läuft; <font face=\"DejaVuSansMono\" size=\"9\">"
    "sudo journalctl -u owlbox -f</font> zeigt die Logs live an, falls etwas nicht wie erwartet "
    "aussieht."
))

# ============================================================ 7. Erste Einrichtung
h1("7. Erste Einrichtung im Browser")
step(1, "IP-Adresse ermitteln",
     "Direkt am Pi: <font face=\"DejaVuSansMono\" size=\"9\">hostname -I</font>. Oder am Router "
     "nachsehen. Oder den Hostnamen aus Kapitel 2 verwenden.")
step(2, "Verwaltung öffnen",
     "Mit einem beliebigen Gerät im selben Netzwerk (Handy reicht) im Browser <font "
     "face=\"DejaVuSansMono\" size=\"9\">http://&lt;pi-ip-oder-hostname&gt;:5000/admin</font> "
     "aufrufen.")
step(3, "Setup-Assistent durchlaufen",
     "Beim allerersten Aufruf fragt OwlBox nach Benutzername und Passwort für die Verwaltung - "
     "das gilt ab jetzt für jeden Zugriff.")
story.append(browser_mockup(
    "http://owlbox.local:5000/admin",
    "OwlBox einrichten",
    ["Benutzername", "Passwort", "Passwort bestätigen"],
    "Konto anlegen",
))
story.append(note_box(
    "Kein WLAN in Reichweite bzw. die Verbindung klappt nicht? Der Pi spannt nach kurzer Zeit "
    "automatisch einen eigenen Notfall-Hotspot auf (Standard-SSID „OwlBox-Setup“), über den die "
    "Verwaltung ebenfalls erreichbar ist - siehe OwlBox-Bedienungsanleitung.pdf, Kapitel 10.5."
))

# ============================================================ 8. Erste Geschichte
h1("8. Erste Geschichte anlegen und Chip zuweisen")
p(
    "Unter „Hinzufügen“ Titel vergeben und Audiodateien bzw. einen Ordner hochladen, dann in der "
    "„Bibliothek“ bei dieser Geschichte auf „Chip zuweisen“ klicken und einen RFID-Chip an den "
    "Leser halten. Chip auf die Box legen - die Wiedergabe startet automatisch."
)
story.append(note_box(
    "Diese sechs Schritte im Detail (mit Screenshots der Bedienelemente) stehen in "
    "OwlBox-Schnellstart.pdf."
))

# ============================================================ 9. Fertig
h1("9. Fertig - wie geht es weiter?")
bullets([
    "<b>OwlBox-Schnellstart.pdf</b> - die ersten Schritte im Alltag, kompakt auf drei Seiten.",
    "<b>OwlBox-Bedienungsanleitung.pdf</b> - jede Seite der Verwaltung und jeder physische Taster "
    "einzeln erklärt, inkl. der Design-Themes und aller Funktions-Chip-Aktionen.",
    "<b>OwlBox-Verkabelung.pdf</b> - vollständige Hardware-Referenz für spätere Änderungen oder "
    "Fehlersuche an der Verkabelung.",
])
p(
    "Alle drei PDFs stehen außerdem jederzeit direkt in der Verwaltung unter Info → Dokumentation "
    "zum Download bereit."
)

# ============================================================ 10. Fehlerbehebung
h1("10. Fehlerbehebung bei der Installation")
story.append(spec_table(
    [
        ["Problem", "Lösungsansatz"],
        ["SD-Karte wird vom Imager nicht erkannt", "Anderen Kartenleser/USB-Anschluss probieren; "
         "Karte in einem anderen Gerät auf Schreibschutz/Defekt prüfen."],
        ["owlbox.local nicht erreichbar", "IP-Adresse stattdessen verwenden (Router-Oberfläche "
         "oder Bildschirm+Tastatur direkt am Pi mit hostname -I)."],
        ["SSH-Verbindung wird abgelehnt", "Prüfen, ob SSH beim Flashen (Kapitel 2, Schritt 4) "
         "wirklich aktiviert wurde; Benutzername/Passwort exakt wie beim Flashen vergeben "
         "verwenden."],
        ["apt update/full-upgrade bricht ab", "Netzwerkverbindung des Pi prüfen (WLAN-Zugangsdaten "
         "korrekt? Kabel eingesteckt?); erneut versuchen, manche Spiegelserver sind kurzzeitig "
         "überlastet."],
        ["scripts/install.sh bricht ab", "Fehlermeldung genau lesen - meist ein fehlendes "
         "Netzwerkpaket oder fehlende Root-Rechte (mit sudo ausführen). Skript ist mehrfach "
         "gefahrlos wiederholbar."],
        ["systemctl status owlbox zeigt „failed“", "sudo journalctl -u owlbox -n 50 für die "
         "letzten Log-Zeilen; scripts/install.sh ein weiteres Mal ausführen - meist fehlt nur "
         "der zweite Durchlauf nach einem Neustart (Kapitel 6)."],
        ["Kein Ton", "aplay -l zeigt die HiFiBerry-Karte erst nach einem Neustart mit aktivem "
         "Overlay; danach scripts/install.sh erneut ausführen, das trägt ALSA-Gerät und Mixer "
         "automatisch in config.yaml ein (Kapitel 6). Bleibt es stumm, HiFiBerry-Overlay in "
         "config.txt und Verkabelung prüfen."],
        ["Display bleibt schwarz", "sudo systemctl status owlbox-fbcp prüfen; GL-Driver wirklich "
         "auf „Legacy“ (Kapitel 4); scripts/install.sh noch einmal ausführen, falls der "
         "Display-Treiber-Installer noch nicht durchgelaufen ist (Kapitel 6)."],
        ["Display zeigt nur einen Textcursor/Login, kein Chromium",
         "sudo systemctl status owlbox-kiosk prüfen; sudo journalctl -u owlbox-kiosk -n 50 für "
         "die Fehlermeldung von X/Chromium; Xwrapper.config wurde von scripts/install.sh unter "
         "/etc/X11/Xwrapper.config angelegt - prüfen, ob die Datei noch existiert."],
        ["Verwaltung im Browser nicht erreichbar", "IP-Adresse erneut prüfen; auf dem Kiosk-Display "
         "nachsehen, ob gerade der Notfall-Hotspot aktiv ist (Kapitel 7)."],
    ],
    col_widths=[55 * mm, 105 * mm],
))

# ---------------------------------------------------------------- build
doc = TocDocTemplate(
    OUT, pagesize=(PAGE_W, PAGE_H),
    leftMargin=MARGIN, rightMargin=MARGIN, topMargin=22 * mm, bottomMargin=20 * mm,
    title="OwlBox Installation", author="OwlBox",
)

on_cover = partial(
    cover_page,
    kicker="OWLBOX",
    title=["Installation"],
    subtitle=["Vom leeren Raspberry Pi bis zur fertig", "eingerichteten, laufenden OwlBox."],
    meta_lines=["Komplette Installationsanleitung", "Danach: OwlBox-Schnellstart.pdf"],
)
on_page = partial(draw_header_footer, title=TITLE)

doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
print("wrote", OUT)
