"""Audio playback via an mpv subprocess controlled over its JSON IPC socket.

Volume is controlled through the ALSA hardware mixer (amixer) rather than mpv's
software volume, since the HiFiBerry boards do hardware volume control and that
avoids clipping/quality loss from software attenuation.

If mpv isn't installed, or config.simulate is set, StubPlayer is used instead so
the rest of the app (web UI, engine loop) keeps working on a dev machine.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import socket
import subprocess
import threading
import time
from typing import Optional, Protocol


class PlayerError(Exception):
    pass


class AlsaMixer:
    def __init__(self, control: str, card: str = "0"):
        self.control = control
        self.card = card

    def set_percent(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        subprocess.run(
            ["amixer", "-c", self.card, "sset", self.control, f"{percent}%"],
            capture_output=True,
            check=False,
        )

    def get_percent(self) -> int:
        try:
            result = subprocess.run(
                ["amixer", "-c", self.card, "sget", self.control],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 0
        for line in result.stdout.splitlines():
            if "%" in line and "[" in line:
                start = line.index("[") + 1
                end = line.index("%", start)
                try:
                    return int(line[start:end])
                except ValueError:
                    continue
        return 0


class _MpvIpc:
    """Line-delimited JSON IPC client for mpv's --input-ipc-server socket."""

    def __init__(self, socket_path: str):
        self._socket_path = socket_path
        self._sock: Optional[socket.socket] = None
        self._send_lock = threading.Lock()
        self._pending: dict[int, "queue.Queue"] = {}
        self._next_id = 1
        self._stop = False

    def connect(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        last_err: Optional[Exception] = None
        sock = None
        while time.monotonic() < deadline:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self._socket_path)
                break
            except OSError as exc:
                last_err = exc
                sock = None
                time.sleep(0.1)
        if sock is None:
            raise PlayerError(f"could not connect to mpv ipc socket: {last_err}")
        self._sock = sock
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self) -> None:
        buffer = b""
        while not self._stop and self._sock is not None:
            try:
                chunk = self._sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._dispatch(msg)

    def _dispatch(self, msg: dict) -> None:
        request_id = msg.get("request_id")
        if request_id is not None and request_id in self._pending:
            self._pending.pop(request_id).put(msg)

    def command(self, *args, timeout: float = 3.0):
        if self._sock is None:
            raise PlayerError("mpv ipc not connected")
        with self._send_lock:
            req_id = self._next_id
            self._next_id += 1
            response_q: "queue.Queue" = queue.Queue(maxsize=1)
            self._pending[req_id] = response_q
            payload = json.dumps({"command": list(args), "request_id": req_id}) + "\n"
            try:
                self._sock.sendall(payload.encode("utf-8"))
            except OSError as exc:
                self._pending.pop(req_id, None)
                raise PlayerError(f"failed to send mpv command {args}: {exc}") from exc
        try:
            msg = response_q.get(timeout=timeout)
        except queue.Empty as exc:
            self._pending.pop(req_id, None)
            raise PlayerError(f"mpv command timed out: {args}") from exc
        if msg.get("error") != "success":
            raise PlayerError(f"mpv error for {args}: {msg.get('error')}")
        return msg.get("data")

    def close(self) -> None:
        self._stop = True
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass


