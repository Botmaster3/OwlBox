"""Erzeugt den Lötplan (docs/loetplan/OwlBox-Loetplan.html).

Eine Seite pro Bauteil: welcher Bauteil-Pin mit welchem Kabel (Farbe,
Querschnitt) auf welchen Pin des 40-Pin-Lötsteckers auf dem Pi gehört.
Die Pinbelegung folgt den Defaults in config/config.example.yaml und
docs/hardware.md - wer dort Pins ändert, ändert sie auch hier und baut neu:

    python3 scripts/loetplan/build_loetplan.py
    node scripts/loetplan/render_pdf.cjs      # optional, erzeugt die PDF
"""
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs/loetplan/OwlBox-Loetplan.html"

# Physische Pin-Nummer -> Bezeichnung (identisch auf allen Pis mit 40-Pin-Header).
HEADER = {
    1: "3,3 V", 2: "5 V", 3: "GPIO2 · SDA", 4: "5 V", 5: "GPIO3 · SCL", 6: "GND",
    7: "GPIO4", 8: "GPIO14", 9: "GND", 10: "GPIO15", 11: "GPIO17", 12: "GPIO18",
    13: "GPIO27", 14: "GND", 15: "GPIO22", 16: "GPIO23", 17: "3,3 V", 18: "GPIO24",
    19: "GPIO10 · MOSI", 20: "GND", 21: "GPIO9 · MISO", 22: "GPIO25",
    23: "GPIO11 · SCLK", 24: "GPIO8 · CE0", 25: "GND", 26: "GPIO7 · CE1",
    27: "GPIO0 · ID_SD", 28: "GPIO1 · ID_SC", 29: "GPIO5", 30: "GND", 31: "GPIO6",
    32: "GPIO12", 33: "GPIO13", 34: "GND", 35: "GPIO19", 36: "GPIO16", 37: "GPIO26",
    38: "GPIO20", 39: "GND", 40: "GPIO21",
}

# Aderfarben (Empfehlung - wichtig ist nur, dass du sie konsequent beibehältst).
WIRE = {
    "rot": "#d63a2f", "schwarz": "#2a2a2a", "orange": "#ee8a1c", "gelb": "#e8c31a",
    "grün": "#2f9a4c", "blau": "#2f6fd1", "violett": "#8a4fc4", "weiß": "#f4f4f0",
    "grau": "#8d9290", "braun": "#8a5a32",
}

SIG = "0,14 mm² (AWG 26)"
PWR = "0,25 mm² (AWG 24)"

