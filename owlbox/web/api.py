from __future__ import annotations

import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Blueprint, after_this_request, current_app, jsonify, request, send_file, session
from werkzeug.utils import secure_filename

from .. import network, repository, system_info
from ..db import backup_to
from ..engine import FUNCTION_ACTION_VALUES
from ..media_utils import is_allowed_audio, is_allowed_image, probe_audio
from .auth import admin_required

logger = logging.getLogger("owlbox.web")

api_bp = Blueprint("api", __name__)


def _engine():
    return current_app.config["ENGINE"]


def _config():
    return current_app.config["OWLBOX_CONFIG"]


def _story_to_dict(story: repository.Story) -> dict:
    tracks = [] if story.stream_url else repository.get_tracks(story.id)
    return {
        "id": story.id,
        "title": story.title,
        "uid": story.uid,
        "cover_url": f"/media/{story.id}/{story.cover_path}" if story.cover_path else None,
        "stream_url": story.stream_url,
        "shuffle": story.shuffle,
        "repeat": story.repeat,
        "play_count": story.play_count,
        "total_seconds": story.total_seconds,
        "last_played_at": story.last_played_at,
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


@api_bp.route("/control/seek", methods=["POST"])
def control_seek():
    data = request.get_json(silent=True) or {}
    try:
        seconds = float(data["seconds"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "expected number 'seconds'"}), 400
    _engine().manual_seek_to(seconds)
    return jsonify({"ok": True})


# -- library ------------------------------------------------------------


@api_bp.route("/stories")
def list_stories():
    return jsonify([_story_to_dict(s) for s in repository.list_stories()])


@api_bp.route("/library/stats")
@admin_required
def library_stats():
    return jsonify(repository.get_listening_stats())


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

    stream_url = request.form.get("stream_url", "").strip()
    audio_files = [f for f in request.files.getlist("audio_files") if f and f.filename]

    if stream_url:
        if not stream_url.startswith(("http://", "https://")):
            return jsonify({"error": "stream_url must start with http:// or https://"}), 400
    elif not audio_files:
        return jsonify({"error": "at least one audio file or a stream_url is required"}), 400
    else:
        for f in audio_files:
            if not is_allowed_audio(f.filename):
                return jsonify({"error": f"unsupported audio file: {f.filename}"}), 400

    cover = request.files.get("cover")
    if cover and cover.filename and not is_allowed_image(cover.filename):
        return jsonify({"error": f"unsupported cover image: {cover.filename}"}), 400

    story = repository.create_story(title=title, stream_url=stream_url or None)
    story_dir = _config().media_dir / str(story.id)
    story_dir.mkdir(parents=True, exist_ok=True)

    if cover and cover.filename:
        cover_filename = "cover" + Path(secure_filename(cover.filename)).suffix.lower()
        cover.save(story_dir / cover_filename)
        repository.set_cover_path(story.id, cover_filename)

    if not stream_url:
        for position, f in enumerate(audio_files):
            filename = secure_filename(f.filename)
            dest = story_dir / filename
            f.save(dest)
            duration, tag_title = probe_audio(dest)
            track_title = tag_title or Path(f.filename).stem
            repository.add_track(story.id, position, filename, track_title, duration)

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


@api_bp.route("/stories/<int:story_id>/unassign", methods=["POST"])
@admin_required
def unassign_story(story_id):
    if repository.get_story(story_id) is None:
        return jsonify({"error": "not found"}), 404
    repository.remove_story_uid(story_id)
    return jsonify({"ok": True})


@api_bp.route("/stories/<int:story_id>/flags", methods=["POST"])
@admin_required
def set_flags(story_id):
    data = request.get_json(silent=True) or {}
    if repository.get_story(story_id) is None:
        return jsonify({"error": "not found"}), 404
    shuffle = data.get("shuffle")
    if shuffle is not None:
        repository.update_story_flags(story_id, shuffle=shuffle)
    repeat = data.get("repeat")
    if repeat is not None:
        # Routed through the Engine (not repository directly, unlike
        # shuffle) so a change to the currently-playing story's repeat mode
        # takes effect immediately instead of only on the next chip scan.
        if not _engine().set_story_repeat(story_id, repeat):
            return jsonify({"error": "invalid repeat mode"}), 400
    return jsonify({"ok": True})


@api_bp.route("/stories/<int:story_id>/tracks", methods=["POST"])
@admin_required
def add_tracks(story_id):
    story = repository.get_story(story_id)
    if story is None:
        return jsonify({"error": "not found"}), 404
    if story.stream_url:
        return jsonify({"error": "cannot add tracks to a livestream story"}), 400
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


# -- system ---------------------------------------------------------------


@api_bp.route("/system/shutdown", methods=["POST"])
@admin_required
def system_shutdown():
    _engine().request_shutdown()
    return jsonify({"ok": True})


@api_bp.route("/system/restart", methods=["POST"])
@admin_required
def system_restart():
    _engine().request_restart()
    return jsonify({"ok": True})


@api_bp.route("/system/backup", methods=["GET"])
@admin_required
def system_backup():
    """Downloads a ZIP with a consistent DB snapshot plus the whole media
    folder - the only way to recover the library if the SD card dies."""
    config = _config()
    tmp_dir = tempfile.mkdtemp(prefix="owlbox-backup-")
    db_snapshot = os.path.join(tmp_dir, "owlbox.db")
    zip_path = os.path.join(tmp_dir, "backup.zip")
    try:
        backup_to(db_snapshot)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(db_snapshot, arcname="owlbox.db")
            media_dir = config.media_dir
            if media_dir.exists():
                for path in media_dir.rglob("*"):
                    if path.is_file():
                        zf.write(path, arcname=str(Path("media") / path.relative_to(media_dir)))
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    @after_this_request
    def cleanup(response):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return response

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"owlbox-backup-{timestamp}.zip",
        mimetype="application/zip",
    )


