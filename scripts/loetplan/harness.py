"""Kabelbaum-Zeichnung und Leitungsliste für den Lötplan.

Stecker-Kennzeichen wie in einer Kfz-Kabelbaumzeichnung: X1 = 40-Pin-Stecker
auf dem Pi, X2..X8 = Bauteile, S1..S3 = Spleiße, W01.. = Leitungen,
L1..L13 = Längenmaße der Baum-Abschnitte (am Gehäuse ausmessen).
"""
from html import escape

CONNECTORS = {
    "X1": "40-Pin-Stecker Pi",
    "X2": "Amp-Buchse (HiFiBerry Amp2)",
    "X3": "Display 5″ DSI",
    "X4": "RC522 RFID",
    "X5": "Taster Weiter",
    "X6": "Taster Zurück",
    "X7": "Encoder Lautstärke",
    "X8": "Encoder Helligkeit",
}

# (Leitung, von, nach, Farbe, Querschnitt-Schlüssel, Funktion)
# von/nach: ("X1", 4) = Stecker X1 Pin 4, ("S3", None) = Spleiß S3
WIRES = [
    ("W01", ("X1", 2), ("X2", 2), "rot", "P", "5 V"),
    ("W02", ("X1", 4), ("S3", None), "rot", "P", "5 V (Amp2 + Display)"),
    ("W03", ("S3", None), ("X2", 4), "rot", "P", "5 V"),
    ("W04", ("X1", 6), ("X2", 6), "schwarz", "P", "GND"),
    ("W05", ("X1", 9), ("X2", 9), "schwarz", "P", "GND"),
    ("W06", ("X1", 14), ("X2", 14), "schwarz", "P", "GND"),
    ("W07", ("X1", 3), ("X2", 3), "blau", "S", "I2C SDA"),
    ("W08", ("X1", 5), ("X2", 5), "violett", "S", "I2C SCL"),
    ("W09", ("X1", 12), ("X2", 12), "gelb", "S", "I2S BCLK"),
    ("W10", ("X1", 35), ("X2", 35), "grün", "S", "I2S LRCLK"),
    ("W11", ("X1", 40), ("X2", 40), "weiß", "S", "I2S Audiodaten"),
    ("W12", ("X1", 38), ("X2", 38), "grau", "S", "I2S DIN (ungenutzt)"),
    ("W13", ("S3", None), ("X3", "5V"), "rot", "P", "5 V Display"),
    ("W14", ("X1", 20), ("X3", "GND"), "schwarz", "P", "GND Display"),
    ("W15", ("X1", 24), ("X4", "SDA"), "weiß", "S", "SPI CS"),
    ("W16", ("X1", 23), ("X4", "SCK"), "gelb", "S", "SPI SCK"),
    ("W17", ("X1", 19), ("X4", "MOSI"), "grün", "S", "SPI MOSI"),
    ("W18", ("X1", 21), ("X4", "MISO"), "blau", "S", "SPI MISO"),
    ("W19", ("X1", 25), ("X4", "GND"), "schwarz", "S", "GND"),
    ("W20", ("X1", 37), ("X4", "RST"), "violett", "S", "Reset"),
    ("W21", ("X1", 1), ("X4", "3.3V"), "orange", "S", "3,3 V"),
    ("W22", ("X1", 29), ("X5", "A"), "weiß", "S", "Taster Weiter"),
    ("W23", ("X1", 31), ("X6", "A"), "grau", "S", "Taster Zurück"),
    ("W24", ("X1", 30), ("S2", None), "schwarz", "S", "GND Taster"),
    ("W25", ("S2", None), ("X5", "B"), "schwarz", "S", "GND"),
    ("W26", ("S2", None), ("X6", "B"), "schwarz", "S", "GND"),
    ("W27", ("X1", 17), ("S1", None), "orange", "S", "3,3 V Encoder"),
    ("W28", ("S1", None), ("X7", "+"), "orange", "S", "3,3 V"),
    ("W29", ("S1", None), ("X8", "+"), "orange", "S", "3,3 V"),
    ("W30", ("X1", 28), ("X7", "CLK"), "gelb", "S", "Drehen A"),
    ("W31", ("X1", 13), ("X7", "DT"), "grün", "S", "Drehen B"),
    ("W32", ("X1", 15), ("X7", "SW"), "blau", "S", "Taster"),
    ("W33", ("X1", 39), ("X7", "GND"), "schwarz", "S", "GND"),
    ("W34", ("X1", 16), ("X8", "CLK"), "gelb", "S", "Drehen A"),
    ("W35", ("X1", 32), ("X8", "DT"), "grün", "S", "Drehen B"),
    ("W36", ("X1", 11), ("X8", "SW"), "blau", "S", "Taster / Nachtmodus"),
    ("W37", ("X1", 34), ("X8", "GND"), "schwarz", "S", "GND"),
]

