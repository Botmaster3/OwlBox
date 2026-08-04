"""Selectable visual themes for the web/kiosk UI - each one is applied purely
via CSS custom properties (see static/css/style.css, `:root[data-theme=...]`
blocks), so this module only needs to know the theme's id/label/description
plus a few swatch colors for rendering the picker in Einstellungen. The
actual color/gradient/bar-radius/effect values live in the CSS, not here, so
the two have to be kept in sync by hand when adding a theme.

`category` only groups themes in the picker UI ("standard" vs
"sonderedition") - it has no effect on validation, persistence, or how a
theme is applied, so a new seasonal design is just another dict entry here.
"""
from __future__ import annotations

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
        "description": "Festliches Tannengrün mit warmem Rot und goldenem Lichterglanz.",
        "swatch": {"bg": "#0d1f14", "panel": "#16291c", "accent": "#e0483f", "text": "#f7f0dc"},
        "bar_radius": "10px",
        "category": "sonderedition",
    },
    "ostern": {
        "label": "Ostern",
        "description": "Helles Frühlingsdesign in Pastelltönen mit Korallrosa-Akzent.",
        "swatch": {"bg": "#faf3fb", "panel": "#ffffff", "accent": "#ef8ba8", "text": "#3a2a3a"},
        "bar_radius": "999px",
        "category": "sonderedition",
    },
    "winter": {
        "label": "Winter",
        "description": "Helle Winterlandschaft in Eisblau, mit sanft fallendem Schnee.",
        "swatch": {"bg": "#eef3f8", "panel": "#ffffff", "accent": "#3f8fd1", "text": "#1c2a36"},
        "bar_radius": "999px",
        "category": "sonderedition",
        "effect": "snow",
    },
}

DEFAULT_THEME = "waldnacht"

CATEGORY_LABELS = {
    "standard": "Standard",
    "sonderedition": "Sonderedition",
}


def is_valid_theme(name: str) -> bool:
    return name in THEMES
