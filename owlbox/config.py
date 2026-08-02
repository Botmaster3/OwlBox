"""Loads config/config.yaml (falling back to config.example.yaml) into typed sections."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    admin_password: str = ""
    secret_key: str = "change-me"


@dataclass
class AudioConfig:
    alsa_device: str = "hw:0,0"
    mixer_control: str = "Digital"
    mixer_card: str = "0"
    default_volume: int = 60
    volume_step: int = 4
    mpv_binary: str = "mpv"
    mpv_ipc_socket: str = "/tmp/owlbox-mpv.sock"


@dataclass
class RfidConfig:
    reader: str = "mfrc522"
    spi_bus: int = 0
    spi_device: int = 0
    reset_pin: int = 25
    poll_interval: float = 0.15
    missing_reads_to_remove: int = 5


@dataclass
class GpioConfig:
    button_next: int = 5
    button_prev: int = 6
    encoder_clk: int = 17
    encoder_dt: int = 27
    encoder_switch: int = 22
    bounce_time: float = 0.05
    shutdown_hold_seconds: float = 4


@dataclass
class PlaybackConfig:
    restart_track_after_seconds: float = 3
    position_save_interval: float = 5


@dataclass
class PathsConfig:
    media_dir: str = "media"
    database: str = "data/owlbox.db"


@dataclass
class Config:
    simulate: bool = False
    paths: PathsConfig = field(default_factory=PathsConfig)
    web: WebConfig = field(default_factory=WebConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    rfid: RfidConfig = field(default_factory=RfidConfig)
    gpio: GpioConfig = field(default_factory=GpioConfig)
    playback: PlaybackConfig = field(default_factory=PlaybackConfig)

    @property
    def media_dir(self) -> Path:
        p = Path(self.paths.media_dir)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def database_path(self) -> Path:
        p = Path(self.paths.database)
        return p if p.is_absolute() else REPO_ROOT / p


def _merge(defaults: dict, overrides: dict) -> dict:
    merged = dict(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _section(cls, data: dict) -> Any:
    known = {f for f in cls.__dataclass_fields__}
    return cls(**{k: v for k, v in data.items() if k in known})


def load_config(path: str | Path | None = None) -> Config:
    candidates = []
    if path:
        candidates.append(Path(path))
    else:
        candidates.append(REPO_ROOT / "config" / "config.yaml")
        candidates.append(REPO_ROOT / "config" / "config.example.yaml")

    data: dict = {}
    for candidate in candidates:
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            break

    env_override = os.environ.get("OWLBOX_SIMULATE")
    if env_override is not None:
        data["simulate"] = env_override.lower() in ("1", "true", "yes")

    cfg = Config(
        simulate=bool(data.get("simulate", False)),
        paths=_section(PathsConfig, data.get("paths", {})),
        web=_section(WebConfig, data.get("web", {})),
        audio=_section(AudioConfig, data.get("audio", {})),
        rfid=_section(RfidConfig, data.get("rfid", {})),
        gpio=_section(GpioConfig, data.get("gpio", {})),
        playback=_section(PlaybackConfig, data.get("playback", {})),
    )
    return cfg