# Jede Ader: (Bauteil-Pin, Header-Pin, Farbe, Querschnitt, Funktion, Hinweis)
DEVICES = [
    {
        "id": "amp",
        "name": "HiFiBerry Amp2",
        "short": "Verstärker",
        "kind": "socket",
        "intro": "Der Amp2 ist ein HAT und hat keine einzelnen Lötpunkte. Er steckt auf einer "
                 "eigenen 2×20-Buchsenleiste (Raster 2,54 mm) auf der Lochrasterplatine. "
                 "Verdrahtet wird <b>1:1, gleiche Pin-Nummer auf beiden Seiten</b>: Pin 12 am Pi "
                 "geht auf Pin 12 der Amp-Buchse und so weiter. Alle anderen Pins der Buchse "
                 "bleiben frei, vor allem 27 und 28, denn GPIO1 (Pin 28) braucht der Lautstärke-Encoder.",
        "wires": [
            ("5 V", 2, "rot", PWR, "Versorgung", ""),
            ("5 V", 4, "rot", PWR, "Versorgung", "+ 5 V vom Display auf demselben Pin"),
            ("GND", 6, "schwarz", PWR, "Masse", ""),
            ("GND", 9, "schwarz", PWR, "Masse", ""),
            ("GND", 14, "schwarz", PWR, "Masse", ""),
            ("SDA", 3, "blau", SIG, "I2C-Daten (Lautstärke, Mute)", ""),
            ("SCL", 5, "violett", SIG, "I2C-Takt", ""),
            ("BCLK", 12, "gelb", SIG, "I2S Bit-Takt (GPIO18)", ""),
            ("LRCLK", 35, "grün", SIG, "I2S Links/Rechts (GPIO19)", ""),
            ("DATA", 40, "weiß", SIG, "I2S Audiodaten (GPIO21)", "ohne diese Ader kein Ton"),
            ("DIN", 38, "grau", SIG, "I2S-Eingang (GPIO20)", "vom Amp2 nicht genutzt"),
        ],
        "notes": [
            "Die fünf Strom-Adern (rot/schwarz) in 0,25 mm², nicht dünner: über 5 V und GND fließen "
            "je nach Lautstärke 1–3 A. Zwei parallele 0,25-mm²-Adern pro Richtung reichen bei "
            "maximal 20 cm Länge locker. Dicker als AWG 24 passt meist nicht mehr an einen "
            "Pin im 2,54-mm-Raster.",
            "Die vier I2S-Adern (gelb, grün, weiß, grau) so kurz wie möglich (unter 20 cm), "
            "gebündelt und dicht an einer schwarzen GND-Ader entlang führen.",
            "Kein 3,3 V nötig. Der Amp2 macht seine Logikspannung selbst, und Pin 27/28 "
            "(ID-EEPROM) bleiben unbeschaltet.",
        ],
    },
    {
        "id": "display",
        "name": "Waveshare 5″ DSI Display",
        "short": "Display",
        "kind": "module",
        "intro": "Bild, Touch und Helligkeit laufen über das DSI-Flachbandkabel. Am 40-Pin-Stecker "
                 "hängt höchstens die Stromversorgung. <b>Läuft dein Display bisher nur mit dem "
                 "DSI-Kabel, lässt du diese Seite weg.</b>",
        "wires": [
            ("5V", 4, "rot", PWR, "Versorgung", "Abzweig (Spleiß S3) von der Amp2-Ader an Pin 4"),
            ("GND", 20, "schwarz", PWR, "Masse", ""),
        ],
        "optional": [
            ("SDA", 3, "blau", SIG, "I2C-Daten", "nur falls Touch ohne nicht geht"),
            ("SCL", 5, "violett", SIG, "I2C-Takt", "nur falls Touch ohne nicht geht"),
        ],
        "notes": [
            "Die 5-V-Ader des Displays kommt nicht direkt an Pin 4, sondern zweigt kurz vor der "
            "Amp-Buchse von der roten Amp2-Ader an Pin 4 ab (Spleiß S3). So landet an Pin 4 nur eine Ader.",
            "SDA/SCL sehr wahrscheinlich unnötig: Helligkeit und Touch laufen über das DSI-Kabel. "
            "Nur anschließen, wenn der Touch ohne sie nicht reagiert.",
        ],
    },
    {
        "id": "rfid",
        "name": "RC522 RFID-Leser",
        "short": "RFID",
        "kind": "module",
        "intro": "Hängt am Hardware-SPI0 des Pi. Die Pin-Reihenfolge unten entspricht der Stiftleiste "
                 "auf dem blauen RC522-Modul (von links: SDA … 3.3V). <b>Nur 3,3 V, niemals 5 V.</b>",
        "wires": [
            ("SDA", 24, "weiß", SIG, "Chip-Select (GPIO8 · CE0)", ""),
            ("SCK", 23, "gelb", SIG, "SPI-Takt (GPIO11)", ""),
            ("MOSI", 19, "grün", SIG, "SPI Daten zum Leser (GPIO10)", ""),
            ("MISO", 21, "blau", SIG, "SPI Daten vom Leser (GPIO9)", ""),
            ("IRQ", None, None, None, "nicht verbunden", "frei lassen"),
            ("GND", 25, "schwarz", SIG, "Masse", ""),
            ("RST", 37, "violett", SIG, "Reset (GPIO26)", ""),
            ("3.3V", 1, "orange", SIG, "Versorgung 3,3 V", "NICHT 5 V"),
        ],
        "notes": [
            "SPI-Adern unter etwa 30 cm halten, sonst liest der Leser unzuverlässig.",
            "Der Leser braucht nur ein paar Dutzend mA, 0,14 mm² reicht für alle Adern.",
        ],
    },
    {
        "id": "next",
        "name": "Taster „Weiter“",
        "short": "Taster vor",
        "kind": "switch",
        "intro": "Cherry-MX-Schalter: nur die zwei Metall-Pins sind Kontakte, der Kunststoff-Pin ist "
                 "nur Halterung. Welcher Metall-Pin wohin geht, ist egal. Kein Widerstand nötig.",
        "wires": [
            ("Kontakt A", 29, "weiß", SIG, "Taster Weiter (GPIO5)", ""),
            ("Kontakt B", 30, "schwarz", SIG, "Masse", "über Spleiß S2, gemeinsam mit „Zurück“"),
        ],
        "notes": [
            "Die GND-Adern beider Taster laufen in Spleiß S2 (in der Nähe der Taster) zusammen, von "
            "dort geht eine schwarze Ader zu Pin 30.",
        ],
    },
    {
        "id": "prev",
        "name": "Taster „Zurück“",
        "short": "Taster zurück",
        "kind": "switch",
        "intro": "Gleicher Aufbau wie „Weiter“. Welcher Metall-Pin wohin geht, ist egal.",
        "wires": [
            ("Kontakt A", 31, "grau", SIG, "Taster Zurück (GPIO6)", ""),
            ("Kontakt B", 30, "schwarz", SIG, "Masse", "über Spleiß S2, gemeinsam mit „Weiter“"),
        ],
        "notes": [
            "Für die beiden Signaladern unterschiedliche Farben nehmen (weiß = Weiter, grau = Zurück), "
            "dann kannst du sie später noch auseinanderhalten.",
        ],
    },
    {
        "id": "vol",
        "name": "Encoder Lautstärke (KY-040)",
        "short": "Encoder Lautstärke",
        "kind": "module",
        "intro": "Drehen ändert die Lautstärke, Drücken ist Play/Pause, 4 s halten fährt den Pi herunter. "
                 "Pin-Reihenfolge wie auf der Stiftleiste des KY-040: CLK, DT, SW, +, GND.",
        "wires": [
            ("CLK", 28, "gelb", SIG, "Drehen A (GPIO1)", "Pin 28 – nicht zur Amp-Buchse führen"),
            ("DT", 13, "grün", SIG, "Drehen B (GPIO27)", ""),
            ("SW", 15, "blau", SIG, "Taster (GPIO22)", ""),
            ("+", 17, "orange", SIG, "Versorgung 3,3 V", "über Spleiß S1, gemeinsam mit dem Helligkeits-Encoder"),
            ("GND", 39, "schwarz", SIG, "Masse", ""),
        ],
        "notes": [
            "Das „+“ des KY-040 an 3,3 V, nicht an 5 V. Mit 5 V lägen die Signale über dem, "
            "was die GPIOs vertragen.",
            "Dreht die Lautstärke falsch herum, CLK und DT tauschen (oder in config.yaml "
            "encoder_clk/encoder_dt tauschen).",
        ],
    },
    {
        "id": "bright",
        "name": "Encoder Helligkeit (KY-040)",
        "short": "Encoder Helligkeit",
        "kind": "module",
        "intro": "Drehen ändert die Display-Helligkeit, Drücken schaltet den Nachtmodus. "
                 "Gleiche Pin-Reihenfolge wie beim Lautstärke-Encoder.",
        "wires": [
            ("CLK", 16, "gelb", SIG, "Drehen A (GPIO23)", ""),
            ("DT", 32, "grün", SIG, "Drehen B (GPIO12)", ""),
            ("SW", 11, "blau", SIG, "Taster / Nachtmodus (GPIO17)", ""),
            ("+", 17, "orange", SIG, "Versorgung 3,3 V", "über Spleiß S1, gemeinsam mit dem Lautstärke-Encoder"),
            ("GND", 34, "schwarz", SIG, "Masse", ""),
        ],
        "notes": [
            "Beide Encoder haben dieselben Aderfarben. Ein Stück beschrifteter Schrumpfschlauch "
            "(„L“ / „H“) am Kabelbündel erspart später das Suchen.",
        ],
    },
]