@api_bp.route("/system/update", methods=["POST"])
@admin_required
def system_update():
    from ..update import run_update

    result = run_update()
    return jsonify(result), (200 if result["ok"] else 500)


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


# -- function tags (control cards) -----------------------------------------


@api_bp.route("/function-tags")
@admin_required
def list_function_tags():
    return jsonify(repository.list_function_tags())


@api_bp.route("/function-tags", methods=["POST"])
@admin_required
def create_function_tag():
    data = request.get_json(silent=True) or {}
    uid = (data.get("uid") or "").strip()
    action = (data.get("action") or "").strip()
    if not uid:
        return jsonify({"error": "uid is required"}), 400
    if action not in FUNCTION_ACTION_VALUES:
        return jsonify({"error": f"unknown action: {action}"}), 400
    repository.set_function_tag(uid, action)
    return jsonify({"ok": True})


@api_bp.route("/function-tags/<uid>", methods=["DELETE"])
@admin_required
def delete_function_tag(uid):
    repository.delete_function_tag(uid)
    return jsonify({"ok": True})


# -- parent tags (Eltern-Chips: RFID login + QR code on the kiosk display) ---


@api_bp.route("/parent-tags")
@admin_required
def list_parent_tags():
    return jsonify(repository.list_parent_tags())


@api_bp.route("/parent-tags", methods=["POST"])
@admin_required
def create_parent_tag():
    data = request.get_json(silent=True) or {}
    uid = (data.get("uid") or "").strip()
    label = (data.get("label") or "").strip()
    if not uid:
        return jsonify({"error": "uid is required"}), 400
    if not label:
        return jsonify({"error": "label is required"}), 400
    repository.add_parent_tag(uid, label)
    return jsonify({"ok": True})


@api_bp.route("/parent-tags/<uid>", methods=["DELETE"])
@admin_required
def delete_parent_tag(uid):
    repository.delete_parent_tag(uid)
    return jsonify({"ok": True})


