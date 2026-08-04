import datetime

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


def test_easter_sunday_matches_known_reference_dates():
    assert themes._easter_sunday(2024) == datetime.date(2024, 3, 31)
    assert themes._easter_sunday(2025) == datetime.date(2025, 4, 20)
    assert themes._easter_sunday(2026) == datetime.date(2026, 4, 5)
    assert themes._easter_sunday(2027) == datetime.date(2027, 3, 28)


def test_get_seasonal_theme_weihnachten_window():
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 1)) == "weihnachten"
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 26)) == "weihnachten"
    assert themes.get_seasonal_theme(datetime.date(2025, 11, 30)) != "weihnachten"
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 27)) != "weihnachten"


def test_get_seasonal_theme_winter_window_spans_year_boundary():
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 27)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 31)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2026, 1, 1)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2026, 2, 28)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2026, 3, 1)) != "winter"
    # 2024 is a leap year - winter should include Feb 29th, not stop at the 28th.
    assert themes.get_seasonal_theme(datetime.date(2024, 2, 29)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2024, 3, 1)) != "winter"


def test_get_seasonal_theme_ostern_window():
    easter_2025 = datetime.date(2025, 4, 20)
    assert themes.get_seasonal_theme(easter_2025 - datetime.timedelta(days=9)) == "ostern"
    assert themes.get_seasonal_theme(easter_2025) == "ostern"
    assert themes.get_seasonal_theme(easter_2025 + datetime.timedelta(days=1)) == "ostern"
    assert themes.get_seasonal_theme(easter_2025 - datetime.timedelta(days=10)) != "ostern"
    assert themes.get_seasonal_theme(easter_2025 + datetime.timedelta(days=2)) != "ostern"


def test_get_seasonal_theme_returns_none_outside_any_window():
    assert themes.get_seasonal_theme(datetime.date(2025, 7, 15)) is None


def test_get_advent_candle_count_2025_reference_sundays():
    # Known 2025 Advent Sundays: 30.11. (1.), 7.12. (2.), 14.12. (3.), 21.12. (4.)
    assert themes.get_advent_candle_count(datetime.date(2025, 11, 29)) == 0
    assert themes.get_advent_candle_count(datetime.date(2025, 11, 30)) == 1
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 6)) == 1
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 7)) == 2
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 13)) == 2
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 14)) == 3
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 20)) == 3
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 21)) == 4
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 25)) == 4
    assert themes.get_advent_candle_count(datetime.date(2025, 12, 26)) == 4


def test_get_advent_candle_count_2024_reference_sundays():
    # Known 2024 Advent Sundays: 1.12. (1.), 8.12. (2.), 15.12. (3.), 22.12. (4.)
    assert themes.get_advent_candle_count(datetime.date(2024, 11, 30)) == 0
    assert themes.get_advent_candle_count(datetime.date(2024, 12, 1)) == 1
    assert themes.get_advent_candle_count(datetime.date(2024, 12, 8)) == 2
    assert themes.get_advent_candle_count(datetime.date(2024, 12, 15)) == 3
    assert themes.get_advent_candle_count(datetime.date(2024, 12, 22)) == 4
