from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


@dataclass(frozen=True)
class Settings:
    spotify_client_id: str
    spotify_redirect_uri: str
    camera_index: int
    camera_mirror: bool
    control_hand: str
    hand_lock_max_distance: float
    gesture_cooldown_ms: int
    enable_media_key_fallback: bool
    previous_media_key_presses: int
    gesture_min_horizontal_displacement: float
    gesture_min_horizontal_velocity: float
    gesture_max_vertical_ratio: float
    gesture_window_ms: int
    gesture_min_confidence: float
    token_cache_path: Path
    hand_landmarker_model_path: Path | None

    @classmethod
    def load(cls, env_path: Path | None = None) -> "Settings":
        _load_env_file(env_path or Path(".env"))

        return cls(
            spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID", "").strip(),
            spotify_redirect_uri=os.getenv(
                "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8765/callback"
            ).strip(),
            camera_index=_get_int("CAMERA_INDEX", 0),
            camera_mirror=_get_bool("CAMERA_MIRROR", True),
            control_hand=os.getenv("CONTROL_HAND", "auto").strip().lower(),
            hand_lock_max_distance=_get_float("HAND_LOCK_MAX_DISTANCE", 0.30),
            gesture_cooldown_ms=_get_int("GESTURE_COOLDOWN_MS", 950),
            enable_media_key_fallback=_get_bool("ENABLE_MEDIA_KEY_FALLBACK", True),
            previous_media_key_presses=max(1, _get_int("PREVIOUS_MEDIA_KEY_PRESSES", 1)),
            gesture_min_horizontal_displacement=_get_float(
                "GESTURE_MIN_HORIZONTAL_DISPLACEMENT", 0.07
            ),
            gesture_min_horizontal_velocity=_get_float(
                "GESTURE_MIN_HORIZONTAL_VELOCITY", 0.85
            ),
            gesture_max_vertical_ratio=_get_float("GESTURE_MAX_VERTICAL_RATIO", 1.25),
            gesture_window_ms=_get_int("GESTURE_WINDOW_MS", 350),
            gesture_min_confidence=_get_float("GESTURE_MIN_CONFIDENCE", 0.50),
            token_cache_path=Path.home() / ".flickdj" / "spotify_token.json",
            hand_landmarker_model_path=(
                Path(os.environ["HAND_LANDMARKER_MODEL_PATH"])
                if os.getenv("HAND_LANDMARKER_MODEL_PATH")
                else None
            ),
        )