# ---------------------------------------------------------------------------
# SVG

PITCH = 34
PAD_X = 60
ROW_EVEN_Y = 70   # Pins 2..40 (Platinenrand)
ROW_ODD_Y = ROW_EVEN_Y + PITCH  # Pins 1..39
SQ = 24


def pin_xy(pin, x0=PAD_X, y_even=ROW_EVEN_Y):
    col = (pin - 1) // 2
    x = x0 + col * PITCH
    y = y_even if pin % 2 == 0 else y_even + PITCH
    return x, y


def header_svg(used, x0=PAD_X, y_even=ROW_EVEN_Y, caption=True, title="40-Pin-Stecker auf dem Pi (Draufsicht)"):
    """used: {pin: farbname}"""
    out = []
    w = 19 * PITCH + SQ + 24
    out.append(f'<rect x="{x0 - SQ/2 - 12}" y="{y_even - SQ/2 - 12}" width="{w}" height="{PITCH + SQ + 24}" '
               f'rx="6" class="hdr-body"/>')
    for pin in range(1, 41):
        x, y = pin_xy(pin, x0, y_even)
        color = used.get(pin)
        if color:
            out.append(f'<rect x="{x - SQ/2}" y="{y - SQ/2}" width="{SQ}" height="{SQ}" rx="3" '
                       f'fill="{WIRE[color]}" class="pin-used"/>')
            txt_cls = "pin-num on-light" if color in ("weiß", "gelb", "orange") else "pin-num on-dark"
        else:
            shape = "rect" if pin == 1 else "circle"
            if shape == "rect":
                out.append(f'<rect x="{x - 7}" y="{y - 7}" width="14" height="14" class="pin-free"/>')
            else:
                out.append(f'<circle cx="{x}" cy="{y}" r="7" class="pin-free"/>')
            txt_cls = None
        if txt_cls:
            out.append(f'<text x="{x}" y="{y + 4}" class="{txt_cls}">{pin}</text>')
    if caption:
        xl = x0 - SQ / 2 - 12
        xr = x0 + 19 * PITCH + SQ / 2 + 12
        out.append(f'<text x="{xl}" y="{y_even - 30}" class="cap" text-anchor="start">{escape(title)}</text>')
        out.append(f'<text x="{xr}" y="{y_even - 30}" class="cap muted" text-anchor="end">Platinenrand ↑ · USB/LAN →</text>')
        out.append(f'<text x="{x0}" y="{y_even + PITCH + 36}" class="cap muted" text-anchor="middle">Pin 1</text>')
        out.append(f'<text x="{x0 + 19*PITCH}" y="{y_even + PITCH + 36}" class="cap muted" text-anchor="middle">Pin 39</text>')
    return "\n".join(out)


