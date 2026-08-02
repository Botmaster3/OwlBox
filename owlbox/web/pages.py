from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from .auth import admin_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def player_page():
    return render_template("player.html")


@pages_bp.route("/admin")
@admin_required
def admin_page():
    config = current_app.config["OWLBOX_CONFIG"]
    return render_template("admin.html", simulate=config.simulate)


@pages_bp.route("/login", methods=["GET", "POST"])
def login():
    config = current_app.config["OWLBOX_CONFIG"]
    error = None
    if request.method == "POST":
        if request.form.get("password") == config.web.admin_password:
            session["authed"] = True
            return redirect(request.args.get("next") or url_for("pages.admin_page"))
        error = "Falsches Passwort"
    return render_template("login.html", error=error)


@pages_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("authed", None)
    return redirect(url_for("pages.login"))