# Längenmaße der Baum-Abschnitte: (Maß, von, bis, Empfehlung)
SEGMENTS = [
    ("L1", "X1", "Abzw. A (Amp2)", "3–5 cm"),
    ("L2", "Abzw. A", "S3", "5–10 cm"),
    ("L3", "S3", "X2 Amp-Buchse", "3–5 cm"),
    ("L4", "S3", "X3 Display", "nach Bedarf"),
    ("L5", "Abzw. A", "Abzw. R (RFID)", "nach Bedarf"),
    ("L6", "Abzw. R", "X4 RC522", "X1–X4 ≤ 30 cm"),
    ("L7", "Abzw. R", "Abzw. F (Front)", "nach Bedarf"),
    ("L8", "Abzw. F", "S2", "nach Bedarf"),
    ("L9", "S2", "X5 Taster Weiter", "≥ 5 cm"),
    ("L10", "S2", "X6 Taster Zurück", "≥ 5 cm"),
    ("L11", "Abzw. F", "S1", "nach Bedarf"),
    ("L12", "S1", "X7 Encoder L", "≥ 5 cm"),
    ("L13", "S1", "X8 Encoder H", "≥ 5 cm"),
]


def _end(e):
    name, pin = e
    if pin is None:
        return name
    return f"{name}:{pin}"


def _rows_for(conn):
    """Kontakte eines Steckers: [(kontakt, leitung, farbe)] in Leitungsreihenfolge."""
    rows = []
    for w, a, b, color, _g, _f in WIRES:
        for end in (a, b):
            if end[0] == conn:
                rows.append((end[1], w, color))
    return rows


def harness_svg(WIRE):
    W, H = 1200, 760
    o = []

    def bundle(points, n, label=None, lpos=None, anchor="middle"):
        d = "M" + " L".join(f"{x},{y}" for x, y in points)
        sw = 4 + n * 0.55
        o.append(f'<path d="{d}" class="hb-edge" stroke-width="{sw + 3}"/>')
        o.append(f'<path d="{d}" class="hb" stroke-width="{sw}"/>')
        if label:
            x, y = lpos
            o.append(f'<text x="{x}" y="{y}" class="hb-lbl" text-anchor="{anchor}">{label}</text>')

    def node(x, y, name, kind):
        if kind == "splice":
            o.append(f'<circle cx="{x}" cy="{y}" r="9" class="splice"/>')
            o.append(f'<text x="{x}" y="{y - 15}" class="splice-lbl">{name}</text>')
        else:
            o.append(f'<rect x="{x - 6}" y="{y - 6}" width="12" height="12" class="bp" transform="rotate(45 {x} {y})"/>')
            o.append(f'<text x="{x + 12}" y="{y + 22}" class="bp-lbl">{name}</text>')

    def conn_box(x, y, cid, w=200):
        rows = _rows_for(cid)
        h = 30 + len(rows) * 17 + 6
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" class="cbox"/>')
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="6" class="chead"/>')
        o.append(f'<text x="{x + 10}" y="{y + 18}" class="cid">{cid}</text>')
        o.append(f'<text x="{x + 40}" y="{y + 18}" class="cname">{escape(CONNECTORS[cid])}</text>')
        for i, (pin, w_id, color) in enumerate(rows):
            ry = y + 30 + i * 17 + 12
            o.append(f'<text x="{x + 10}" y="{ry}" class="crow">{escape(str(pin))}</text>')
            o.append(f'<rect x="{x + 70}" y="{ry - 9}" width="22" height="10" rx="2" fill="{WIRE[color]}" class="cw"/>')
            o.append(f'<text x="{x + 100}" y="{ry}" class="crow b">{w_id}</text>')
            o.append(f'<text x="{x + 140}" y="{ry}" class="crow m">{escape(color)}</text>')
        return h

    # Punkte
    X1 = (215, 380)
    A, R, F = (300, 380), (470, 380), (700, 380)
    S3 = (430, 170)
    S2, S1 = (840, 250), (840, 520)

    # Bündel (vom Stamm nach außen)
    bundle([X1, A], 31, "31 Ltg · L1", (257, 404))
    bundle([A, (300, 170), S3], 12, "12 Ltg · L2", (310, 270), "start")
    bundle([S3, (520, 170)], 11, "11 · L3", (475, 158))
    bundle([S3, (430, 92), (372, 92)], 2, "2 · L4", (438, 128), "start")
    bundle([A, R], 19, "19 Ltg · L5", (385, 368))
    bundle([R, (470, 585), (520, 585)], 7, "7 Ltg · L6", (482, 490), "start")
    bundle([R, F], 12, "12 Ltg · L7", (585, 368))
    bundle([F, (700, 250), S2], 3, "3 Ltg · L8", (711, 310), "start")
    bundle([S2, (900, 250), (900, 120), (940, 120)], 2, "2 · L9", (891, 190), "end")
    bundle([S2, (900, 250), (900, 300), (940, 300)], 2, "2 · L10", (891, 292), "end")
    bundle([F, (700, 520), S1], 9, "9 Ltg · L11", (714, 455), "start")
    bundle([S1, (900, 520), (900, 430), (940, 430)], 5, "5 · L12", (891, 480), "end")
    bundle([S1, (900, 520), (900, 600), (940, 600)], 5, "5 · L13", (891, 568), "end")

    # X1
    o.append(f'<rect x="30" y="300" width="185" height="160" rx="6" class="cbox"/>')
    o.append(f'<rect x="30" y="300" width="185" height="26" rx="6" class="chead"/>')
    o.append('<text x="40" y="318" class="cid">X1</text>')
    o.append('<text x="70" y="318" class="cname">40-Pin-Stecker Pi</text>')
    for i, t in enumerate(["31 Pins belegt, je 1 Ader", "Pin-Belegung: siehe", "Leitungsliste / Übersicht",
                           "Stecker zum Löten", "vom Pi abziehen"]):
        o.append(f'<text x="42" y="{350 + i * 20}" class="crow m">{t}</text>')

    for p, n in ((A, "Abzweig A"), (R, "Abzweig R"), (F, "Abzweig F")):
        node(*p, n, "bp")
    for p, n in ((S3, "S3"), (S2, "S2"), (S1, "S1")):
        node(*p, n, "splice")

    conn_box(520, 40, "X2", 210)
    conn_box(172, 50, "X3")
    conn_box(520, 520, "X4", 210)
    conn_box(940, 80, "X5")
    conn_box(940, 262, "X6")
    conn_box(940, 362, "X7")
    conn_box(940, 548, "X8")

    # Legende
    o.append('<g class="legend">'
             '<circle cx="40" cy="712" r="7" class="splice"/><text x="54" y="716">Spleiß (Lötverbindung, Schrumpfschlauch)</text>'
             '<rect x="34" y="734" width="11" height="11" class="bp" transform="rotate(45 39.5 739.5)"/>'
             '<text x="54" y="744">Abzweig (Adern verlassen den Baum, nichts verbunden)</text>'
             '<text x="560" y="716">Strichstärke ≈ Anzahl Leitungen im Abschnitt</text>'
             '<text x="560" y="744">L1–L13 = Längen, am Gehäuse ausmessen und in die Tabelle eintragen</text>'
             '</g>')
    return (f'<svg viewBox="0 0 {W} {H}" class="plan harness" role="img" '
            f'aria-label="Kabelbaum-Zeichnung OwlBox">' + "\n".join(o) + "</svg>")