def device_svg(dev):
    wires = [w for w in dev["wires"]] + list(dev.get("optional", []))
    used = {}
    for (_, pin, color, *_r) in wires:
        if pin:
            used.setdefault(pin, color)
    width = 2 * PAD_X + 19 * PITCH
    parts = []
    if dev["kind"] == "socket":
        # Zweite Buchse 1:1 darunter
        y2 = ROW_EVEN_Y + 230
        height = y2 + PITCH + 60
        for (label, pin, color, gauge, *_r) in wires:
            x, y = pin_xy(pin)
            x2, yb = pin_xy(pin, y_even=y2)
            sw = 5 if gauge == PWR else 3
            # Adern laufen von der Lötseite (Pin) nach unten zur gleichen Pin-Nummer der Buchse.
            mid = (y + yb) / 2
            off = (pin % 2) * 6
            d = f"M{x},{y} C{x},{mid + off} {x2},{mid + off} {x2},{yb}"
            parts.append(f'<path d="{d}" stroke-width="{sw + 2}" class="wire-edge"/>')
            parts.append(f'<path d="{d}" stroke="{WIRE[color]}" stroke-width="{sw}" class="wire"/>')
        parts.append(header_svg(used))
        parts.append(header_svg(used, y_even=y2, caption=False))
        parts.append(f'<text x="{PAD_X - SQ/2 - 12}" y="{y2 + PITCH + 44}" class="cap" text-anchor="start">'
                     f'Amp-Buchse auf der Lochrasterplatine (Draufsicht, Amp2 steckt hier drauf)</text>')
        return f'<svg viewBox="0 0 {width} {height}" class="plan" role="img" aria-label="Verdrahtung {escape(dev["name"])}">' \
               + "\n".join(parts) + "</svg>"

    # Modul / Schalter: Bauteil-Box unten, Anschlüsse in Modul-Reihenfolge
    n = len(wires)
    dev_pitch = 74 if n > 2 else 120
    box_w = max(220, (n - 1) * dev_pitch + 110)
    box_x = width / 2 - box_w / 2
    box_y = ROW_ODD_Y + 190
    pin_y = box_y
    height = box_y + 130
    optional = set(id(w) for w in dev.get("optional", []))
    for i, w in enumerate(wires):
        label, pin, color, gauge, func, note = w
        dx = box_x + 55 + i * dev_pitch
        if pin:
            x, y = pin_xy(pin)
            sw = 5 if gauge == PWR else 3
            dash = ' stroke-dasharray="7 5"' if id(w) in optional else ""
            c1y = y + 80 + (i % 3) * 10
            d = f"M{x},{y} C{x},{c1y} {dx},{pin_y - 90} {dx},{pin_y}"
            parts.append(f'<path d="{d}" stroke-width="{sw + 2}"{dash} class="wire-edge"/>')
            parts.append(f'<path d="{d}" stroke="{WIRE[color]}" stroke-width="{sw}"{dash} class="wire"/>')
    parts.append(header_svg(used))
    kind_label = {"module": "Modul", "switch": "Schalter"}[dev["kind"]]
    parts.append(f'<rect x="{box_x}" y="{box_y}" width="{box_w}" height="92" rx="8" class="dev-body"/>')
    parts.append(f'<text x="{box_x + box_w/2}" y="{box_y + 80}" class="dev-name">{escape(dev["name"])} · {kind_label}</text>')
    for i, w in enumerate(wires):
        label, pin, color, gauge, func, note = w
        dx = box_x + 55 + i * dev_pitch
        fill = WIRE[color] if color else "none"
        parts.append(f'<circle cx="{dx}" cy="{pin_y}" r="8" fill="{fill}" class="dev-pin{" nc" if not pin else ""}"/>')
        parts.append(f'<text x="{dx}" y="{pin_y + 28}" class="dev-lbl">{escape(label)}</text>')
        sub = f"→ Pin {pin}" if pin else "frei"
        parts.append(f'<text x="{dx}" y="{pin_y + 46}" class="dev-sub">{sub}</text>')
    return f'<svg viewBox="0 0 {width} {height}" class="plan" role="img" aria-label="Verdrahtung {escape(dev["name"])}">' \
           + "\n".join(parts) + "</svg>"


