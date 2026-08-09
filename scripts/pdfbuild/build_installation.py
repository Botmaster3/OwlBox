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
    imager_window_mockup, terminal_mockup, browser_mockup,
    screenshot_with_chrome,
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


def mono(t):
    return f"<font face=\"DejaVuSansMono\" size=\"9\">{t}</font>"


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
    "HiFiBerry Amp2 (I2S-Verstärker-HAT) + Lautsprecher",
    "RC522 RFID-Modul + mindestens ein RFID-Chip/-Karte (13,56 MHz, MIFARE-kompatibel)",
    "Offizielles Raspberry Pi 7″ Touch Display (DSI, erste Generation)",
    "2 Taster, 2 Dreh-Encoder (KY-040) - siehe OwlBox-Verkabelung.pdf für die genaue Bauteilliste",
    "PC oder Laptop mit SD-Kartenleser (zum Beschreiben der SD-Karte) - Windows, macOS oder Linux",
    "Netzwerkkabel oder WLAN-Zugang für den Pi",
])
h2("1.2 Software (auf deinem PC)")
bullets([
    "Raspberry Pi Imager (kostenlos, für Windows/macOS/Linux) - " + mono("raspberrypi.com/software"),
    "Ein SSH-fähiges Terminal (bei allen drei Betriebssystemen bereits eingebaut bzw. mit "
    "Bordmitteln nachrüstbar - Details dazu jeweils im passenden Kapitel)",
])
story.append(note_box(
    "Diese Anleitung führt vom leeren Raspberry Pi bis zur fertig eingerichteten, laufenden "
    "OwlBox. Die Kapitel 2, 3 und 4 enthalten dafür die komplette Anleitung gleich dreimal - "
    "einmal für Windows, einmal für macOS und einmal für Linux, jeweils vollständig und "
    "in sich abgeschlossen. Einfach das passende Kapitel wählen und von vorn bis hinten "
    "durcharbeiten, ohne zwischendurch etwas anderswo nachschlagen zu müssen. Für die reine "
    "Bedienung danach siehe OwlBox-Schnellstart.pdf und OwlBox-Bedienungsanleitung.pdf, für die "
    "komplette Verkabelungsreferenz OwlBox-Verkabelung.pdf - hierhin wird an den passenden "
    "Stellen verwiesen."
))


