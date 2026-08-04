"""Selectable visual themes for the web/kiosk UI - each one is applied purely
via CSS custom properties (see static/css/style.css, `:root[data-theme=...]`
blocks), so this module only needs to know the theme's id/label/description
plus a few swatch colors for rendering the picker in Einstellungen. The
actual color/gradient/bar-radius values live in the CSS, not here, so the two
have to be kept in sync by hand when adding a theme.
"""
from __future__ import annotations

THEMES = {
    "waldnacht": {
        "label": "Waldnacht",
        "description": "Dunkle Nacht im Wald mit warmem Bernstein-Glühen - das Standarddesign.",
        "swatch": {"bg": "#12141c", "panel": "#1c2030", "accent": "#f2a93c", "text": "#f5f2ea"},
        "bar_radius": "4px",
    },
    "mondschein": {
        "label": "Mondschein",
        "description": "Kühle, sternenklare Nacht in Blautönen mit eisblauem Akzent.",
        "swatch": {"bg": "#0d1420", "panel": "#182234", "accent": "#6fc3f7", "text": "#eef4fa"},
        "bar_radius": "999px",
    },
    "herbstwald": {
        "label": "Herbstwald",
        "description": "Warme Herbstfarben in Rot- und Orangetönen, gemütlich und erdig.",
        "swatch": {"bg": "#1a1410", "panel": "#241b14", "accent": "#e2703a", "text": "#f7ece0"},
        "bar_radius": "6px",
    },
    "tageslicht": {
        "label": "Tageslicht",
        "description": "Helles Design für den Tag, mit frischem Grün.",
        "swatch": {"bg": "#eef1f6", "panel": "#ffffff", "accent": "#2f8f5b", "text": "#1c2230"},
        "bar_radius": "999px",
    },
}

DEFAULT_THEME = "waldnacht"


def is_valid_theme(name: str) -> bool:
    return name in THEMES