def swatch(color):
    if not color:
        return '<span class="sw nc"></span>–'
    return f'<span class="sw" style="background:{WIRE[color]}"></span>{color}'


def wire_table(dev):
    rows = []
    for w in dev["wires"]:
        rows.append(("", w))
    for w in dev.get("optional", []):
        rows.append(("opt", w))
    body = []
    for flag, (label, pin, color, gauge, func, note) in rows:
        pin_cell = f'<b>{pin}</b> <span class="muted">{escape(HEADER[pin])}</span>' if pin else '<span class="muted">–</span>'
        if dev["kind"] == "socket" and pin:
            pin_cell = f'<b>{pin}</b> → Buchse {pin}'
        cls = ' class="opt"' if flag else ""
        note_txt = ("optional · " if flag else "") + note
        body.append(
            f"<tr{cls}><td class='mono nw'><b>{escape(label)}</b></td><td class='mono nw'>{pin_cell}</td>"
            f"<td class='nw'>{swatch(color)}</td><td class='mono nw'>{gauge or '–'}</td>"
            f"<td>{escape(func)}{('<br><span class=note>' + escape(note_txt) + '</span>') if note_txt else ''}</td></tr>")
    head = ("<tr><th>Bauteil-Pin</th><th>Pin am Pi-Stecker</th><th>Aderfarbe</th>"
            "<th>Querschnitt</th><th>Funktion / Hinweis</th></tr>")
    return f'<div class="tbl"><table><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>'


def overview():
    owner = {}
    for dev in DEVICES:
        for (label, pin, color, gauge, *_r) in dev["wires"]:
            if pin:
                owner.setdefault(pin, []).append((dev["short"], label, color))
        for (label, pin, color, gauge, *_r) in dev.get("optional", []):
            owner.setdefault(pin, []).append((dev["short"] + " (opt.)", label, color))
    used = {p: v[0][2] for p, v in owner.items()}
    width = 2 * PAD_X + 19 * PITCH
    svg = f'<svg viewBox="0 0 {width} {ROW_ODD_Y + 60}" class="plan" role="img" aria-label="Übersicht 40-Pin-Stecker">' \
          + header_svg(used) + "</svg>"
    rows = []
    for odd in range(1, 41, 2):
        cells = []
        for pin in (odd, odd + 1):
            who = owner.get(pin)
            if who:
                txt = "<br>".join(f'<span class="sw" style="background:{WIRE[c]}"></span>{escape(d)}: {escape(l)}'
                                  for d, l, c in who)
            else:
                txt = '<span class="muted">frei</span>'
            cells.append((pin, txt))
        (p1, t1), (p2, t2) = cells
        rows.append(f"<tr><td class='r'>{t1}</td><td class='mono r muted'>{escape(HEADER[p1])}</td>"
                    f"<td class='pn'>{p1}</td><td class='pn'>{p2}</td>"
                    f"<td class='mono muted'>{escape(HEADER[p2])}</td><td>{t2}</td></tr>")
    table = ('<div class="tbl"><table class="ov"><thead><tr><th class="r">Bauteil</th><th class="r">Signal</th>'
             '<th class="pn">ungerade</th><th class="pn">gerade</th><th>Signal</th><th>Bauteil</th></tr></thead>'
             f'<tbody>{"".join(rows)}</tbody></table></div>')
    return svg, table


def count_wires():
    # Pro Pin kommt genau eine Ader an (geteilte Pins werden im Kabelbaum gespleißt).
    pins = {w[1]: w[3] for d in DEVICES for w in d["wires"] if w[1]}
    sig = sum(1 for g in pins.values() if g == SIG)
    return len(pins), len(pins) - sig, sig