# ============================================================ Gemeinsamer Aufbau für die drei
# Betriebssystem-Kapitel (Windows / macOS / Linux) - bewusst als eine Funktion, die dreimal mit
# unterschiedlichen Parametern aufgerufen wird, statt dreimal von Hand ausformuliert: so bleiben
# alle drei Fassungen garantiert inhaltsgleich, nur die paar echten Unterschiede (Imager-Installation,
# Terminal-App, Tastenkombination, SD-Karte auswerfen) wandern als Parameter durch.
def install_section(n, os_name, imager_steps, shortcut, terminal_name, terminal_open, eject_hint,
                     app_name, os_key):
    h1(f"{n}. Installation unter {os_name}")
    p(
        f"Vollständige Schritt-für-Schritt-Anleitung für {os_name} - von der leeren SD-Karte bis "
        "zur fertig eingerichteten, laufenden OwlBox. Dieser Abschnitt wiederholt bewusst alles "
        "noch einmal komplett (auch wenn du schon eines der anderen Betriebssysteme "
        "durchgearbeitet hast) - nichts muss anderswo nachgeschlagen werden."
    )

    # -- X.1 Imager installieren --------------------------------------------
    h2(f"{n}.1 Raspberry Pi Imager installieren")
    for i, (title, *paras) in enumerate(imager_steps, start=1):
        step(i, title, *paras)

    # -- X.2 OS flashen -------------------------------------------------------
    h2(f"{n}.2 Raspberry Pi OS auf die SD-Karte flashen")
    p("Raspberry Pi Imager öffnen, SD-Karte in den PC stecken.")
    story.append(note_box(
        "Die Screenshots in diesem Kapitel zeigen die echte Bedienoberfläche des Raspberry Pi "
        "Imager - die ist auf allen drei Betriebssystemen identisch, nur der Fensterrahmen "
        f"drumherum sieht unter {os_name} anders aus (hier entsprechend nachgebildet). "
        "Hostname, Benutzername, Passwort und WLAN-Daten sind frei gewählte Beispielwerte zur "
        "Illustration - beim eigenen Durchlauf hier die eigenen Werte eintragen."
    ))
    story.append(screenshot_with_chrome(str(ASSETS / "imager-main-window.png"), os_key,
                                         "Der Raspberry Pi Imager nach dem Start.",
                                         app_title="Raspberry Pi Imager"))
    step(1, "Gerät wählen", "„CHOOSE DEVICE“ → Raspberry Pi 3.")
    story.append(imager_window_mockup("device", os_key))
    step(2, "Betriebssystem wählen",
         "„CHOOSE OS“ → direkt in der obersten Liste <b>„Raspberry Pi OS Lite (64-bit)“</b> "
         "auswählen (nicht die volle Variante mit Desktop-Umgebung, und nicht „(other)“/„Legacy“ "
         "nötig).",
         "Diese Variante ist Debian Bookworm mit dem modernen KMS-Grafiktreiber (Standard, bleibt "
         f"aktiv - das Display braucht dafür keinen extra Treiber, siehe {n}.6), aber bewusst ohne "
         "Desktop-Umgebung: OwlBox startet für den Kiosk selbst nur ein minimales X "
         "(kein lightdm/LXDE) - „Lite“ bringt so eine Desktop-Umgebung gar nicht erst mit, die "
         "beim Boot nur unnötig Zeit kosten würde, ohne dass sie je zu sehen wäre.")
    story.append(screenshot_with_chrome(str(ASSETS / "imager-os-list.png"), os_key,
                                         "„CHOOSE OS“ - „Raspberry Pi OS Lite (64-bit)“ steht "
                                         "bereits in der obersten Auswahlebene.",
                                         app_title="Operating System"))
    story.append(imager_window_mockup("os", os_key))
    step(3, "Speicherziel wählen", "„CHOOSE STORAGE“ → die eingelegte SD-Karte auswählen. "
         "Vorsicht: alles darauf wird überschrieben.")
    story.append(imager_window_mockup("storage", os_key))
    step(4, "Anpassungen vornehmen",
         "Nach Klick auf „NEXT“ fragt der Imager „Would you like to apply OS customisation "
         "settings?“ - <b>„EDIT SETTINGS“</b> wählen (bei älteren Imager-Versionen stattdessen "
         f"vorher auf das Zahnrad-Symbol bzw. {shortcut} klicken). Dort einstellen:")
    bullets([
        "<b>Hostname</b>: z.B. „owlbox“ (damit später " + mono("owlbox.local") +
        " statt einer IP-Adresse erreichbar ist)",
        "<b>Benutzername und Passwort</b> für den Pi selbst festlegen (nicht zu verwechseln mit "
        "dem OwlBox-Verwaltungslogin, das später separat im Browser eingerichtet wird)",
        "<b>WLAN konfigurieren</b> (SSID, Passwort, Land) - bei Netzwerkkabel diesen Punkt "
        "überspringen",
        "<b>SSH aktivieren</b> (Passwort-Authentifizierung reicht für den Einstieg)",
        "Zeitzone und Tastaturlayout passend setzen",
    ])
    story.append(screenshot_with_chrome(str(ASSETS / "imager-settings-general.png"), os_key,
                                         "Reiter „GENERAL“ - Hostname, Benutzer/Passwort und "
                                         "WLAN (Beispielwerte).",
                                         app_title="OS Customization"))
    story.append(screenshot_with_chrome(str(ASSETS / "imager-settings-services.png"), os_key,
                                         "Reiter „SERVICES“ - SSH mit "
                                         "Passwort-Authentifizierung aktivieren.",
                                         app_title="OS Customization"))
    step(5, "Schreiben", "„SAVE“, dann „YES“/„WRITE“ bestätigen. Der Vorgang dauert je nach "
         "Kartengröße/-geschwindigkeit einige Minuten (Schreiben + Verifizieren). Danach die "
         f"SD-Karte sicher auswerfen ({eject_hint}).")

    # -- X.3 Erster Start -------------------------------------------------------
    h2(f"{n}.3 Erster Start und Verbindung zum Pi")
    p(
        "SD-Karte in den Pi einsetzen. Für die allererste Inbetriebnahme reicht Strom + "
        "Netzwerk - die restliche Hardware (HiFiBerry, Display, RC522, Taster/Encoder) kommt "
        f"erst in {n}.5 dazu, wenn die Software-Grundlage steht."
    )
    p(
        f"Nach ca. 1-2 Minuten (erster Boot dauert etwas länger als spätere) {terminal_open} "
        "öffnen und per SSH verbinden. Funktioniert der Hostname nicht, stattdessen die "
        "IP-Adresse verwenden (z.B. aus der Router-Oberfläche abgelesen). Raspberry Pi OS Lite "
        "bringt git nicht von Haus aus mit - gleich mit installieren, dann das System einmal "
        "komplett aktualisieren und neu starten:"
    )
    story.append(terminal_mockup(app_name, [
        (True, "ssh pi@owlbox.local"),
        (False, "pi@owlbox.local's password:"),
        (False, "Linux owlbox 6.12 ..."),
        (True, "sudo apt update"),
        (True, "sudo apt install -y git"),
        (True, "sudo apt full-upgrade -y"),
        (True, "sudo reboot"),
    ], os_key=os_key))
    p("Zum Abtippen bzw. Kopieren, Zeile für Zeile:")
    code([
        "ssh pi@owlbox.local",
        "sudo apt update",
        "sudo apt install -y git",
        "sudo apt full-upgrade -y",
        "sudo reboot",
    ])
    story.append(note_box(
        "Falls owlbox.local nicht gefunden wird: manche Router/Netzwerke unterstützen mDNS "
        "(.local-Namen) nicht. Dann die IP-Adresse des Pi direkt verwenden - am Router "
        "nachsehen oder, falls ein Bildschirm+Tastatur direkt am Pi angeschlossen ist, dort " +
        mono("hostname -I") + " ausführen."
    ))
    story.append(note_box(
        f"Kein SSH-Client zur Hand? Empfohlen wird {terminal_name}."
    ))

    # -- X.4 Grundeinstellungen -------------------------------------------------
    h2(f"{n}.4 Grundeinstellungen prüfen")
    p(
        "Dieser Schritt ist optional - nur für alle, die Hostname/Zeitzone/Tastaturlayout nicht "
        f"schon beim Flashen in {n}.2 gesetzt haben:"
    )
    code(["sudo raspi-config"])
    p("Menü mit „Finish“ verlassen, bei Aufforderung neu starten.")

    # -- X.5 Hardware verkabeln --------------------------------------------------
    h2(f"{n}.5 Hardware verkabeln")
    p(
        "Jetzt den Pi <b>vom Strom trennen</b> und die komplette restliche Hardware verkabeln: "
        "HiFiBerry Amp2 (direkt aufgesteckt), RC522-RFID-Leser, beide Taster, beide "
        "Dreh-Encoder sowie das 7″-Touch-Display - per DSI-Flachbandkabel am eigenen "
        "DSI-Steckplatz (kein Konflikt mit dem HiFiBerry, keine Steckplatzkollision) plus 4 "
        "Jumperkabel für Strom und Touch-I2C."
    )
    story.append(note_box(
        "Die komplette, detaillierte Verkabelung (jeder Pin, jedes Bauteil, inkl. "
        "Schaltplan-Grafiken) steht in <b>OwlBox-Verkabelung.pdf</b> - diese Anleitung hier "
        "wiederholt sie bewusst nicht, um nicht an zwei Stellen unterschiedlich aktuell zu "
        "sein. Erst weiterlesen, wenn die Hardware fertig verkabelt ist."
    ))
    p("Danach den Pi wieder mit Strom versorgen und erneut per SSH verbinden.")

    # -- X.6 Software installieren ------------------------------------------------
    h2(f"{n}.6 OwlBox-Software installieren")
    h3(f"{n}.6.1 Code herunterladen")
    story.append(terminal_mockup(app_name, [
        (True, "git clone https://github.com/Botmaster3/owlbox.git"),
        (True, "cd owlbox"),
    ], os_key=os_key))
    p("Zum Abtippen bzw. Kopieren:")
    code([
        "git clone https://github.com/Botmaster3/owlbox.git",
        "cd owlbox",
    ])
    h3(f"{n}.6.2 Installationsskript ausführen (1. Durchlauf)")
    story.append(terminal_mockup(app_name, [
        (True, "sudo ./scripts/install.sh"),
        (False, "[*] Installiere Systempakete ..."),
        (False, "[*] Aktiviere SPI/I2C ..."),
        (False, "[*] Trage HiFiBerry- und Display-Overlay in config.txt ein ..."),
        (False, "[*] Neustart erforderlich - starte neu ..."),
    ], os_key=os_key))
    p("Zum Abtippen bzw. Kopieren:")
    code(["sudo ./scripts/install.sh"])
    p(
        "Für die in Kapitel 1 gelistete Standardhardware (HiFiBerry Amp2, offizielles "
        "7″-Touch-Display) automatisiert das Skript inzwischen praktisch alles, was früher von "
        "Hand nachgetragen werden musste. Im ersten Durchlauf erledigt es:"
    )
    bullets([
        "Benötigte System-Pakete installieren (Python, mpv, alsa-utils, git, Chromium, ein "
        "minimaler X-Stack für den Kiosk, ...)",
        "SPI (für den RC522) und I2C aktivieren",
        "Ungenutzte Dienste und Boot-Wartezeiten abschalten, um den Bootvorgang zu verkürzen",
        "Einen eigenen Service-User „owlbox“ anlegen (mit Zugriff auf gpio/spi/audio/video/i2c)",
        "Die Anwendung nach " + mono("/opt/owlbox") + " kopieren, eine "
        "Python-virtuelle-Umgebung anlegen und alle Abhängigkeiten installieren",
        mono("config/config.yaml") + " aus der Vorlage anlegen, falls noch nicht vorhanden",
        "HiFiBerry-Overlay (" + mono("dtoverlay=hifiberry-dacplus") + ", passend zum "
        "TAS5756M-Chip des Amp2) sowie den Grafiktreiber-Overlay (" +
        mono("dtoverlay=vc4-kms-v3d,noaudio") + " plus " + mono("dtoverlay=vc4-kms-dsi-7inch") +
        " fürs Display) in config.txt eintragen - das Display selbst braucht keinen separaten "
        "Treiber-Installer",
        "Den Pi am Ende automatisch neu starten",
    ])
    story.append(note_box(
        "Meldet das Skript am Ende trotzdem, dass ein Neustart noch aussteht (z.B. weil der "
        "automatische Neustart fehlgeschlagen ist): einmal von Hand " + mono("sudo reboot") +
        " ausführen, bevor der zweite Durchlauf sinnvoll ist."
    ))
    story.append(note_box(
        "Was konkret abgeschaltet wird: die Dienste bluetooth, hciuart, triggerhappy, "
        "ModemManager und dphys-swapfile (auf dieser Box ungenutzt), der Text-Login auf tty1 "
        "(der Kiosk übernimmt dieses Terminal direkt), das Warten auf eine Netzwerkverbindung "
        "beim Boot sowie der Boot-Splash-Bildschirm. Alles reine Boot-Zeit-Optimierungen ohne "
        "Funktionsverlust für OwlBox."
    ))
    h3(f"{n}.6.3 Installationsskript erneut ausführen (2. Durchlauf, nach dem Neustart)")
    p("Nach dem Neustart erneut per SSH verbinden und das Skript noch einmal starten:")
    story.append(terminal_mockup(app_name, [
        (True, "cd owlbox"),
        (True, "sudo ./scripts/install.sh"),
        (False, "[*] Erkenne ALSA-Gerät ... hw:0,0"),
        (False, "[*] Richte Kiosk-Autostart ein ..."),
        (False, "[OK] Alles eingerichtet."),
    ], os_key=os_key))
    p("Zum Abtippen bzw. Kopieren:")
    code([
        "cd owlbox",
        "sudo ./scripts/install.sh",
    ])
    p("Jetzt ist die Hardware aktiv, deshalb erledigt das Skript in diesem Durchlauf "
      "zusätzlich:")
    bullets([
        "Das aktive ALSA-Gerät und den passenden Mixer-Namen automatisch erkennen (aplay -l / "
        "amixer scontrols) und in config.yaml eintragen",
        "Den Kiosk-Autostart einrichten und aktivieren: ein eigener systemd-Dienst "
        "(" + mono("owlbox-kiosk.service") + ") startet X direkt (kein Desktop, kein "
        "Login-Bildschirm) und darin Chromium im Vollbild",
        "Den systemd-Dienst " + mono("owlbox.service") + " installieren, aktivieren und "
        "starten",
    ])
    p(
        "Ist alles fertig, meldet das Skript das explizit. Bleibt danach noch eine Meldung zu "
        "einem weiteren nötigen Neustart übrig, das Skript einfach ein drittes Mal laufen "
        "lassen - es ist beliebig oft gefahrlos wiederholbar und bricht nichts, wenn ein "
        "Schritt schon erledigt ist."
    )
    story.append(note_box(
        "Abweichende Hardware (anderes HiFiBerry-Modell, anderes Display, kein Display)? Dann "
        "bitte OwlBox-Verkabelung.pdf zurate ziehen - dort steht jeder Schritt, den das Skript "
        "für die Standardhardware automatisch erledigt, einzeln zum manuellen Nachvollziehen "
        "und Anpassen."
    ))
    story.append(note_box(
        "Mit " + mono("sudo systemctl status owlbox") + " lässt sich jederzeit prüfen, ob der "
        "Dienst sauber läuft; " + mono("sudo journalctl -u owlbox -f") + " zeigt die Logs live "
        "an, falls etwas nicht wie erwartet aussieht."
    ))

    # -- X.7 Browser-Einrichtung -----------------------------------------------
    h2(f"{n}.7 Erste Einrichtung im Browser")
    step(1, "IP-Adresse ermitteln",
         "Direkt am Pi: " + mono("hostname -I") + f". Oder am Router nachsehen. Oder den "
         f"Hostnamen aus {n}.2 verwenden.")
    step(2, "Verwaltung öffnen",
         "Mit einem beliebigen Gerät im selben Netzwerk (Handy reicht) im Browser " +
         mono("http://&lt;pi-ip-oder-hostname&gt;:5000/admin") + " aufrufen.")
    step(3, "Setup-Assistent durchlaufen",
         "Beim allerersten Aufruf fragt OwlBox nach Benutzername und Passwort für die "
         "Verwaltung - das gilt ab jetzt für jeden Zugriff.")
    story.append(browser_mockup(
        "http://owlbox.local:5000/admin",
        "OwlBox einrichten",
        ["Benutzername", "Passwort", "Passwort bestätigen"],
        "Konto anlegen",
    ))
    story.append(note_box(
        "Kein WLAN in Reichweite bzw. die Verbindung klappt nicht? Der Pi spannt nach kurzer "
        "Zeit automatisch einen eigenen Notfall-Hotspot auf (Standard-SSID „OwlBox-Setup“), "
        "über den die Verwaltung ebenfalls erreichbar ist - siehe "
        "OwlBox-Bedienungsanleitung.pdf, Kapitel 10.5."
    ))

    # -- X.8 Erste Geschichte -----------------------------------------------------
    h2(f"{n}.8 Erste Geschichte anlegen und Chip zuweisen")
    p(
        "Unter „Hinzufügen“ Titel vergeben und Audiodateien bzw. einen Ordner hochladen, dann "
        "in der „Bibliothek“ bei dieser Geschichte auf „Chip zuweisen“ klicken und einen "
        "RFID-Chip an den Leser halten. Chip auf die Box legen - die Wiedergabe startet "
        "automatisch."
    )
    story.append(note_box(
        "Diese sechs Schritte im Detail (mit Screenshots der Bedienelemente) stehen in "
        "OwlBox-Schnellstart.pdf."
    ))

    # -- X.9 Fertig ----------------------------------------------------------------
    h2(f"{n}.9 Fertig - wie geht es weiter?")
    bullets([
        "<b>OwlBox-Schnellstart.pdf</b> - die ersten Schritte im Alltag, kompakt auf drei "
        "Seiten.",
        "<b>OwlBox-Bedienungsanleitung.pdf</b> - jede Seite der Verwaltung und jeder "
        "physische Taster einzeln erklärt, inkl. der Design-Themes und aller "
        "Funktions-Chip-Aktionen.",
        "<b>OwlBox-Verkabelung.pdf</b> - vollständige Hardware-Referenz für spätere "
        "Änderungen oder Fehlersuche an der Verkabelung.",
    ])
    p(
        "Alle drei PDFs stehen außerdem jederzeit direkt in der Verwaltung unter Info → "
        "Dokumentation zum Download bereit."
    )


