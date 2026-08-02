from __future__ import annotations

import logging
import shutil
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from .. import repository
from ..media_utils import is_allowed_audio, is_allowed_image, probe_audio
from .auth import admin_required

logger = logging.getLogger("owlbox.web")

api_bp = Blueprint("api", __name__)


def _engine():
    return current_app.config["ENGINE"]


def _config():
    return current_app.config["OWLBOX_CONFIG"]


def _story_to_dict(story: repository.Story) -> dict:
    tracks = repository.get_tracks(story.id)
    return {
        "id": story.id,
        "title": story.title,
        "uid": story.uid,
        "cover_url": f"/media/{story.id}/{story.cover_path}" if story.cover_path else None,
        "shuffle": story.shuffle,
        "repeat": story.repeat,
        "track_count": len(tracks),
        "tracks": [
            {"id": t.id, "position": t.position, "filename": t.filename, "title": t.title, "duration": t.duration}
            for t in tracks
        ],
    }


# -- player state & controls -------------------------------------------------


@api_bp.route("/state")
def state():
    return jsonify(_engine().get_state())


@api_bp.route("/control/play", methods=["POST"])
def control_play():
    _engine().manual_play()
    return jsonify({"ok": True})


@api_bp.route("/control/pause", methods=["POST"])
def control_pause():
    _engine().manual_pause()
    return jsonify({"ok": True})


@api_bp.route("/control/toggle", methods=["POST"])
def control_toggle():
    _engine().manual_toggle_pause()
    return jsonify({"ok": True})


@api_bp.route("/control/next", methods=["POST"])
def control_next():
    _engine().manual_next()
    return jsonify({"ok": True})


@api_bp.route("/control/prev", methods=["POST"])
def control_prev():
    _engine().manual_prev()
    return jsonify({"ok": True})


@api_bp.route("/control/volume", methods=["POST"])
def control_volume():
    data = request.get_json(silent=True) or {}
    try:
        level = int(data["level"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "expected integer 'level'"}), 400
    _engine().manual_set_volume(level)
    return jsonify({"ok": True})


# -- library ------------------------------------------------------------


@api_bp.route("/stories")
def list_stories():
    return jsonify([_story_to_dict(s) for s in repository.list_stories()])


@api_bp.route("/stories/<int:story_id>")
def get_story(story_id):
    story = repository.get_story(story_id)
    if story is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(_story_to_dict(story))


@api_bp.route("/stories", methods=["POST"])
@admin_required
def create_story():
    title = request.form.get("title", "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    audio_files = [f for f in request.files.getlist("audio_files") if f and f.filename]
    if not audio_files:
        return jsonify({"error": "at least one audio file is required"}), 400
    for f in audio_files:
        if not is_allowed_audio(f.filename):
            return jsonify({"error": f"unsupported audio file: {f.filename}"}), 400

    cover = request.files.get("cover")
    if cover and cover.filename and not is_allowed_image(cover.filename):
        return jsonify({"error": f"unsupported cover image: {cover.filename}"}), 400

    story = repository.create_story(title=title)
    story_dir = _config().media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)

    if cover and cover.filename:
        cover_filename = "cover" + Path(secure_filename(cover.filename)).suffix.lower()
        cover.save(story_dir / cover_filename)
        repository.set_cover_path(story.id, cover_filename)

    for position, f in enumerate(audio_files):
        filename = secure_filename(f.filename)
        dest = story_dir / filename
        f.save(dest)
        duration, tag_title = probe_audio(dest)
        title = tag_title or Path(f.filename).stem
        repository.add_track(story.id, position, filename, title, duration)

    uid = request.form.get("uid", "").strip()
    if uid:
        repository.assign_uid(story.id, uid)

    return jsonify(_story_to_dict(repository.get_story(story.id))), 201


@api_bp.route("/stories/<int:story_id>", methods=["DELETE"])
@admin_required
def delete_story(story_id):
    story = repository.get_story(story_id)
    if story is None:
        return jsonify({"error": "not found"}), 404
    repository.delete_story(story_id)
    shutil.rmtree(_config().media_dir / str(story_id), ignore_errors=True)
    return jsonify({"ok": True})


@api_bp.route("/stories/<int:story_id>/assign", methods=["POST"])
@admin_required
def assign_story(story_id):
    data = request.get_json(silent=True) or {}
    uid = (data.get("uid") or "").strip()
    if not uid:
        return jsonify({"error": "uid is required"}), 400
    if repository.get_story(story_id) is None:
        return jsonify({"error": "not found"}), 404
    repository.assign_uid(story_id, uid)
    return jsonify({"ok": True})


@api_bp.route("/stories/<int:story_id>/flags", methods=["POST"])
@admin_required
def set_flags(story_id):
    data = request.get_json(silent=True) or {}
    if repository.get_story(story_id) is None:
        return jsonify({"error": "not found"}), 404
    repository.update_story_flags(story_id, shuffle=data.get("shuffle"), repeat=data.get("repeat"))
    return jsonify({"ok": True})


@api_bp.route("/stories/<int:story_id>/tracks", methods=["POST"])
@admin_required
def add_tracks(story_id):
    story = repository.get_story(story_id)
    if story is None:
        return jsonify({"error": "not found"}), 404
    audio_files = [f for f in request.files.getlist("audio_files") if f and f.filename]
    if not audio_files:
        return jsonify({"error": "at least one audio file is required"}), 400
    for f in audio_files:
        if not is_allowed_audio(f.filename):
            return jsonify({"error": f"unsupported audio file: {f.filename}"}), 400
    story_dir = _config().media_dir / str(story_id)
    story_dir.mkdir(parents=True, exist_ok=True)
    next_pos = repository.next_track_position(story_id)
    for offset, f in enumerate(audio_files):
        filename = secure_filename(f.filename)
        dest = story_dir / filename
        f.save(dest)
        duration, tag_title = probe_audio(dest)
        repository.add_track(story_id, next_pos + offset, filename, tag_title, duration)
    return jsonify(_story_to_dict(repository.get_story(story_id)))


@api_bp.route("/stories/<int:story_id>/tracks/<int:track_id>", methods=["DELETE"])
@admin_required
def delete_track(story_id, track_id):
    repository.delete_track(track_id)
    return jsonify({"ok": True})


@api_bp.route("/stories/<int:story_id>/tracks/reorder", methods=["POST"])
@admin_required
def reorder_tracks(story_id):
    data = request.get_json(silent=True) or {}
    track_ids = data.get("track_ids")
    if not isinstance(track_ids, list):
        return jsonify({"error": "expected list 'track_ids'"}), 400
    repository.reorder_tracks(story_id, [int(i) for i in track_ids])
    return jsonify({"ok": True})


# -- RFID scans -----------------------------------------------------------


@api_bp.route("/scans/last")
def last_scan():
    return jsonify(repository.get_last_scan())


# -- dev tools (only meaningful with the simulated RFID reader) --------------


@api_bp.route("/dev/simulate-scan", methods=["POST"])
@admin_required
def simulate_scan():
    if not _config().simulate:
        return jsonify({"error": "only available with simulate: true"}), 404
    data = request.get_json(silent=True) or {}
    uid = (data.get("uid") or "").strip()
    if not uid:
        return jsonify({"error": "uid is required"}), 400
    _engine().simulate_scan(uid, hold_seconds=data.get("hold_seconds"))
    return jsonify({"ok": True})


@api_bp.route("/dev/simulate-remove", methods=["POST"])
@admin_required
def simulate_remove():
    if not _config().simulate:
        return jsonify({"error": "only available with simulate: true"}), 404
    _engine().simulate_remove()
    return jsonify({"ok": True})
