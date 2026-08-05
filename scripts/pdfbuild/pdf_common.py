"""Shared styling for the three OwlBox PDF documents.

Regenerate after a UI/feature change with:
    pip install reportlab
    python3 scripts/pdfbuild/build_schnellstart.py
    python3 scripts/pdfbuild/build_bedienung.py
    python3 scripts/pdfbuild/build_verkabelung.py

Needs the DejaVu TTF family on the system (Debian/Ubuntu: apt install fonts-dejavu-core) -
picked over the reportlab base-14 fonts for full German-umlaut/dash/Ohm-sign coverage.
Deliberately no emoji in any of the three documents: reportlab draws text from a single
vector font per run, and no vector font on a typical Linux box has color-emoji glyphs -
they'd render as blank boxes (unlike the app's own UI, which renders emoji via the browser).
"""
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Table, TableStyle, Paragraph, Spacer, KeepTogether, SimpleDocTemplate, Image as RLImage,
)
from reportlab.platypus.tableofcontents import TableOfContents
from PIL import Image as PILImage

# -- fonts --------------------------------------------------------------
_FONT_DIR_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/",
    "/usr/share/fonts/dejavu/",
    "/usr/local/share/fonts/dejavu/",
]
FONT_DIR = next((d for d in _FONT_DIR_CANDIDATES if __import__("os").path.exists(d + "DejaVuSans.ttf")), None)
if FONT_DIR is None:
    raise SystemExit(
        "DejaVu Sans TTF not found - install it first, e.g. 'apt install fonts-dejavu-core' "
        "(searched: " + ", ".join(_FONT_DIR_CANDIDATES) + ")"
    )
pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_DIR + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", FONT_DIR + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily(
    "DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
    italic="DejaVuSans", boldItalic="DejaVuSans-Bold",
)
pdfmetrics.registerFont(TTFont("DejaVuSansMono", FONT_DIR + "DejaVuSansMono.ttf"))

# -- palette (forest-green accent on charcoal, matches the app's default theme) --
ACCENT = HexColor("#4f8a5b")
ACCENT_DARK = HexColor("#3a6b46")
DARK = HexColor("#1c2230")
DARK2 = HexColor("#262e40")
TEXT = HexColor("#20242c")
MUTED = HexColor("#5c6470")
RULE = HexColor("#d7dce0")
LIGHT_BG = HexColor("#f2f5f2")
NOTE_BG = HexColor("#eaf3ec")
WARN_BG = HexColor("#fbeeea")
WARN_TEXT = HexColor("#8a3b1f")
CREAM = HexColor("#f7f5ef")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm

styles = getSampleStyleSheet()

def style(name, **kw):
    base = dict(fontName="DejaVuSans", textColor=TEXT, leading=14, fontSize=10)
    base.update(kw)
    return ParagraphStyle(name, **base)

S_COVER_KICKER = style("CoverKicker", fontName="DejaVuSans-Bold", fontSize=13, textColor=ACCENT,
                        alignment=TA_CENTER, spaceAfter=6)
S_COVER_TITLE = style("CoverTitle", fontName="DejaVuSans-Bold", fontSize=30, textColor=colors.white,
                       alignment=TA_CENTER, leading=36, spaceAfter=10)
S_COVER_SUB = style("CoverSub", fontName="DejaVuSans", fontSize=13, textColor=HexColor("#c9d6cd"),
                     alignment=TA_CENTER, leading=18)
S_COVER_META = style("CoverMeta", fontName="DejaVuSans", fontSize=9.5, textColor=HexColor("#8fa393"),
                      alignment=TA_CENTER, leading=14)

S_H1 = style("H1", fontName="DejaVuSans-Bold", fontSize=19, textColor=DARK, spaceBefore=4, spaceAfter=10)
S_H2 = style("H2", fontName="DejaVuSans-Bold", fontSize=14, textColor=ACCENT_DARK, spaceBefore=16, spaceAfter=8)
S_H3 = style("H3", fontName="DejaVuSans-Bold", fontSize=11.5, textColor=DARK, spaceBefore=10, spaceAfter=5)
S_BODY = style("Body", fontSize=9.8, leading=14, spaceAfter=6, alignment=TA_LEFT)
S_BODY_TIGHT = style("BodyTight", fontSize=9.8, leading=13, spaceAfter=2)
S_SMALL = style("Small", fontSize=8.5, leading=12, textColor=MUTED, spaceAfter=4)
S_LABEL = style("Label", fontName="DejaVuSans-Bold", fontSize=9.8, leading=13, textColor=DARK)
S_BULLET = style("Bullet", fontSize=9.8, leading=14, leftIndent=12, spaceAfter=4, bulletIndent=0)
S_TOC = style("TocEntry", fontSize=10.5, leading=18, textColor=TEXT)
S_TOC_NUM = style("TocNum", fontName="DejaVuSans-Bold", fontSize=10.5, leading=18, textColor=ACCENT)
S_CELL = style("Cell", fontSize=9, leading=12.5)
S_CELL_HEAD = style("CellHead", fontName="DejaVuSans-Bold", fontSize=9, leading=12.5, textColor=colors.white)
S_MONO = style("Mono", fontName="DejaVuSansMono", fontSize=8.7, leading=12, textColor=DARK2)


