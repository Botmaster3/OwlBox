from __future__ import annotations

from flask import Flask, send_from_directory

from .. import themes


def create_app(engine, config) -> Flask:
    app = Flask(__name__)
    app.config["OWLBOX_CONFIG"] = config
    app.config["SECRET_KEY"] = config.web.secret_key
    app.config["ENGINE"] = engine
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # story audio uploads can be sizeable

    from .api import api_bp
    from .pages import pages_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.context_processor
    def inject_theme():
        # Rendered server-side into <html data-theme="..."> (base.html) so the
        # right design is active on first paint - the kiosk page in particular
        # can stay open for days, so waiting for a JS-driven poll to apply it
        # would mean starting every fresh page load in the wrong theme.
        # advent_candles is a pure date calculation (see themes.py), unrelated
        # to engine state - only rendered as CSS on the Weihnachten theme, but
        # harmless to always include.
        theme = engine.get_theme()
        custom_theme_style = ""
        if theme == themes.CUSTOM_THEME_ID:
            # The "custom" theme has no static `:root[data-theme="custom"]`
            # CSS block - its colors are entirely user-supplied, so they're
            # injected here as inline custom properties instead, which beat
            # the default :root block on specificity the same way a themed
            # block normally would. Engine.set_custom_theme_colors() already
            # validates every value (hex colors / an allow-listed
            # bar-radius) before it's ever stored, so this is safe to inline
            # directly rather than needing to re-validate/escape here.
            colors = engine.get_custom_theme_colors()
            custom_theme_style = " ".join(f"--{key.replace('_', '-')}: {value};" for key, value in colors.items())
        return {
            "theme": theme,
            "advent_candles": themes.get_advent_candle_count(),
            "christmas_eve": themes.is_christmas_eve(),
            "custom_theme_style": custom_theme_style,
        }

    @app.route("/media/<int:story_id>/<path:filename>")
    def media(story_id: int, filename: str):
        directory = config.media_dir / str(story_id)
        return send_from_directory(directory, filename)

    @app.route("/media/game/<path:filename>")
    def game_media(filename: str):
        # Flat pool, not per-story like the route above - see
        # repository.game_images / api.py's /api/game/images.
        return send_from_directory(config.media_dir / "game", filename)

    return app