def wire_list(WIRE, SIG, PWR):
    gauge = {"S": SIG, "P": PWR}
    rows = []
    for w, a, b, color, g, func in WIRES:
        rows.append(
            f"<tr><td class='mono nw'><b>{w}</b></td><td class='mono nw'>{escape(_end(a))}</td>"
            f"<td class='mono nw'>{escape(_end(b))}</td>"
            f"<td class='nw'><span class='sw' style='background:{WIRE[color]}'></span>{escape(color)}</td>"
            f"<td class='mono nw'>{gauge[g].split(' ')[0]} mm²</td><td>{escape(func)}</td>"
            f"<td class='blank'></td></tr>")
    head = ("<tr><th>Ltg</th><th>von</th><th>nach</th><th>Farbe</th><th>Quer&shy;schnitt</th>"
            "<th>Funktion</th><th>Länge cm</th></tr>")
    return f'<div class="tbl"><table class="wl"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def segment_table():
    rows = "".join(
        f"<tr><td class='mono'><b>{m}</b></td><td>{escape(a)}</td><td>{escape(b)}</td>"
        f"<td class='muted'>{escape(r)}</td><td class='blank'></td></tr>" for m, a, b, r in SEGMENTS)
    return ('<div class="tbl"><table class="wl"><thead><tr><th>Maß</th><th>von</th><th>bis</th>'
            f'<th>Richtwert</th><th>Länge cm</th></tr></thead><tbody>{rows}</tbody></table></div>')


def connector_legend():
    return "".join(f"<li><b class='mono'>{c}</b> {escape(n)}</li>" for c, n in CONNECTORS.items())


