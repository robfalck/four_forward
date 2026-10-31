"""Persistent player settings stored as JSON in the user's home dir."""

from __future__ import annotations

import json
from pathlib import Path

from .constants import AMBIENT_VOLUME

_SAVE_PATH = Path.home() / ".four_forward_settings.json"


def load_volume() -> float:
    try:
        return max(0.0, min(1.0, float(json.loads(_SAVE_PATH.read_text())["volume"])))
    except Exception:
        return AMBIENT_VOLUME


def save_volume(volume: float) -> None:
    try:
        _SAVE_PATH.write_text(json.dumps({"volume": round(volume, 3)}))
    except Exception:
        pass
