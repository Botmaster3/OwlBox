from __future__ import annotations

from functools import wraps

from flask import current_app, jsonify, redirect, request, session, url_for


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        config = current_app.config["OWLBOX_CONFIG"]
        if not config.web.admin_password or session.get("authed"):
            return view(*args, **kwargs)
        if request.path.startswith("/api/"):
            return jsonify({"error": "unauthorized"}), 401
        return redirect(url_for("pages.login", next=request.path))

    return wrapped