def spec_table(rows, col_widths, header=True, header_bg=ACCENT_DARK):
    """rows: list of list-of-strings; first row is header if header=True."""
    data = []
    for i, row in enumerate(rows):
        if header and i == 0:
            data.append([Paragraph(c, S_CELL_HEAD) for c in row])
        else:
            data.append([Paragraph(c, S_CELL) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    ts = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT_BG]),
    ]
    if header:
        ts.append(("BACKGROUND", (0, 0), (-1, 0), header_bg))
    t.setStyle(TableStyle(ts))
    return t


def note_box(text, kind="note"):
    bg = NOTE_BG if kind == "note" else WARN_BG
    fg = TEXT if kind == "note" else WARN_TEXT
    label = "Hinweis: " if kind == "note" else "Wichtig: "
    p = Paragraph(f"<b>{label}</b>{text}", style("NoteBody", fontSize=9.5, leading=13.5, textColor=fg))
    t = Table([[p]], colWidths=[PAGE_W - 2 * MARGIN])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.6, ACCENT if kind == "note" else HexColor("#c96a4a")),
    ]))
    return KeepTogether([Spacer(1, 4), t, Spacer(1, 4)])


# -- window / screen mock-ups --------------------------------------------
# Stylised illustrations (title bar + content), not literal screenshots of any
# specific software version - used so a printed step-by-step guide has a
# picture to go with each step even though this build has no real display/Pi
# to photograph.
S_WIN_TITLE = style("WinTitle", fontName="DejaVuSans-Bold", fontSize=8.5, textColor=colors.white,
                     leading=11, alignment=TA_CENTER)
S_WIN_TITLE_LEFT = style("WinTitleLeft", fontName="DejaVuSans-Bold", fontSize=8.5,
                          textColor=colors.white, leading=11, alignment=TA_LEFT)
S_WIN_DOT = style("WinDot", fontSize=9, leading=11)
S_WIN_CTRL = style("WinCtrl", fontName="DejaVuSans", fontSize=9, textColor=colors.white,
                    leading=11, alignment=TA_RIGHT)
S_WIN_HAMBURGER = style("WinHamburger", fontName="DejaVuSans", fontSize=9, textColor=colors.white,
                         leading=11, alignment=TA_LEFT)
S_MOCK_LABEL = style("MockLabel", fontName="DejaVuSans-Bold", fontSize=8.3, leading=15, textColor=MUTED)
S_MOCK_VALUE = style("MockValue", fontName="DejaVuSansMono", fontSize=8.8, leading=15, textColor=TEXT)
S_MOCK_BTN_LABEL = style("MockBtnLabel", fontName="DejaVuSans-Bold", fontSize=8.2, leading=11,
                          alignment=TA_CENTER)
S_MOCK_BTN_VALUE = style("MockBtnValue", fontSize=7.6, leading=10, alignment=TA_CENTER)
S_BROWSER_URL = style("BrowserUrl", fontName="DejaVuSansMono", fontSize=8.3, leading=11,
                       textColor=HexColor("#2c3540"))

# Real Raspberry Pi Imager screenshots (see screenshot()) show its own actual header -
# plain and light, no coloured "traffic light" dots. The device/storage mock-ups below
# depict the same real app (just without a live catalogue to show a populated dropdown),
# so their title bar matches that real look instead of inventing a fake one.
S_APP_TITLE = style("AppTitle", fontName="DejaVuSans-Bold", fontSize=9, textColor=TEXT,
                     leading=12, alignment=TA_CENTER)


