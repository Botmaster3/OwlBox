from __future__ import annotations

from functools import wraps

from flask import jsonify, redirect, request, session, url_for

from .. import repository


def admin_required(view):
    """Gates /admin* pages and the mutating API - always requires a login.

    The kiosk now-playing page (/) is intentionally NOT behind this: it has to
    keep working on the box's own touch-disabled display, which has no way to
    type a password.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("authed"):
            return view(*args, **kwargs)
        if repository.get_admin_user() is None:
            target = url_for("pages.setup")
        else:
            target = url_for("pages.login", next=request.path)
        if request.path.startswith("/api/"):
            return jsonify({"error": "unauthorized"}), 401
        return redirect(target)

    return wrapped
