"""Selectable visual themes for the web/kiosk UI - each one is applied purely
via CSS custom properties (see static/css/style.css, `:root[data-theme=...]`
blocks), so this module only needs to know the theme's id/label/description
plus a few swatch colors for rendering the picker in Einstellungen. The
actual color/gradient/bar-radius/effect values live in the CSS, not here, so
the two have to be kept in sync by hand when adding a theme.

`category` only groups themes in the picker UI ("standard" vs
"sonderedition") - it has no effect on validation, persistence, or how a
theme is applied, so a new seasonal design is just another dict entry here.

The `sonderedition` themes can additionally be auto-selected by date (see
`get_seasonal_theme` below) - that's an Engine-level opt-in
(`auto_seasonal_theme` setting), not something this module enforces.
"""
from __future__ import annotations

import calendar
import datetime
from typing import Optional

THEMES = {
    "waldnacht": {
        "label": "Waldnacht",
        "description": "Dunkle Nacht im Wald mit warmem Bernstein-Glühen - das Standarddesign.",
        "swatch": {"bg": "#12141c", "panel": "#1c2030", "accent": "#f2a93c", "text": "#f5f2ea"},
        "bar_radius": "4px",
        "category": "standard",
    },
    "mondschein": {
        "label": "Mondschein",
        "description": "Kühle, sternenklare Nacht in Blautönen mit eisblauem Akzent.",
        "swatch": {"bg": "#0d1420", "panel": "#182234", "accent": "#6fc3f7", "text": "#eef4fa"},
        "bar_radius": "999px",
        "category": "standard",
    },
    "herbstwald": {
        "label": "Herbstwald",
        "description": "Warme Herbstfarben in Rot- und Orangetönen, gemütlich und erdig.",
        "swatch": {"bg": "#1a1410", "panel": "#241b14", "accent": "#e2703a", "text": "#f7ece0"},
        "bar_radius": "6px",
        "category": "standard",
    },
    "tageslicht": {
        "label": "Tageslicht",
        "description": "Helles Design für den Tag, mit frischem Grün.",
        "swatch": {"bg": "#eef1f6", "panel": "#ffffff", "accent": "#2f8f5b", "text": "#1c2230"},
        "bar_radius": "999px",
        "category": "standard",
    },
    "weihnachten": {
        "label": "Weihnachten",
        "description": "Festliches Tannengrün mit warmem Rot, goldenem Lichterglanz und flackernden Kerzen.",
        "swatch": {"bg": "#0d1f14", "panel": "#16291c", "accent": "#e0483f", "text": "#f7f0dc"},
        "bar_radius": "10px",
        "category": "sonderedition",
        "effect": "candles",
        "season_label": "1.-26. Dezember",
    },
    "ostern": {
        "label": "Ostern",
        "description": "Helles Frühlingsdesign in Pastelltönen mit Korallrosa-Akzent und versteckten Ostereiern.",
        "swatch": {"bg": "#faf3fb", "panel": "#ffffff", "accent": "#ef8ba8", "text": "#3a2a3a"},
        "bar_radius": "999px",
        "category": "sonderedition",
        "effect": "eggs",
        "season_label": "9 Tage vor bis 1 Tag nach Ostern",
    },
    "winter": {
        "label": "Winter",
        "description": "Dunkle Winternacht in Eisblau, mit sanft fallendem Schnee.",
        "swatch": {"bg": "#0d1822", "panel": "#16232f", "accent": "#5fb4e8", "text": "#e8f1f8"},
        "bar_radius": "999px",
        "category": "sonderedition",
        "effect": "snow",
        "season_label": "27. Dezember bis Ende Februar",
    },
}

DEFAULT_THEME = "waldnacht"

CATEGORY_LABELS = {
    "standard": "Standard",
    "sonderedition": "Sonderedition",
}


def is_valid_theme(name: str) -> bool:
    return name in THEMES


def _easter_sunday(year: int) -> datetime.date:
    """Gregorian Easter date via the Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def get_seasonal_theme(today: Optional[datetime.date] = None) -> Optional[str]:
    """The Sonderedition theme that matches today's date, or None outside any
    of their windows. Weihnachten and Winter are checked before Ostern since
    they're plain calendar ranges (cheap, no year ambiguity); Ostern needs
    that year's computed Easter Sunday."""
    today = today or datetime.date.today()
    year = today.year

    if datetime.date(year, 12, 1) <= today <= datetime.date(year, 12, 26):
        return "weihnachten"

    # Winter spans the year boundary (27.12. of this year through the end of
    # February next year) - checked as two halves of the same window.
    if today >= datetime.date(year, 12, 27):
        return "winter"
    last_day_of_feb = 29 if calendar.isleap(year) else 28
    if today <= datetime.date(year, 2, last_day_of_feb):
        return "winter"

    easter = _easter_sunday(year)
    if easter - datetime.timedelta(days=9) <= today <= easter + datetime.timedelta(days=1):
        return "ostern"

    return None
