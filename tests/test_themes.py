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
    for theme_id in ("weihnachten", "ostern", "winter", "silvester"):
        assert themes.is_valid_theme(theme_id)
        assert themes.THEMES[theme_id]["category"] == "sonderedition"


def test_winter_theme_declares_the_snow_effect():
    assert themes.THEMES["winter"].get("effect") == "snow"


def test_silvester_theme_declares_the_fireworks_effect():
    assert themes.THEMES["silvester"].get("effect") == "fireworks"


def test_custom_theme_is_present_in_its_own_category():
    assert themes.is_valid_theme(themes.CUSTOM_THEME_ID)
    assert themes.THEMES[themes.CUSTOM_THEME_ID]["category"] == "custom"


def test_is_valid_custom_color_accepts_only_six_digit_hex():
    assert themes.is_valid_custom_color("#12ab34") is True
    assert themes.is_valid_custom_color("#ABCDEF") is True
    assert themes.is_valid_custom_color("#fff") is False
    assert themes.is_valid_custom_color("red") is False
    assert themes.is_valid_custom_color("#12ab3g") is False
    # The whole point of this check - a value ending up in an inline style
    # attribute must never be able to smuggle in extra CSS declarations.
    assert themes.is_valid_custom_color("#000000; --bg: red") is False
    assert themes.is_valid_custom_color(None) is False


def test_is_valid_bar_radius_only_accepts_known_presets():
    for preset in themes.BAR_RADIUS_PRESETS:
        assert themes.is_valid_bar_radius(preset) is True
    assert themes.is_valid_bar_radius("999px; --bg: red") is False
    assert themes.is_valid_bar_radius("12345px") is False


def test_default_custom_theme_colors_cover_every_custom_var():
    for var in themes.CUSTOM_THEME_VARS:
        assert var in themes.DEFAULT_CUSTOM_THEME_COLORS
        assert themes.is_valid_custom_color(themes.DEFAULT_CUSTOM_THEME_COLORS[var])
    assert themes.is_valid_bar_radius(themes.DEFAULT_CUSTOM_THEME_COLORS["bar_radius"])


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
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 30)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2026, 1, 2)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2026, 3, 19)) == "winter"
    assert themes.get_seasonal_theme(datetime.date(2026, 3, 20)) != "winter"
    # Silvester sits inside Winter's window but is more specific and wins.
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 31)) == "silvester"
    assert themes.get_seasonal_theme(datetime.date(2026, 1, 1)) == "silvester"


def test_get_seasonal_theme_silvester_window_spans_year_boundary():
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 31)) == "silvester"
    assert themes.get_seasonal_theme(datetime.date(2026, 1, 1)) == "silvester"
    assert themes.get_seasonal_theme(datetime.date(2025, 12, 30)) != "silvester"
    assert themes.get_seasonal_theme(datetime.date(2026, 1, 2)) != "silvester"


def test_get_seasonal_theme_ostern_window():
    easter_2025 = datetime.date(2025, 4, 20)
    assert themes.get_seasonal_theme(easter_2025 - datetime.timedelta(days=9)) == "ostern"
    assert themes.get_seasonal_theme(easter_2025) == "ostern"
    assert themes.get_seasonal_theme(easter_2025 + datetime.timedelta(days=1)) == "ostern"
    assert themes.get_seasonal_theme(easter_2025 - datetime.timedelta(days=10)) != "ostern"
    assert themes.get_seasonal_theme(easter_2025 + datetime.timedelta(days=2)) != "ostern"


def test_get_seasonal_theme_ostern_wins_over_winter_in_an_early_easter_year():
    # Easter 2016 was 27. März - its -9-days window reaches back into what
    # would otherwise be Winter's tail end (bis 19. März).
    easter_2016 = datetime.date(2016, 3, 27)
    early_ostern_day = easter_2016 - datetime.timedelta(days=9)
    assert early_ostern_day < datetime.date(2016, 3, 20)
    assert themes.get_seasonal_theme(early_ostern_day) == "ostern"


def test_get_seasonal_theme_base_season_windows():
    assert themes.get_seasonal_theme(datetime.date(2026, 3, 20)) == "waldnacht"
    assert themes.get_seasonal_theme(datetime.date(2026, 6, 20)) == "waldnacht"
    assert themes.get_seasonal_theme(datetime.date(2026, 6, 21)) == "tageslicht"
    assert themes.get_seasonal_theme(datetime.date(2026, 9, 22)) == "tageslicht"
    assert themes.get_seasonal_theme(datetime.date(2026, 9, 23)) == "herbstwald"
    assert themes.get_seasonal_theme(datetime.date(2026, 11, 30)) == "herbstwald"
    # Weihnachten still wins over Herbst's own nominal window for 1.-26. Dez.
    assert themes.get_seasonal_theme(datetime.date(2026, 12, 10)) == "weihnachten"


def test_get_seasonal_theme_covers_every_day_of_the_year():
    day = datetime.date(2026, 1, 1)
    one_year_later = datetime.date(2027, 1, 1)
    while day < one_year_later:
        assert themes.get_seasonal_theme(day) is not None, day
        day += datetime.timedelta(days=1)


def test_auto_themeable_ids_matches_priority_order():
    ids = themes.auto_themeable_ids()
    assert ids == ("weihnachten", "silvester", "ostern", "winter", "herbstwald", "tageslicht", "waldnacht")
    for theme_id in ids:
        assert themes.is_valid_theme(theme_id)


def test_get_auto_theme_falls_through_to_next_match_when_disabled():
    day = datetime.date(2026, 12, 10)
    assert themes.get_auto_theme({}, day) == "weihnachten"
    assert themes.get_auto_theme({"weihnachten": False}, day) == "herbstwald"
    # herbstwald's own window (23.9.-20.12.) does cover 10.12. too, so
    # disabling it as well should fall through further - nothing else
    # matches that day, so the manual theme should win instead.
    assert themes.get_auto_theme({"weihnachten": False, "herbstwald": False}, day) is None


def test_get_auto_theme_defaults_unlisted_themes_to_enabled():
    day = datetime.date(2025, 12, 31)
    assert themes.get_auto_theme({}, day) == "silvester"


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
