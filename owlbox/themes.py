"""Selectable visual themes for the web/kiosk UI - each one is applied purely
via CSS custom properties (see static/css/style.css, `:root[data-theme=...]`
blocks), so this module only needs to know the theme's id/label/description
plus a few swatch colors for rendering the picker in Einstellungen. The
actual color/gradient/bar-radius/effect values live in the CSS, not here, so
the two have to be kept in sync by hand when adding a theme - the one
exception is "custom" (see CUSTOM_THEME_ID below), whose colors are entirely
user-supplied at runtime rather than baked into the stylesheet.

`category` only groups themes in the picker UI ("standard", "sonderedition",
"custom") - it has no effect on validation, persistence, or how a theme is
applied, so a new seasonal design is just another dict entry here.

Several themes can additionally be auto-selected by date - not just the
Sonderedition ones anymore, but also three of the "standard" themes acting
as stand-ins for the calendar seasons (Herbstwald=Herbst, Tageslicht=Sommer,
Waldnacht=Frühling; Winter reuses the snowy Sonderedition theme rather than
needing a fourth). See `get_seasonal_theme`/`get_auto_theme` below - auto-
selection is an Engine-level opt-in, individually toggleable per theme
(`auto_theme_enabled` setting), not something this module enforces.
"""
from __future__ import annotations

import datetime
import re
from typing import Dict, Optional

CUSTOM_THEME_ID = "custom"

THEMES = {
    "waldnacht": {
        "label": "Waldnacht",
        "description": "Dunkle Nacht im Wald mit warmem Bernstein-Glühen - das Standarddesign.",
        "swatch": {"bg": "#12141c", "panel": "#1c2030", "accent": "#f2a93c", "text": "#f5f2ea"},
        "bar_radius": "4px",
        "category": "standard",
        "season_label": "20. März bis 20. Juni",
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
        "season_label": "23. September bis 20. Dezember",
    },
    "tageslicht": {
        "label": "Tageslicht",
        "description": "Helles Design für den Tag, mit frischem Grün.",
        "swatch": {"bg": "#eef1f6", "panel": "#ffffff", "accent": "#2f8f5b", "text": "#1c2230"},
        "bar_radius": "999px",
        "category": "standard",
        "season_label": "21. Juni bis 22. September",
    },
    "weihnachten": {
        "label": "Weihnachten",
        "description": (
            "Festliches Tannengrün mit warmem Rot, goldenem Lichterglanz und einem Adventskranz, "
            "dessen Kerzen mit jedem Advent nacheinander angezündet werden."
        ),
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
        "season_label": "27. Dezember bis 19. März",
    },
    "silvester": {
        "label": "Silvester",
        "description": "Mitternachtsblaue Feierlaune mit Gold-Akzent und Feuerwerk am Himmel.",
        "swatch": {"bg": "#0c0c18", "panel": "#17172c", "accent": "#f2c14e", "text": "#f5f0e6"},
        "bar_radius": "8px",
        "category": "sonderedition",
        "effect": "fireworks",
        "season_label": "31. Dezember bis 1. Januar",
    },
    CUSTOM_THEME_ID: {
        "label": "Eigenes Design",
        "description": "Deine eigene Farbkombination - unter Einstellungen > Design anpassbar.",
        # Placeholder - overwritten with the actually-saved colors wherever
        # the picker is rendered (see pages.py), so this only matters before
        # any custom colors have ever been saved.
        "swatch": {"bg": "#12141c", "panel": "#1c2030", "accent": "#f2a93c", "text": "#f5f2ea"},
        "bar_radius": "8px",
        "category": "custom",
    },
}

DEFAULT_THEME = "waldnacht"

CATEGORY_LABELS = {
    "standard": "Standard",
    "sonderedition": "Sonderedition",
    "custom": "Eigenes Design",
}

# The full set of CSS custom properties a theme can define, in the order the
# custom-color editor presents them. "bar_radius" is deliberately not a free
# text field in the UI (or validated as arbitrary CSS in the API) - a raw
# string would let anyone inject extra CSS declarations via the inline style
# attribute it ends up in, so it's constrained to BAR_RADIUS_PRESETS instead.
CUSTOM_THEME_VARS = (
    "bg",
    "panel",
    "accent",
    "accent_dim",
    "text",
    "text_dim",
    "border",
    "input_bg",
    "on_accent",
)
BAR_RADIUS_PRESETS = ("0px", "4px", "6px", "8px", "10px", "999px")
DEFAULT_CUSTOM_THEME_COLORS: Dict[str, str] = {
    "bg": "#12141c",
    "panel": "#1c2030",
    "accent": "#f2a93c",
    "accent_dim": "#7a5a26",
    "text": "#f5f2ea",
    "text_dim": "#9a9db0",
    "border": "#2a2f42",
    "input_bg": "#10131c",
    "on_accent": "#201400",
    "bar_radius": "4px",
}


def is_valid_theme(name: str) -> bool:
    return name in THEMES


_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def is_valid_custom_color(value: str) -> bool:
    return isinstance(value, str) and bool(_HEX_COLOR_RE.match(value))