# ============================================================ 2. Windows
install_section(
    2, "Windows",
    imager_steps=[
        ("Herunterladen", "Im Browser " + mono("raspberrypi.com/software") + " öffnen und auf "
         "„Download for Windows“ klicken."),
        ("Installieren", "Die heruntergeladene .exe-Datei ausführen. Warnt Windows SmartScreen "
         "vor einer unbekannten App: auf „Weitere Informationen“ und dann „Trotzdem "
         "ausführen“ klicken. Im Installationsassistenten „Install“ und am Ende „Finish“ "
         "klicken."),
        ("Starten", "Raspberry Pi Imager über das Startmenü öffnen."),
    ],
    shortcut="Strg+Umschalt+X",
    terminal_name="die Eingabeaufforderung (cmd) - seit Windows 10 Version 1809 mit eingebautem "
                   "SSH-Client; alternativ PowerShell oder die neuere Windows-Terminal-App "
                   "(Windows 11 vorinstalliert, für Windows 10 kostenlos im Microsoft Store); "
                   "PuTTY ist bei älteren Windows-Versionen eine Alternative",
    terminal_open="die Eingabeaufforderung (Startmenü öffnen, „cmd“ eingeben, Enter - "
                   "alternativ PowerShell oder Windows Terminal)",
    eject_hint="im Explorer per Rechtsklick auf das Laufwerk → „Auswerfen“",
    app_name="Eingabeaufforderung",
    os_key="windows",
)

