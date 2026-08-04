# PDF-Dokumentation erzeugen

Erzeugt die drei PDFs unter `owlbox/web/static/docs/`, die auf der Info-Seite
der Verwaltung zum Download stehen: Schnellstart, Bedienungsanleitung und
Verkabelung. Kein Teil der laufenden App - nur zum lokalen Neugenerieren, wenn
sich die Bedienoberfläche oder der Hardwareaufbau ändert.

```bash
pip install -r scripts/pdfbuild/requirements.txt
python3 scripts/pdfbuild/build_schnellstart.py
python3 scripts/pdfbuild/build_bedienung.py
python3 scripts/pdfbuild/build_verkabelung.py
```

Braucht die DejaVu-Schriftfamilie auf dem System (Debian/Ubuntu: `apt install
fonts-dejavu-core`) - genutzt statt reportlabs eingebauter Basis-14-Fonts für
vollständige Unterstützung von Umlauten, Gedankenstrichen und dem Ohm-Zeichen.
Bewusst keine Emojis in den Texten: reportlab zeichnet aus einer einzigen
Vektorschrift, und keine gängige Vektorschrift auf Linux bringt farbige
Emoji-Glyphen mit - sie würden als leere Kästchen erscheinen.

`pdf_common.py` bündelt Farben, Absatzstile, die Titelseiten-/Kopf-Fuß-Zeile
sowie die automatische Inhaltsverzeichnis-Logik (reportlabs `TableOfContents`
+ `multiBuild`, zwei Render-Durchgänge, damit Seitenzahlen stimmen); jedes
`build_*.py` füllt nur noch den Seiteninhalt.