CSS = """
:root {
  /* Werkbank-Blatt: links Zeichnung, darunter Tabelle; eine Seite pro Bauteil */
  --bg: #f4f6f2; --paper: #ffffff; --fg: #1b2420; --muted: #5d6b64;
  --line: #d3dad4; --mask: #1f6b4a; --copper: #b4682a; --hdr: #26302b; --pin-free: #b9c2bc;
  --font-display: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --font-body: "Archivo", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #111613; --paper: #182019; --fg: #e3e9e4; --muted: #94a39a;
  --line: #2c3730; --mask: #5cbf8c; --copper: #e09a5c; --hdr: #0b0f0d; --pin-free: #4a564f; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #111613; --paper: #182019; --fg: #e3e9e4; --muted: #94a39a;
  --line: #2c3730; --mask: #5cbf8c; --copper: #e09a5c; --hdr: #0b0f0d; --pin-free: #4a564f; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--font-body); font-size: 15px; line-height: 1.5; }
.wrap { max-width: 1060px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
h1, h2, h3 { font-family: var(--font-display); text-wrap: balance; line-height: 1.15; margin: 0; }
h1 { font-size: 2.1rem; font-weight: 800; letter-spacing: -0.01em; }
h2 { font-size: 1.45rem; font-weight: 750; }
h3 { font-size: 1rem; font-weight: 700; }
p { margin: 0; max-width: 72ch; }
.eyebrow { font-family: var(--font-mono); font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; color: var(--mask); }
.muted { color: var(--muted); }
.mono { font-family: var(--font-mono); font-size: .86rem; }
header.top { display: grid; gap: 10px; margin-bottom: 24px; }
nav.toc { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
nav.toc a { font-family: var(--font-mono); font-size: .8rem; color: var(--fg); text-decoration: none;
  border: 1px solid var(--line); border-radius: 999px; padding: 3px 10px; background: var(--paper); }
nav.toc a:hover, nav.toc a:focus-visible { border-color: var(--mask); outline: none; }
section.sheet { background: var(--paper); border: 1px solid var(--line); border-radius: 10px;
  padding: 22px; margin-top: 22px; display: grid; gap: 16px; }
.sheet-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 6px 16px; }
.sheet-head .count { font-family: var(--font-mono); font-size: .8rem; color: var(--muted); }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
.grid2 > * { min-width: 0; }
.card { border: 1px solid var(--line); border-radius: 8px; padding: 14px; display: grid; gap: 6px; align-content: start; }
.card ul { margin: 0; padding-left: 18px; display: grid; gap: 4px; }
.fig { overflow-x: auto; }
svg.plan { display: block; width: 100%; min-width: 640px; height: auto; font-family: var(--font-mono); }
.hdr-body { fill: var(--hdr); }
.pin-free { fill: none; stroke: var(--pin-free); stroke-width: 1.5; }
.pin-used { stroke: rgba(0,0,0,.35); stroke-width: 1; }
.pin-num { font-size: 11px; font-weight: 700; text-anchor: middle; }
.pin-num.on-dark { fill: #ffffff; } .pin-num.on-light { fill: #1b2420; }
.wire { fill: none; stroke-linecap: round; }
.wire-edge { fill: none; stroke-linecap: round; stroke: color-mix(in srgb, var(--fg) 45%, transparent); }
.cap { font-size: 12px; fill: var(--fg); font-family: var(--font-body); font-weight: 600; }
.cap.muted { fill: var(--muted); font-weight: 500; }
.dev-body { fill: var(--bg); stroke: var(--mask); stroke-width: 2; }
.dev-name { font-size: 13px; fill: var(--fg); text-anchor: middle; font-family: var(--font-body); font-weight: 700; }
.dev-pin { stroke: var(--fg); stroke-width: 1.5; }
.dev-pin.nc { stroke-dasharray: 2 2; }
.dev-lbl { font-size: 13px; font-weight: 700; fill: var(--fg); text-anchor: middle; }
.dev-sub { font-size: 11px; fill: var(--muted); text-anchor: middle; }
.cols, .side { display: grid; gap: 16px; }
.cols > *, .side > * { min-width: 0; }
.tbl { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-family: var(--font-mono); font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); font-weight: 600; }
tr.opt td { color: var(--muted); }
td.r, th.r { text-align: right; }
td.nw { white-space: nowrap; }
td.pn, th.pn { text-align: center; font-family: var(--font-mono); font-weight: 700; width: 3.2em;
  background: color-mix(in srgb, var(--hdr) 8%, transparent); }
table.ov td { font-size: .82rem; padding: 4px 8px; }
.note { font-size: .82rem; color: var(--copper); }
.sw { display: inline-block; width: .85em; height: .85em; border-radius: 2px; margin-right: 6px; vertical-align: -1px;
  border: 1px solid color-mix(in srgb, var(--fg) 40%, transparent); }
.sw.nc { background: none; border-style: dashed; }
.kpis { display: flex; flex-wrap: wrap; gap: 10px 28px; font-family: var(--font-mono); font-size: .85rem; }
.kpis b { font-family: var(--font-display); font-size: 1.3rem; display: block; }
.warn { border-left: 3px solid var(--copper); padding: 8px 12px; background: color-mix(in srgb, var(--copper) 9%, transparent); border-radius: 0 6px 6px 0; }
@media print {
  @page { size: A4 landscape; margin: 11mm; }
  body { font-size: 11.5px; background: #fff; }
  .wrap { max-width: none; padding: 0; }
  nav.toc { display: none; }
  section.sheet { break-before: page; border: none; padding: 0; margin: 0; gap: 10px; }
  section.sheet.first { break-before: auto; }
  svg.plan { min-width: 0; }
  .grid2 { grid-template-columns: 1fr 1fr; }
  h1 { font-size: 1.7rem; } h2 { font-size: 1.25rem; }
  .cols { grid-template-columns: 1.25fr 1fr; align-items: start; gap: 8mm; }
  .side { gap: 8px; }
  .stack .cols { grid-template-columns: 1fr; gap: 4mm; }
  .stack svg.plan { max-height: 50mm; width: auto; margin: 0 auto; }
  .stack p { max-width: none; }
  .stack td { padding: 2px 6px; }
  .stack .side { grid-template-columns: 1.7fr 1fr; align-items: start; }
  table { font-size: .82rem; } th, td { padding: 3px 6px; }
  .card { padding: 8px 10px; }
  #uebersicht svg.plan { max-height: 34mm; width: auto; margin: 0 auto; }
  table.ov td { font-size: .74rem; padding: 1px 6px; line-height: 1.3; }
  #uebersicht > p { font-size: .8rem; }
}
"""