def _app_window_bar(title, width):
    """Plain light title bar matching the real Raspberry Pi Imager's own header -
    used only for the illustrative parts of that same app (not for terminals)."""
    ttl = Paragraph(title, S_APP_TITLE)
    bar = Table([[ttl]], colWidths=[width])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#f7f7f7")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
    ]))
    return bar


# Per-OS terminal "chrome" (title bar look + colour scheme) so the same command really
# looks like it was typed on that operating system, not a generic/copy-pasted picture:
#   macos   - Terminal.app: traffic-light dots, dark theme
#   windows - Eingabeaufforderung (Command Prompt): classic navy-blue console, plain
#             window with minimise/maximise/close glyphs, no coloured dots
#   linux   - a GTK terminal (e.g. GNOME Terminal) running bash: hamburger menu, dark
#             purple-ish theme, minimise/maximise/close glyphs
TERMINAL_CHROME = {
    "macos": dict(chrome="dots", bar_bg=DARK2, body_bg=DARK,
                  cmd_color=HexColor("#7fe08a"), out_color=HexColor("#d7dce0")),
    "windows": dict(chrome="win", bar_bg=HexColor("#1c1c1c"), body_bg=HexColor("#012456"),
                     cmd_color=HexColor("#f2f2f2"), out_color=HexColor("#b6c6e3")),
    "linux": dict(chrome="gtk", bar_bg=HexColor("#3a3a3a"), body_bg=HexColor("#300a24"),
                  cmd_color=HexColor("#8ae234"), out_color=HexColor("#eeeeec")),
}


def _terminal_bar(title, width, chrome, bar_bg):
    common = [
        ("BACKGROUND", (0, 0), (-1, -1), bar_bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if chrome == "dots":
        dots = Paragraph(
            '<font color="#ff5f57">⬤</font> <font color="#febc2e">⬤</font> '
            '<font color="#28c840">⬤</font>',
            S_WIN_DOT,
        )
        ttl = Paragraph(title, S_WIN_TITLE)
        bar = Table([[dots, ttl, ""]], colWidths=[18 * mm, width - 36 * mm, 18 * mm])
        bar.setStyle(TableStyle(common + [("LEFTPADDING", (0, 0), (0, 0), 8)]))
    elif chrome == "win":
        ttl = Paragraph(title, S_WIN_TITLE_LEFT)
        ctrl = Paragraph("─&nbsp;&nbsp;&nbsp;□&nbsp;&nbsp;&nbsp;✕", S_WIN_CTRL)
        bar = Table([[ttl, ctrl]], colWidths=[width - 24 * mm, 24 * mm])
        bar.setStyle(TableStyle(common + [
            ("LEFTPADDING", (0, 0), (0, 0), 8), ("RIGHTPADDING", (-1, -1), (-1, -1), 8),
        ]))
    elif chrome == "gtk":
        ham = Paragraph("☰", S_WIN_HAMBURGER)
        ttl = Paragraph(title, S_WIN_TITLE)
        ctrl = Paragraph("─&nbsp;&nbsp;&nbsp;□&nbsp;&nbsp;&nbsp;✕", S_WIN_CTRL)
        bar = Table([[ham, ttl, ctrl]], colWidths=[14 * mm, width - 38 * mm, 24 * mm])
        bar.setStyle(TableStyle(common + [
            ("LEFTPADDING", (0, 0), (0, 0), 8), ("RIGHTPADDING", (-1, -1), (-1, -1), 8),
        ]))
    else:
        raise ValueError(f"unknown chrome kind: {chrome!r}")
    return bar


def imager_window_mockup(highlight):
    """Mock-up of the Raspberry Pi Imager main window's three choice buttons.
    highlight: 'device' | 'os' | 'storage' - which button is drawn as active."""
    width = PAGE_W - 2 * MARGIN
    bar = _app_window_bar("Raspberry Pi Imager", width)
    btn_defs = [
        ("device", "CHOOSE DEVICE", "Raspberry Pi 3"),
        ("os", "CHOOSE OS", "Raspberry Pi OS (Legacy) Lite"),
        ("storage", "CHOOSE STORAGE", "SD-Karte"),
    ]
    btn_w = (width - 16 * mm) / 3
    cells, styles_row = [], []
    for key, label, value in btn_defs:
        active = key == highlight
        bg = ACCENT if active else colors.white
        fg = colors.white if active else TEXT
        lbl_style = ParagraphStyle("l", parent=S_MOCK_BTN_LABEL, textColor=fg)
        val_style = ParagraphStyle(
            "v", parent=S_MOCK_BTN_VALUE, textColor=fg if active else MUTED,
            fontName="DejaVuSans-Bold" if active else "DejaVuSans",
        )
        inner = Table(
            [[Paragraph(label, lbl_style)], [Paragraph(value, val_style)]],
            colWidths=[btn_w - 4 * mm],
        )
        inner.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        cells.append(inner)
        styles_row.append(("BACKGROUND", bg, ACCENT_DARK if active else RULE))
    row = Table([cells], colWidths=[btn_w] * 3)
    ts = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, (_, bg, box) in enumerate(styles_row):
        ts.append(("BACKGROUND", (i, 0), (i, 0), bg))
        ts.append(("BOX", (i, 0), (i, 0), 1, box))
    row.setStyle(TableStyle(ts))
    body = Table([[row]], colWidths=[width])
    body.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CREAM),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return KeepTogether([bar, body, Spacer(1, 8)])


def imager_settings_mockup(rows):
    """Mock-up of the Imager 'EDIT SETTINGS' dialog. rows: list of (label, value)."""
    width = PAGE_W - 2 * MARGIN
    bar = _app_window_bar("OS-Anpassungen (EDIT SETTINGS)", width)
    data = [[Paragraph(lbl, S_MOCK_LABEL), Paragraph(val, S_MOCK_VALUE)] for lbl, val in rows]
    t = Table(data, colWidths=[42 * mm, width - 42 * mm])
    ts = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
    ]
    t.setStyle(TableStyle(ts))
    return KeepTogether([bar, t, Spacer(1, 8)])