@api_bp.route("/auth/rfid-login", methods=["POST"])
def rfid_login():
    data = request.get_json(silent=True) or {}
    uid = (data.get("uid") or "").strip()
    if not uid:
        return jsonify({"error": "uid is required"}), 400
    if not repository.is_parent_tag(uid):
        return jsonify({"error": "Chip nicht als Eltern-Chip hinterlegt."}), 401
    session["authed"] = True
    return jsonify({"ok": True})


# -- volume settings + sleep timer -------------------------------------------


@api_bp.route("/settings/volume", methods=["POST"])
@admin_required
def update_volume_settings():
    data = request.get_json(silent=True) or {}
    if "max_volume" in data:
        try:
            _engine().set_max_volume(int(data["max_volume"]))
        except (TypeError, ValueError):
            return jsonify({"error": "max_volume must be an integer"}), 400
    if "volume_step" in data:
        try:
            _engine().set_volume_step(int(data["volume_step"]))
        except (TypeError, ValueError):
            return jsonify({"error": "volume_step must be an integer"}), 400
    if "current_volume" in data:
        try:
            _engine().manual_set_volume(int(data["current_volume"]))
        except (TypeError, ValueError):
            return jsonify({"error": "current_volume must be an integer"}), 400
    return jsonify(_engine().get_state()["settings"])


@api_bp.route("/settings/brightness", methods=["POST"])
@admin_required
def update_brightness():
    data = request.get_json(silent=True) or {}
    if "min_brightness" in data:
        try:
            _engine().set_min_brightness(int(data["min_brightness"]))
        except (TypeError, ValueError):
            return jsonify({"error": "min_brightness must be an integer"}), 400
    if "max_brightness" in data:
        try:
            _engine().set_max_brightness(int(data["max_brightness"]))
        except (TypeError, ValueError):
            return jsonify({"error": "max_brightness must be an integer"}), 400
    if "brightness_step" in data:
        try:
            _engine().set_brightness_step(int(data["brightness_step"]))
        except (TypeError, ValueError):
            return jsonify({"error": "brightness_step must be an integer"}), 400
    if "brightness" in data:
        try:
            _engine().manual_set_brightness(int(data["brightness"]))
        except (TypeError, ValueError):
            return jsonify({"error": "brightness must be an integer"}), 400
    return jsonify(_engine().get_state()["settings"])


@api_bp.route("/settings/auto-sleep", methods=["POST"])
@admin_required
def update_auto_sleep():
    data = request.get_json(silent=True) or {}
    if "auto_sleep_minutes" in data:
        try:
            _engine().set_auto_sleep_minutes(int(data["auto_sleep_minutes"]))
        except (TypeError, ValueError):
            return jsonify({"error": "auto_sleep_minutes must be an integer"}), 400
    return jsonify(_engine().get_state()["settings"])


@api_bp.route("/settings/chime", methods=["POST"])
@admin_required
def update_chime():
    from .. import feedback

    data = request.get_json(silent=True) or {}
    engine = _engine()
    if "chime_volume_percent" in data:
        try:
            engine.set_chime_volume_percent(int(data["chime_volume_percent"]))
        except (TypeError, ValueError):
            return jsonify({"error": "chime_volume_percent must be an integer"}), 400
    chime_enabled = data.get("chime_enabled")
    if isinstance(chime_enabled, dict):
        for name, enabled in chime_enabled.items():
            if name in feedback.CHIMES:
                engine.set_chime_type_enabled(name, bool(enabled))
    return jsonify(engine.get_state()["settings"])


@api_bp.route("/settings/chime/test", methods=["POST"])
@admin_required
def test_chime():
    from .. import feedback

    data = request.get_json(silent=True) or {}
    name = data.get("name", "known")
    if name not in feedback.CHIMES:
        return jsonify({"error": "unknown chime name"}), 400
    volume_percent = data.get("chime_volume_percent")
    if volume_percent is not None:
        try:
            volume_percent = int(volume_percent)
        except (TypeError, ValueError):
            return jsonify({"error": "chime_volume_percent must be an integer"}), 400
    _engine().test_chime(name, volume_percent)
    return jsonify({"ok": True})


