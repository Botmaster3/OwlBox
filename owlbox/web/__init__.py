from __future__ import annotations

from flask import Flask, send_from_directory


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

    @app.route("/media/<int:story_id>/<path:filename>")
    def media(story_id: int, filename: str):
        directory = config.media_dir / str(story_id)
        return send_from_directory(directory, filename)

    return app