def terminal_mockup(title, lines, os_key="macos"):
    """Mock-up of a terminal window, styled to actually look like that OS's terminal
    (see TERMINAL_CHROME). lines: list of (is_command: bool, text: str).
    os_key: 'macos' | 'windows' | 'linux'."""
    cfg = TERMINAL_CHROME[os_key]
    width = PAGE_W - 2 * MARGIN
    bar = _terminal_bar(title, width, cfg["chrome"], cfg["bar_bg"])
    paras = [
        Paragraph(
            ("$ " if is_cmd else "") + text,
            style("TermLine", fontName="DejaVuSansMono", fontSize=8.6, leading=13.5,
                  textColor=cfg["cmd_color"] if is_cmd else cfg["out_color"]),
        )
        for is_cmd, text in lines
    ]
    body = Table([[p] for p in paras], colWidths=[width])
    body.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cfg["body_bg"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (0, 0), 8), ("BOTTOMPADDING", (-1, -1), (-1, -1), 8),
    ]))
    return KeepTogether([bar, body, Spacer(1, 8)])


def browser_mockup(url, heading, field_labels, button_text):
    """Mock-up of a browser window showing a simple form page. Deliberately
    OS-/browser-neutral (no macOS-style dots etc.) since the same browser
    (Chrome, Firefox, Edge, ...) can run on any of the three operating systems -
    unlike the terminal, there is no single "the" look to imitate here."""
    width = PAGE_W - 2 * MARGIN
    addr = Table([[Paragraph(url, S_BROWSER_URL)]], colWidths=[width - 16 * mm])
    addr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    bar = Table([[addr]], colWidths=[width - 8 * mm])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#e4e4e4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 8), ("RIGHTPADDING", (-1, -1), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    head_p = Paragraph(heading, style("MockHeading", fontName="DejaVuSans-Bold", fontSize=12,
                                       textColor=DARK, spaceAfter=8))
    field_rows = []
    for lbl in field_labels:
        field_rows.append(Paragraph(lbl, S_MOCK_LABEL))
        placeholder = Table([[""]], colWidths=[width - 20 * mm], rowHeights=[7 * mm])
        placeholder.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ]))
        field_rows.append(placeholder)
        field_rows.append(Spacer(1, 5))
    btn = Table([[Paragraph(button_text, ParagraphStyle(
        "b", parent=S_MOCK_BTN_LABEL, textColor=colors.white))]],
        colWidths=[45 * mm], rowHeights=[8 * mm])
    btn.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    content = [head_p] + field_rows + [btn]
    body = Table([[c] for c in content], colWidths=[width - 20 * mm])
    body.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    outer = Table([[body]], colWidths=[width])
    outer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    return KeepTogether([bar, outer, Spacer(1, 8)])


S_SCREENSHOT_CAPTION = style("ScreenshotCaption", fontSize=8, leading=11, textColor=MUTED,
                              alignment=TA_CENTER, spaceBefore=3)


