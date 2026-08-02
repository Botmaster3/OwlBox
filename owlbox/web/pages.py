from __future__ import annotations

from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .. import repository
from ..engine import FUNCTION_ACTIONS
from .auth import admin_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def player_page():
    return render_template("player.html")


@pages_bp.route("/admin")
@admin_required
def admin_dashboard_page():
    return render_template("admin_dashboard.html", active="dashboard")


@pages_bp.route("/admin/library")
@admin_required
def admin_library_page():
    config = current_app.config["OWLBOX_CONFIG"]
    return render_template("admin_library.html", simulate=config.simulate, active="library")


@pages_bp.route("/admin/add")
@admin_required
def admin_add_page():
    return render_template("admin_add.html", active="add")


@pages_bp.route("/admin/tags")
@admin_required
def admin_tags_page():
    user = repository.get_admin_user()
    return render_template(
        "admin_tags.html",
        active="tags",
        admin_rfid_uid=user.rfid_uid if user else None,
        function_actions=FUNCTION_ACTIONS,
        function_action_labels=dict(FUNCTION_ACTIONS),
    )


@pages_bp.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings_page():
    error = None
    success = None
    user = repository.get_admin_user()

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "")
        new_password_confirm = request.form.get("new_password_confirm", "")

        if user is None or not check_password_hash(user.password_hash, current_password):
            error = "Aktuelles Passwort ist falsch."
        elif not new_username:
            error = "Benutzername darf nicht leer sein."
        elif new_password and new_password != new_password_confirm:
            error = "Neue Passwörter stimmen nicht überein."
        else:
            password_hash = generate_password_hash(new_password) if new_password else user.password_hash
            repository.update_admin_user(new_username, password_hash)
            user = repository.get_admin_user()
            success = "Gespeichert."

    return render_template(
        "admin_settings.html",
        active="settings",
        username=user.username if user else "",
        error=error,
        success=success,
    )


@pages_bp.route("/setup", methods=["GET", "POST"])
def setup():
    if repository.get_admin_user() is not None:
        return redirect(url_for("pages.login"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        if not username or not password:
            error = "Benutzername und Passwort dürfen nicht leer sein."
        elif password != password_confirm:
            error = "Passwörter stimmen nicht überein."
        else:
            repository.create_admin_user(username, generate_password_hash(password))
            session["authed"] = True
            return redirect(url_for("pages.admin_dashboard_page"))
    return render_template("setup.html", error=error)


@pages_bp.route("/login", methods=["GET", "POST"])
def login():
    if repository.get_admin_user() is None:
        return redirect(url_for("pages.setup"))

    error = None
    if request.method == "POST":
        user = repository.get_admin_user()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if user is not None and username == user.username and check_password_hash(user.password_hash, password):
            session["authed"] = True
            return redirect(request.args.get("next") or url_for("pages.admin_dashboard_page"))
        error = "Benutzername oder Passwort falsch."
    return render_template("login.html", error=error)


@pages_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("authed", None)
    return redirect(url_for("pages.login"))
