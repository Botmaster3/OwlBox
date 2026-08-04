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
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Table, TableStyle, Paragraph, Spacer, KeepTogether, SimpleDocTemplate,
)
from reportlab.platypus.tableofcontents import TableOfContents

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