def screenshot(path, caption=None, max_width=None):
    """Embed a real screenshot PNG, scaled to fit the page width (or max_width),
    with a thin border and an optional italic caption underneath."""
    width = max_width or (PAGE_W - 2 * MARGIN)
    with PILImage.open(path) as im:
        iw, ih = im.size
    scale = min(width / iw, 1.0)
    w, h = iw * scale, ih * scale
    img = RLImage(path, width=w, height=h, hAlign="CENTER")
    framed = Table([[img]], colWidths=[w + 4], hAlign="CENTER")
    framed.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    parts = [framed]
    if caption:
        parts.append(Paragraph(f"<i>{caption}</i>", S_SCREENSHOT_CAPTION))
    parts.append(Spacer(1, 8))
    return KeepTogether(parts)


def control_block(name, control_desc, effect_desc, extra=None):
    """One documented 'Regler' entry: name, what the widget is, what it does."""
    parts = [
        Paragraph(name, S_H3),
        Paragraph(f"<b>Steuerelement:</b> {control_desc}", S_BODY_TIGHT),
        Paragraph(f"<b>Wirkung:</b> {effect_desc}", S_BODY_TIGHT),
    ]
    if extra:
        parts.append(Paragraph(extra, S_SMALL))
    parts.append(Spacer(1, 4))
    return KeepTogether(parts)


def draw_header_footer(canvas, doc, title):
    canvas.saveState()
    # footer rule + page number
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 16 * mm, PAGE_W - MARGIN, 16 * mm)
    canvas.setFont("DejaVuSans", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 11 * mm, "OwlBox")
    canvas.drawRightString(PAGE_W - MARGIN, 11 * mm, f"Seite {doc.page}")
    canvas.drawCentredString(PAGE_W / 2, 11 * mm, title)
    canvas.restoreState()


def cover_page(canvas, doc, kicker, title, subtitle, meta_lines):
    canvas.saveState()
    canvas.setFillColor(DARK)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(ACCENT_DARK)
    canvas.rect(0, PAGE_H - 6, PAGE_W, 6, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, PAGE_W, 3, fill=1, stroke=0)

    y = PAGE_H - 110 * mm
    canvas.setFont("DejaVuSans-Bold", 13)
    canvas.setFillColor(ACCENT)
    canvas.drawCentredString(PAGE_W / 2, y, kicker)

    canvas.setFont("DejaVuSans-Bold", 30)
    canvas.setFillColor(colors.white)
    y -= 16 * mm
    for line in title:
        canvas.drawCentredString(PAGE_W / 2, y, line)
        y -= 12 * mm

    canvas.setFont("DejaVuSans", 12.5)
    canvas.setFillColor(HexColor("#c9d6cd"))
    y -= 4 * mm
    for line in subtitle:
        canvas.drawCentredString(PAGE_W / 2, y, line)
        y -= 6.5 * mm

    canvas.setFont("DejaVuSans", 9.5)
    canvas.setFillColor(HexColor("#8fa393"))
    y = 28 * mm
    for line in meta_lines:
        canvas.drawCentredString(PAGE_W / 2, y, line)
        y -= 5 * mm
    canvas.restoreState()


# -- table of contents ---------------------------------------------------
S_TOC_H1 = style("TocH1", fontName="DejaVuSans-Bold", fontSize=11.5, leading=20, textColor=DARK,
                  spaceBefore=6)
S_TOC_H2 = style("TocH2", fontName="DejaVuSans", fontSize=10, leading=16, textColor=MUTED,
                  leftIndent=12)


def make_toc():
    toc = TableOfContents()
    toc.levelStyles = [S_TOC_H1, S_TOC_H2]
    return toc


class TocDocTemplate(SimpleDocTemplate):
    """SimpleDocTemplate that feeds H1/H2 paragraphs into a TableOfContents
    flowable and registers PDF outline (bookmark) entries - needs
    doc.multiBuild() (two passes) instead of doc.build() so TOC page
    numbers resolve correctly."""

    def afterFlowable(self, flowable):
        if not isinstance(flowable, Paragraph):
            return
        text = flowable.getPlainText()
        style_name = flowable.style.name
        if style_name == "H1":
            key = f"h1-{self.page}-{abs(hash(text))}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=0, closed=False)
            self.notify("TOCEntry", (0, text, self.page, key))
        elif style_name == "H2":
            key = f"h2-{self.page}-{abs(hash(text))}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=1, closed=False)
            self.notify("TOCEntry", (1, text, self.page, key))