def is_valid_bar_radius(value: str) -> bool:
    return value in BAR_RADIUS_PRESETS


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


def _in_weihnachten_window(today: datetime.date) -> bool:
    year = today.year
    return datetime.date(year, 12, 1) <= today <= datetime.date(year, 12, 26)


def _in_silvester_window(today: datetime.date) -> bool:
    # Spans the year boundary (31.12. through 1.1.) - checked as two halves
    # of the same window, same trick as the Winter window below: whichever
    # side `today` falls on, `today.year` is already the right year to
    # construct that side's date from.
    year = today.year
    return today >= datetime.date(year, 12, 31) or today <= datetime.date(year, 1, 1)


def _in_winter_window(today: datetime.date) -> bool:
    # 27.12. of this year through 19.3. (the day before kalendarischer
    # Frühlingsanfang) of the next - also spans the year boundary.
    year = today.year
    return today >= datetime.date(year, 12, 27) or today <= datetime.date(year, 3, 19)


def _in_ostern_window(today: datetime.date) -> bool:
    easter = _easter_sunday(today.year)
    return easter - datetime.timedelta(days=9) <= today <= easter + datetime.timedelta(days=1)


def _in_herbst_window(today: datetime.date) -> bool:
    year = today.year
    return datetime.date(year, 9, 23) <= today <= datetime.date(year, 12, 20)


def _in_sommer_window(today: datetime.date) -> bool:
    year = today.year
    return datetime.date(year, 6, 21) <= today <= datetime.date(year, 9, 22)


def _in_fruehling_window(today: datetime.date) -> bool:
    year = today.year
    return datetime.date(year, 3, 20) <= today <= datetime.date(year, 6, 20)


# Ordered most to least specific - the first matching window wins. Silvester
# and Ostern both need to be checked before Winter since their windows sit
# inside its much wider one (Silvester always; Ostern only in an
# early-Easter year, where the -9-days window can reach back to 13. März).
# Herbst/Sommer/Frühling stand in for the calendar seasons using three of
# the plain "standard" themes rather than dedicated ones - Winter already
# has a proper Sonderedition (the snowy one) doing that job, and Weihnachten
# still wins over it for 1.-26. Dezember regardless of Herbst's nominal
# window nominally reaching to the 20., same as it always has.
_AUTO_THEME_PRIORITY = (
    ("weihnachten", _in_weihnachten_window),
    ("silvester", _in_silvester_window),
    ("ostern", _in_ostern_window),
    ("winter", _in_winter_window),
    ("herbstwald", _in_herbst_window),
    ("tageslicht", _in_sommer_window),
    ("waldnacht", _in_fruehling_window),
)


def auto_themeable_ids() -> tuple:
    """Every theme id that has a calendar window at all - what the per-theme
    auto-toggle in Einstellungen needs to list. Mondschein and the custom
    theme aren't tied to any date, so they're not included."""
    return tuple(theme_id for theme_id, _ in _AUTO_THEME_PRIORITY)


def get_seasonal_theme(today: Optional[datetime.date] = None) -> Optional[str]:
    """The highest-priority theme whose calendar window matches today,
    ignoring per-theme enable/disable state entirely - see `get_auto_theme`
    for the version the Engine actually uses, which respects it."""
    today = today or datetime.date.today()
    for theme_id, predicate in _AUTO_THEME_PRIORITY:
        if predicate(today):
            return theme_id
    return None


def get_auto_theme(enabled: Dict[str, bool], today: Optional[datetime.date] = None) -> Optional[str]:
    """Like `get_seasonal_theme`, but skips any theme whose auto-toggle is
    off, falling through to the next-lower-priority match instead of giving
    up entirely - turning off Weihnachten in December should reveal Winter
    underneath it, not silently do nothing. A theme absent from `enabled`
    (e.g. one added after the setting was last saved) defaults to on."""
    today = today or datetime.date.today()
    for theme_id, predicate in _AUTO_THEME_PRIORITY:
        if predicate(today) and enabled.get(theme_id, True):
            return theme_id
    return None


def get_advent_candle_count(today: Optional[datetime.date] = None) -> int:
    """How many Adventskranz candles should be lit today (0-4) - the nth
    candle lights on the nth Advent Sunday and stays lit for the rest of
    Advent (all 4 remain lit through Christmas). The four Advent Sundays are
    the Sundays on/before Dec 24th, and the three before that, one week
    apart - computed straight from the calendar rather than a lookup table so
    it stays correct for any year."""
    today = today or datetime.date.today()
    christmas_eve = datetime.date(today.year, 12, 24)
    days_since_sunday = (christmas_eve.weekday() - 6) % 7  # Mon=0 ... Sun=6
    fourth_advent = christmas_eve - datetime.timedelta(days=days_since_sunday)
    for candles_lit in (4, 3, 2, 1):
        advent_sunday = fourth_advent - datetime.timedelta(weeks=4 - candles_lit)
        if today >= advent_sunday:
            return candles_lit
    return 0