def build():
    total, pwr, sig = count_wires()
    ov_svg, ov_table = overview()
    toc = "".join(f'<a href="#{d["id"]}">{escape(d["short"])}</a>' for d in DEVICES)
    html = [
        "<title>OwlBox Lötplan</title>",
        '<meta name="claude:viewport-fit-sides" content="cover">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800&'
        'family=IBM+Plex+Mono:wght@400;600;700&display=swap">',
        f"<style>{CSS}</style>",
        '<div class="wrap">',
        '<header class="top">',
        '<span class="eyebrow">OwlBox · Raspberry Pi 5 · 40-Pin-Lötstecker</span>',
        "<h1>Lötplan: alle Bauteile an den 40-Pin-Stecker</h1>",
        "<p>Pro Bauteil eine Seite mit Zeichnung und Tabelle: welcher Bauteil-Pin mit welcher Aderfarbe "
        "und welchem Querschnitt an welchen Pin des Steckers kommt. Alle Pin-Nummern sind die "
        "<b>physischen</b> Nummern 1–40 auf dem Stecker, nicht die GPIO-Nummern. Die Belegung "
        "entspricht der Standard-config.yaml, die Software muss also nicht angepasst werden.</p>",
        f'<nav class="toc"><a href="#kabel">Kabel</a><a href="#uebersicht">Übersicht</a><a href="#kabelbaum">Kabelbaum</a>{toc}</nav>',
        "</header>",
        # Kabel
        '<section class="sheet first" id="kabel">',
        '<div class="sheet-head"><h2>Welche Kabel?</h2></div>',
        '<div class="kpis">'
        f'<span><b>{total}</b>Adern am Stecker</span>'
        f'<span><b>{sig}</b>× 0,14 mm² Signal</span>'
        f'<span><b>{pwr}</b>× 0,25 mm² Strom</span>'
        '<span><b>2</b>× 0,75 mm² Lautsprecher</span></div>',
        '<div class="grid2">',
        '<div class="card"><h3>Signal-Adern: 0,14 mm² (AWG 26)</h3>'
        "<p>Für alles außer der Stromversorgung von Amp2 und Display: RFID, Taster, Encoder, I2C, I2S. "
        "Es fließen nur Milliampere.</p><ul>"
        "<li><b>Silikon-Litze</b> (hochflexibel, Isolierung schmilzt beim Löten nicht weg) oder PVC-Schaltlitze LiY</li>"
        "<li>Set mit 10 Farben, je ca. 2 m reicht</li>"
        "<li>Außendurchmesser ≤ 1,2 mm, damit benachbarte Pins (2,54 mm Abstand) Platz haben</li></ul></div>",
        '<div class="card"><h3>Strom-Adern: 0,25 mm² (AWG 24)</h3>'
        "<p>Nur für 5 V und GND zum Amp2 (5 Adern) und zum Display (2 Adern). Über diese Adern fließen bis zu "
        "ca. 3 A.</p><ul>"
        "<li>Silikon-Litze in Rot und Schwarz</li>"
        "<li>So kurz wie möglich, max. ca. 20 cm</li>"
        "<li>Dicker (AWG 22/20) passt meist nicht mehr an einen 2,54-mm-Pin. Deshalb lieber "
        "zwei Pins parallel (5 V auf Pin 2 und 4, GND auf 6, 9 und 14)</li></ul></div>",
        '<div class="card"><h3>Lautsprecher: 0,75 mm² (AWG 18)</h3>'
        "<p>2-adriges Lautsprecherkabel von den Federklemmen des Amp2 zu den Lautsprechern. "
        "Nicht am 40-Pin-Stecker. Polarität an beiden Lautsprechern gleich (+ zu +).</p></div>",
        '<div class="card"><h3>Zubehör</h3><ul>'
        "<li>Schrumpfschlauch 1,5 mm (über jede Lötstelle am Stecker) und 3 mm (Bündel)</li>"
        "<li>2×20-Buchsenleiste RM 2,54 + Stück Lochraster für den Amp2</li>"
        "<li>Kabelbinder bzw. Gewebeband zum Bündeln pro Bauteil</li>"
        "<li>Lötzinn 0,5–0,8 mm mit Flussmittel, Lötkolben ca. 330 °C</li></ul></div>",
        "</div>",
        '<div class="warn"><b>Vor dem Löten:</b> Pi ausschalten und Netzteil ab. Den Stecker zum Löten '
        "<b>vom Pi abziehen</b>, die Hitze kann sonst den Pi beschädigen. Pin 1 ist der Pin mit dem eckigen "
        "Lötauge, auf der Seite weg von USB/LAN. Gerade Pins (2, 4, 6 …) liegen in der Reihe am Platinenrand. "
        "Alle Zeichnungen zeigen den Stecker <b>von oben, so wie er auf dem Pi sitzt</b>. Lötest du von "
        "unten, ist alles spiegelverkehrt.</div>",
        "</section>",
        # Übersicht
        '<section class="sheet" id="uebersicht">',
        '<div class="sheet-head"><h2>Übersicht: alle 40 Pins</h2>'
        '<span class="count">Farbe = Aderfarbe des ersten Bauteils am Pin</span></div>',
        f'<div class="fig">{ov_svg}</div>',
        ov_table,
        "</section>",
        '<section class="sheet" id="kabelbaum">',
        '<div class="sheet-head"><h2>Kabelbaum: an jedem Pin nur eine Ader</h2></div>',
        '<div class="card">'
        "<p>Drei Pins versorgen zwei Bauteile. Die Adern werden dafür vorher im Kabelbaum "
        "zusammengeführt (Spleiß, wie beim Auto), sodass am Stecker immer nur eine Ader ankommt:</p><ul>"
        "<li><b>S1 · Pin 17 (3,3 V, orange):</b> eine Ader zu S1 in der Nähe der Encoder, von dort je eine "
        "zum „+“ beider Encoder</li>"
        "<li><b>S2 · Pin 30 (GND, schwarz):</b> eine Ader zu S2 in der Nähe der Taster, von dort zu Kontakt B "
        "beider Taster</li>"
        "<li><b>S3 · Pin 4 (5 V, rot):</b> die Amp2-Ader von Pin 4 bekommt kurz vor der Amp-Buchse einen "
        "Abzweig zum Display (0,25 mm²)</li>"
        "<li>So spleißen: Schrumpfschlauch vorher aufschieben, 8 mm abisolieren, Adern verdrillen oder "
        "die Abzweigader um die Hauptader wickeln, verlöten, Schrumpfschlauch drüber</li>"
        "<li>Spleiße mindestens 5 cm vom Stecker entfernt und gegeneinander versetzt setzen, damit der "
        "Baum nicht an einer Stelle dick wird und nichts direkt am Stecker knickt</li>"
        "<li>Nicht zusammenführen: die Strom-Adern des Amp2 (Pins 2, 4, 6, 9, 14). Die laufen absichtlich "
        "über mehrere Pins parallel.</li></ul></div>",
        "</section>",
    ]
    for dev in DEVICES:
        n = sum(1 for w in dev["wires"] if w[1])
        opt = len(dev.get("optional", []))
        cnt = f"{n} Adern" + (f" + {opt} optional" if opt else "")
        notes = "".join(f"<li>{escape(t)}</li>" for t in dev["notes"])
        html += [
            f'<section class="sheet{" stack" if dev["kind"] == "socket" else ""}" id="{dev["id"]}">',
            f'<div class="sheet-head"><h2>{escape(dev["name"])}</h2><span class="count">{cnt}</span></div>',
            f"<p>{dev['intro']}</p>",
            '<div class="cols">',
            f'<div class="fig">{device_svg(dev)}</div>',
            '<div class="side">',
            wire_table(dev),
            f'<div class="card"><h3>Hinweise</h3><ul>{notes}</ul></div>',
            "</div></div>",
            "</section>",
        ]
    html.append("</div>")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(html), encoding="utf-8")
    print(f"geschrieben: {OUT.relative_to(REPO_ROOT)} ({total} Adern)")


if __name__ == "__main__":
    build()