@api_bp.route("/settings/theme", methods=["POST"])
@admin_required
def update_theme():
    data = request.get_json(silent=True) or {}
    name = data.get("theme")
    if not name or not _engine().set_theme(name):
        return jsonify({"error": "unknown theme"}), 400
    return jsonify(_engine().get_state()["settings"])


@api_bp.route("/settings/theme/auto", methods=["POST"])
@admin_required
def update_theme_auto():
    data = request.get_json(silent=True) or {}
    theme_id = data.get("theme")
    if "enabled" not in data:
        return jsonify({"error": "enabled is required"}), 400
    if not theme_id or not _engine().set_auto_theme_enabled(theme_id, bool(data["enabled"])):
        return jsonify({"error": "unknown auto-themeable theme"}), 400
    return jsonify(_engine().get_state()["settings"])


@api_bp.route("/settings/theme/custom", methods=["POST"])
@admin_required
def update_theme_custom():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "at least one color/bar_radius field is required"}), 400
    if not _engine().set_custom_theme_colors(data):
        return jsonify({"error": "invalid custom theme colors"}), 400
    return jsonify(_engine().get_state()["settings"])


@api_bp.route("/sleep-timer", methods=["POST"])
@admin_required
def start_sleep_timer():
    data = request.get_json(silent=True) or {}
    try:
        minutes = float(data.get("minutes"))
    except (TypeError, ValueError):
        return jsonify({"error": "minutes is required"}), 400
    if minutes <= 0:
        return jsonify({"error": "minutes must be positive"}), 400
    _engine().start_sleep_timer(minutes)
    return jsonify({"ok": True})


@api_bp.route("/sleep-timer", methods=["DELETE"])
@admin_required
def cancel_sleep_timer():
    _engine().cancel_sleep_timer()
    return jsonify({"ok": True})


# -- wifi ---------------------------------------------------------------


@api_bp.route("/network/status")
@admin_required
def network_status():
    return jsonify(network.get_status())


@api_bp.route("/network/scan")
@admin_required
def network_scan():
    return jsonify(network.scan_networks())


@api_bp.route("/network/connect", methods=["POST"])
@admin_required
def network_connect():
    data = request.get_json(silent=True) or {}
    ssid = (data.get("ssid") or "").strip()
    password = data.get("password") or ""
    if not ssid:
        return jsonify({"error": "ssid is required"}), 400
    ok, message = network.connect(ssid, password)
    return jsonify({"ok": ok, "message": message}), (200 if ok else 400)


@api_bp.route("/network/known")
@admin_required
def network_known():
    return jsonify(network.list_known_networks())


@api_bp.route("/network/known/<name>/connect", methods=["POST"])
@admin_required
def network_known_connect(name):
    ok, message = network.connect_known(name)
    return jsonify({"ok": ok, "message": message}), (200 if ok else 400)


@api_bp.route("/network/known/<name>", methods=["DELETE"])
@admin_required
def network_known_delete(name):
    network.forget_network(name)
    return jsonify({"ok": True})


@api_bp.route("/network/wifi-power", methods=["POST"])
@admin_required
def network_wifi_power():
    data = request.get_json(silent=True) or {}
    network.set_wifi_enabled(bool(data.get("enabled")))
    return jsonify({"ok": True})


# -- system info -----------------------------------------------------------


@api_bp.route("/system/info")
@admin_required
def system_info_route():
    from .. import __version__

    config = _config()
    return jsonify(
        {
            "hardware_model": system_info.get_hardware_model(),
            "os": system_info.get_os_pretty_name(),
            "uptime_seconds": system_info.get_uptime_seconds(),
            "cpu_temp_celsius": system_info.get_cpu_temperature_celsius(),
            "memory": system_info.get_memory_info(),
            "disk": system_info.get_disk_usage(config.media_dir),
            "library": repository.get_library_stats(),
            "weekly_review": repository.get_weekly_review(),
            "app": {"version": __version__, "simulate": config.simulate},
        }
    )