CSS = """
.harness .hb { fill: none; stroke: color-mix(in srgb, var(--mask) 70%, var(--fg)); stroke-linejoin: round; stroke-linecap: round; }
.harness .hb-edge { fill: none; stroke: var(--paper); stroke-linejoin: round; stroke-linecap: round; }
.harness .hb-lbl { font-size: 12px; fill: var(--fg); font-weight: 600; paint-order: stroke; stroke: var(--paper); stroke-width: 4px; }
.harness .splice { fill: var(--copper); stroke: var(--fg); stroke-width: 1.5; }
.harness .splice-lbl { font-size: 13px; font-weight: 700; fill: var(--copper); text-anchor: middle; paint-order: stroke; stroke: var(--paper); stroke-width: 4px; }
.harness .bp { fill: var(--paper); stroke: var(--fg); stroke-width: 1.5; }
.harness .bp-lbl { font-size: 11px; fill: var(--muted); paint-order: stroke; stroke: var(--paper); stroke-width: 4px; }
.harness .cbox { fill: var(--paper); stroke: var(--fg); stroke-width: 1.3; }
.harness .chead { fill: var(--hdr); }
.harness .cid { font-size: 13px; font-weight: 700; fill: #ffffff; }
.harness .cname { font-size: 11.5px; fill: #e6ece7; font-family: var(--font-body); font-weight: 600; }
.harness .crow { font-size: 11px; fill: var(--fg); }
.harness .crow.b { font-weight: 700; } .harness .crow.m { fill: var(--muted); }
.harness .cw { stroke: color-mix(in srgb, var(--fg) 45%, transparent); stroke-width: 1; }
.harness .legend text { font-size: 12px; fill: var(--muted); font-family: var(--font-body); }
svg.harness { min-width: 760px; }
td.blank { min-width: 4.5em; border-bottom: 1px solid var(--fg); }
table.wl td { padding: 4px 8px; }
.card ul.conn { display: block; columns: 2; margin: 0; padding-left: 18px; }
@media print {
  #kabelbaum-zeichnung svg.harness { max-height: 150mm; width: auto; margin: 0 auto; }
  table.wl td { padding: 0 6px; font-size: .7rem; line-height: 1.32; }
  table.wl th { padding: 2px 6px; }
  #leitungsliste .card { padding: 6px 10px; gap: 3px; }
  #leitungsliste .card ul { gap: 1px; font-size: .78rem; }
  #leitungsliste td { white-space: nowrap; }
  .wl-cols { display: grid; grid-template-columns: 1.5fr 1fr; gap: 8mm; align-items: start; }
}
"""


def sections(WIRE, SIG, PWR):
    return [
        '<section class="sheet" id="kabelbaum-zeichnung">',
        '<div class="sheet-head"><h2>Kabelbaum-Zeichnung</h2>'
        f'<span class="count">{len(WIRES)} Leitungen · 3 Spleiße · 8 Stecker</span></div>',
        "<p>Der ganze Baum auf einen Blick, so wie eine Kabelbaumzeichnung beim Auto: Vom Stecker X1 "
        "geht ein Stamm ab, der sich an den Abzweigen A, R und F aufteilt. In jedem Abschnitt steht, wie viele "
        "Leitungen darin laufen. In den Steckerkästen steht pro Kontakt die Leitungsnummer und Farbe. Die "
        "Leitungsliste auf der nächsten Seite sagt, wo jede Leitung anfängt und endet.</p>",
        f'<div class="fig">{harness_svg(WIRE)}</div>',
        "</section>",
        '<section class="sheet" id="leitungsliste">',
        '<div class="sheet-head"><h2>Leitungsliste</h2>'
        '<span class="count">Länge beim Zuschneiden eintragen</span></div>',
        '<div class="wl-cols">',
        wire_list(WIRE, SIG, PWR),
        '<div class="side">',
        '<div class="card"><h3>Stecker</h3><ul class="conn">' + connector_legend() + "</ul>"
        '<p class="muted">X1:4 = Stecker X1, Pin 4. X4:MOSI = RC522, Anschluss MOSI. S1–S3 = Spleiße.</p></div>',
        '<div class="card"><h3>Abschnittslängen</h3>' + segment_table() + "</div>",
        '<div class="card"><h3>Reihenfolge beim Bauen</h3><ul>'
        "<li>Bauteile im Gehäuse montieren, Längen L1–L13 mit einer Schnur ausmessen und eintragen</li>"
        "<li>Jede Leitung = Summe der Abschnitte auf ihrem Weg + 3 cm Reserve, zuschneiden und an beiden "
        "Enden mit der Ltg-Nummer markieren (Malerkrepp)</li>"
        "<li>Spleiße S1–S3 zuerst löten, dann die Bauteil-Enden, X1 zuletzt</li>"
        "<li>Nach dem Löten jede Leitung mit dem Durchgangsprüfer von X1 bis zum Bauteil messen, erst dann bündeln</li>"
        "</ul></div>",
        "</div></div>",
        "</section>",
    ]