# ============================================================ 3. macOS
install_section(
    3, "macOS",
    imager_steps=[
        ("Herunterladen", "Im Browser " + mono("raspberrypi.com/software") + " öffnen und auf "
         "„Download for macOS“ klicken."),
        ("Installieren", "Die heruntergeladene .dmg-Datei per Doppelklick öffnen. Im sich "
         "öffnenden Fenster „Raspberry Pi Imager“ auf den Ordner „Applications“ ziehen, "
         "anschließend das dmg-Laufwerk im Finder auswerfen."),
        ("Starten", "Raspberry Pi Imager aus dem Programme-Ordner bzw. über Launchpad oder "
         "Spotlight (⌘+Leertaste, „Raspberry Pi Imager“ eingeben) öffnen. Meldet macOS, die "
         "App stamme von einem „nicht verifizierten Entwickler“: bei gedrückter ctrl-Taste "
         "(bzw. Rechtsklick) auf die App klicken → „Öffnen“ wählen und bestätigen."),
    ],
    shortcut="⌘+Umschalt+X",
    terminal_name="Terminal.app (unter Programme → Dienstprogramme, mit eingebautem SSH-Client)",
    terminal_open="Terminal.app (Programme → Dienstprogramme → Terminal, oder per Spotlight - "
                   "⌘+Leertaste, „Terminal“ eingeben)",
    eject_hint="im Finder auf das Auswurfsymbol neben der SD-Karte klicken",
    app_name="Terminal.app",
    os_key="macos",
)

