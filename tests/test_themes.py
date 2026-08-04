from owlbox import themes

REQUIRED_SWATCH_KEYS = {"bg", "panel", "accent", "text"}


def test_default_theme_is_a_valid_theme():
    assert themes.is_valid_theme(themes.DEFAULT_THEME)


def test_every_theme_has_the_fields_the_picker_needs():
    for theme_id, theme in themes.THEMES.items():
        assert theme["label"], theme_id
        assert theme["description"], theme_id
        assert theme["bar_radius"], theme_id
        assert theme["category"] in themes.CATEGORY_LABELS, theme_id
        assert REQUIRED_SWATCH_KEYS.issubset(theme["swatch"].keys()), theme_id


def test_is_valid_theme_rejects_unknown_names():
    assert themes.is_valid_theme("not-a-real-theme") is False
    assert themes.is_valid_theme("") is False


def test_seasonal_themes_are_present_in_sonderedition_category():
    for theme_id in ("weihnachten", "ostern", "winter"):
        assert themes.is_valid_theme(theme_id)
        assert themes.THEMES[theme_id]["category"] == "sonderedition"


def test_winter_theme_declares_the_snow_effect():
    assert themes.THEMES["winter"].get("effect") == "snow"