class PlayerBase(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def load_playlist(self, filepaths: list[str], start_index: int = 0, start_seconds: float = 0.0) -> None: ...
    def play(self) -> None: ...
    def pause(self) -> None: ...
    def toggle_pause(self) -> None: ...
    def next(self) -> None: ...
    def previous(self) -> None: ...
    def seek(self, seconds: float, absolute: bool = True) -> None: ...
    def set_volume(self, percent: int) -> None: ...
    def get_volume(self) -> int: ...
    def get_status(self) -> dict: ...


class MpvPlayer:
    def __init__(self, config):
        self._config = config.audio
        self._process: Optional[subprocess.Popen] = None
        self._ipc: Optional[_MpvIpc] = None
        self._mixer = AlsaMixer(self._config.mixer_control, self._config.mixer_card)

    def start(self) -> None:
        socket_path = self._config.mpv_ipc_socket
        try:
            os.remove(socket_path)
        except FileNotFoundError:
            pass
        args = [
            self._config.mpv_binary,
            "--idle=yes",
            "--no-video",
            "--no-terminal",
            f"--input-ipc-server={socket_path}",
            f"--audio-device=alsa/{self._config.alsa_device}",
            "--volume=100",
            "--volume-max=100",
        ]
        self._process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._ipc = _MpvIpc(socket_path)
        self._ipc.connect()
        self.set_volume(self._config.default_volume)

    def stop(self) -> None:
        if self._ipc is not None:
            self._ipc.close()
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def load_playlist(self, filepaths: list[str], start_index: int = 0, start_seconds: float = 0.0) -> None:
        if not filepaths or self._ipc is None:
            return
        self._ipc.command("loadfile", filepaths[0], "replace")
        for f in filepaths[1:]:
            self._ipc.command("loadfile", f, "append")
        if start_index:
            self._ipc.command("set_property", "playlist-pos", start_index)
        if start_seconds:
            self._ipc.command("seek", start_seconds, "absolute")
        self._ipc.command("set_property", "pause", False)

    def play(self) -> None:
        self._ipc.command("set_property", "pause", False)

    def pause(self) -> None:
        self._ipc.command("set_property", "pause", True)

    def toggle_pause(self) -> None:
        try:
            paused = self._ipc.command("get_property", "pause")
        except PlayerError:
            paused = False
        self._ipc.command("set_property", "pause", not paused)

    def next(self) -> None:
        try:
            self._ipc.command("playlist-next", "weak")
        except PlayerError:
            pass

    def previous(self) -> None:
        try:
            self._ipc.command("playlist-prev", "weak")
        except PlayerError:
            pass

    def seek(self, seconds: float, absolute: bool = True) -> None:
        self._ipc.command("seek", seconds, "absolute" if absolute else "relative")

    def set_volume(self, percent: int) -> None:
        self._mixer.set_percent(percent)

    def get_volume(self) -> int:
        return self._mixer.get_percent()

    def get_status(self) -> dict:
        def prop(name, default=None):
            try:
                return self._ipc.command("get_property", name)
            except PlayerError:
                return default

        paused = bool(prop("pause", True))
        idle = bool(prop("idle-active", False))
        return {
            "playing": (not paused) and (not idle),
            "paused": paused,
            "time_pos": prop("time-pos", 0.0) or 0.0,
            "duration": prop("duration", 0.0) or 0.0,
            "playlist_pos": prop("playlist-pos", 0) or 0,
            "playlist_count": prop("playlist-count", 0) or 0,
            "volume": self.get_volume(),
            "eof": bool(prop("eof-reached", False)),
        }


class StubPlayer:
    """No-op player used in simulate mode or when mpv isn't installed."""

    def __init__(self, config):
        self._volume = config.audio.default_volume
        self._playlist: list[str] = []
        self._index = 0
        self._paused = True
        self._position = 0.0

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def load_playlist(self, filepaths: list[str], start_index: int = 0, start_seconds: float = 0.0) -> None:
        self._playlist = list(filepaths)
        self._index = min(start_index, max(len(filepaths) - 1, 0))
        self._position = start_seconds
        self._paused = False

    def play(self) -> None:
        self._paused = False

    def pause(self) -> None:
        self._paused = True

    def toggle_pause(self) -> None:
        self._paused = not self._paused

    def next(self) -> None:
        if self._index < len(self._playlist) - 1:
            self._index += 1
            self._position = 0.0

    def previous(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._position = 0.0

    def seek(self, seconds: float, absolute: bool = True) -> None:
        self._position = seconds if absolute else self._position + seconds

    def set_volume(self, percent: int) -> None:
        self._volume = max(0, min(100, percent))

    def get_volume(self) -> int:
        return self._volume

    def get_status(self) -> dict:
        return {
            "playing": (not self._paused) and bool(self._playlist),
            "paused": self._paused,
            "time_pos": self._position,
            "duration": 0.0,
            "playlist_pos": self._index,
            "playlist_count": len(self._playlist),
            "volume": self._volume,
            "eof": False,
        }


def create_player(config) -> PlayerBase:
    if config.simulate or shutil.which(config.audio.mpv_binary) is None:
        return StubPlayer(config)
    return MpvPlayer(config)
