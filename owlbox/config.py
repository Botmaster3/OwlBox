"""Loads config/config.yaml (falling back to config.example.yaml) into typed sections."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 5000
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
    # Short confirmation chime on RFID scans (chip erkannt/unbekannt/Funktions-
    # Chip) plus Start/Stop, played via `aplay` alongside mpv rather than
    # through it - see feedback.py. Toggle in Einstellungen; needs `aplay`
    # (alsa-utils).
    chime_enabled: bool = True
    # Chimes share the hardware ALSA mixer with the story, so the engine
    # briefly sets the mixer to this fraction of max_volume for the chime's
    # duration and restores the real volume right after - keeps chimes at a
    # consistent, quiet level regardless of how loud the story is currently
    # playing.
    chime_volume_ratio: float = 0.15


@dataclass
class RfidConfig:
    reader: str = "mfrc522"
    # Software (bit-banged) SPI on plain GPIOs - see Mfrc522Reader for why:
    # both of the Pi's hardware SPI buses are already claimed by other parts
    # of the standard hardware (the display and its touch controller, the
    # HiFiBerry's I2S audio).
    sck_pin: int = 4
    mosi_pin: int = 16
    miso_pin: int = 15
    cs_pin: int = 14
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
    # How long the next/prev button must be held before it starts fast-forwarding/
    # rewinding instead of jumping to the next/previous track on release.
    seek_hold_seconds: float = 0.4
    # Seconds seeked per repeat tick while a button is held past seek_hold_seconds.
    seek_step_seconds: float = 10
    # Display backlight, for dimming (see docs/hardware.md) - wired through a
    # driver transistor, not straight to 3.3V. Required hardware, not optional;
    # only set to None/0 if the backlight is (against the standard build)
    # still hardwired straight to 3.3V.
    backlight_pin: Optional[int] = 13
    # Second rotary encoder, dedicated to brightness - required hardware,
    # same KY-040 wiring pattern as the volume encoder.
    brightness_encoder_clk: int = 23
    brightness_encoder_dt: int = 12
    # Brightness change (percent) per encoder detent.
    brightness_step: int = 5


@dataclass
class PlaybackConfig:
    restart_track_after_seconds: float = 3
    position_save_interval: float = 5
    # Minutes spent paused (via the pause button/tag or by turning the volume
    # down to 0) before the kiosk shows a sleeping-owl screen. Configurable in
    # Einstellungen; 0 disables it. Waking up (volume raised, play/pause
    # pressed, or an RFID tag scanned) resumes the track from the exact
    # position it was paused at.
    auto_sleep_minutes: float = 20
    # Seconds over which the volume gently fades out before the sleep timer
    # (not auto-sleep, which starts from an already-paused/silent state) forces
    # a pause - a soft transition instead of an abrupt cut. 0 disables fading.
    sleep_fade_seconds: float = 60


@dataclass
class NetworkConfig:
    # Recovery hotspot (see docs/hardware.md) - shown on the kiosk display and admin
    # Home whenever it's active, so it doesn't need to be memorized in advance.
    hotspot_ssid: str = "OwlBox-Setup"
    hotspot_password: str = "owlbox-setup"
    # How long WiFi has to be enabled-but-disconnected before the hotspot kicks in.
    hotspot_after_seconds: float = 60
    # While the hotspot is up, how often to briefly check whether a known network
    # has come back into range.
    hotspot_retry_interval_seconds: float = 120


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
    network: NetworkConfig = field(default_factory=NetworkConfig)

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
        network=_section(NetworkConfig, data.get("network", {})),
    )
    return cfg