# ============================================================ 4. Linux
install_section(
    4, "Linux",
    imager_steps=[
        ("Installieren (Debian/Ubuntu-basiert)", "Terminal öffnen und " +
         mono("sudo apt install rpi-imager") + " ausführen."),
        ("Alternative für andere Distributionen", "AppImage oder Flatpak von " +
         mono("raspberrypi.com/software") + " herunterladen, falls rpi-imager nicht im "
         "Paketmanager verfügbar ist oder eine neuere Version gewünscht wird."),
        ("Starten", "Über das Anwendungsmenü oder im Terminal mit " + mono("rpi-imager") + "."),
    ],
    shortcut="Strg+Umschalt+X",
    terminal_name="ein beliebiges Terminalprogramm mit Bash (z.B. GNOME Terminal oder Konsole, "
                   "mit eingebautem SSH-Client)",
    terminal_open="ein Terminalprogramm (z.B. GNOME Terminal oder Konsole, über das "
                   "Anwendungsmenü) - darin läuft standardmäßig Bash",
    eject_hint="im Dateimanager auswerfen, oder im Terminal mit udisksctl unmount / eject",
    app_name="Bash",
    os_key="linux",
)

# ============================================================ 5. Fehlerbehebung
h1("5. Fehlerbehebung bei der Installation")
story.append(spec_table(
    [
        ["Problem", "Lösungsansatz"],
        ["SD-Karte wird vom Imager nicht erkannt", "Anderen Kartenleser/USB-Anschluss "
         "probieren; Karte in einem anderen Gerät auf Schreibschutz/Defekt prüfen."],
        ["„git: command not found“", "Prompt genau ansehen: Steht dort pi@owlbox (SSH-Sitzung "
         "auf dem Pi), fehlt git auf dem frischen Raspberry Pi OS Lite - beheben mit "
         "sudo apt update && sudo apt install -y git. Steht dort der eigene Rechnername (lokal "
         "im Terminal, macOS), stattdessen xcode-select --install ausführen und den Dialog "
         "bestätigen."],
        ["owlbox.local nicht erreichbar", "IP-Adresse stattdessen verwenden (Router-Oberfläche "
         "oder Bildschirm+Tastatur direkt am Pi mit hostname -I)."],
        ["SSH-Verbindung wird abgelehnt", "Prüfen, ob SSH beim Flashen (Schritt „Anpassungen "
         "vornehmen“ im jeweiligen Betriebssystem-Kapitel) wirklich aktiviert wurde; "
         "Benutzername/Passwort exakt wie beim Flashen vergeben verwenden."],
        ["apt update/full-upgrade bricht ab", "Netzwerkverbindung des Pi prüfen "
         "(WLAN-Zugangsdaten korrekt? Kabel eingesteckt?); erneut versuchen, manche "
         "Spiegelserver sind kurzzeitig überlastet."],
        ["scripts/install.sh bricht ab", "Fehlermeldung genau lesen - meist ein fehlendes "
         "Netzwerkpaket oder fehlende Root-Rechte (mit sudo ausführen). Skript ist mehrfach "
         "gefahrlos wiederholbar."],
        ["systemctl status owlbox zeigt „failed“", "sudo journalctl -u owlbox -n 50 für die "
         "letzten Log-Zeilen; scripts/install.sh ein weiteres Mal ausführen - meist fehlt nur "
         "der zweite Durchlauf nach einem Neustart (Abschnitt „OwlBox-Software "
         "installieren“)."],
        ["Kein Ton", "aplay -l zeigt die HiFiBerry-Karte erst nach einem Neustart mit aktivem "
         "Overlay; danach scripts/install.sh erneut ausführen, das trägt ALSA-Gerät und Mixer "
         "automatisch in config.yaml ein (Abschnitt „OwlBox-Software installieren“). Zeigt "
         "aplay -l „no soundcards found“ dauerhaft: falsches Overlay für den Chip - der Amp2 "
         "braucht dtoverlay=hifiberry-dacplus (TAS5756M-Chip), nicht hifiberry-amp (das ist für "
         "den älteren Amp/Amp+ mit TAS5713); mit i2cdetect -y 1 prüfen, ob Adresse 0x4d "
         "(TAS5756M/Amp2) oder 0x1b (TAS5713/Amp) antwortet."],
        ["Eingestellte Lautstärke wird nie gespeichert, zeigt immer 0", "audio.mixer_card in "
         "config.yaml prüfen - muss zur tatsächlichen, mit aplay -l ermittelten Kartennummer "
         "passen (nicht nur audio.alsa_device). scripts/install.sh erneut ausführen, trägt alle "
         "drei Audio-Werte automatisch neu ein."],
        ["Ton knackst/klingt fragmentiert (trotz sonst unauffälligem Signalweg)",
         "vc4-kms-v3d ohne ,noaudio registriert eine eigene, ungenutzte HDMI-Audio-ALSA-Karte, "
         "die mit dem I2S-Pfad des HiFiBerry kollidiert. In config.txt prüfen: "
         "dtoverlay=vc4-kms-v3d,noaudio (nicht nur vc4-kms-v3d ohne den Zusatz) - "
         "scripts/install.sh trägt das automatisch so ein, siehe OwlBox-Verkabelung.pdf, "
         "Kapitel 2."],
        ["Display bleibt schwarz", "dmesg | grep -i drm prüfen - „Cannot find any crtc or "
         "sizes“ bedeutet, dass in config.txt der displayspezifische Overlay fehlt: neben "
         "dtoverlay=vc4-kms-v3d,noaudio wird zusätzlich dtoverlay=vc4-kms-dsi-7inch gebraucht "
         "(siehe OwlBox-Verkabelung.pdf, Kapitel 8); scripts/install.sh noch einmal ausführen, "
         "falls das noch nicht eingetragen ist (Abschnitt „OwlBox-Software installieren“)."],
        ["Display zeigt nur einen Textcursor/Login, kein Chromium",
         "sudo systemctl status owlbox-kiosk prüfen; journalctl -u owlbox-kiosk zeigt bei einem "
         "X-Absturz meist nur „status=1“ ohne echten Grund - die eigentliche Fehlermeldung steht "
         "in sudo tail /var/log/Xorg.0.log. Xwrapper.config wurde von scripts/install.sh unter "
         "/etc/X11/Xwrapper.config angelegt - prüfen, ob die Datei noch existiert."],
        ["Verwaltung im Browser nicht erreichbar", "IP-Adresse erneut prüfen; auf dem "
         "Kiosk-Display nachsehen, ob gerade der Notfall-Hotspot aktiv ist (Abschnitt „Erste "
         "Einrichtung im Browser“)."],
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
    subtitle=["Vom leeren Raspberry Pi bis zur fertig", "eingerichteten, laufenden OwlBox -",
              "für Windows, macOS und Linux."],
    meta_lines=["Komplette Installationsanleitung", "Danach: OwlBox-Schnellstart.pdf"],
)
on_page = partial(draw_header_footer, title=TITLE)

doc.multiBuild(story, onFirstPage=on_cover, onLaterPages=on_page)
print("wrote", OUT)
