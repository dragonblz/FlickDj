from __future__ import annotations

import math
from dataclasses import dataclass

from smartcamera.camera import HandObservation
from smartcamera.gestures import flick_point_from_landmarks


@dataclass(frozen=True)
class ControlHandConfig:
    preferred_handedness: str = "auto"
    lock_max_distance: float = 0.30
    lock_timeout_ms: int = 1000


class ControlHandSelector:
    """Locks onto one control hand and ignores other detected hands."""

    def __init__(self, config: ControlHandConfig | None = None) -> None:
        self.config = config or ControlHandConfig()
        self._locked_point: tuple[float, float] | None = None
        self._last_seen_ms = -10**12

    @property
    def locked(self) -> bool:
        return self._locked_point is not None

    def select(
        self,
        observations: list[HandObservation],
        timestamp_ms: int,
    ) -> HandObservation | None:
        candidates = self._preferred_candidates(observations)
        if not candidates:
            self._unlock_if_stale(timestamp_ms)
            return None

        if self._locked_point is None or self._is_stale(timestamp_ms):
            return self._lock(max(candidates, key=lambda item: item.confidence), timestamp_ms)

        selected = self._closest_locked_candidate(candidates)
        if selected is None:
            return None

        return self._lock(selected, timestamp_ms)

    def reset(self) -> None:
        self._locked_point = None
        self._last_seen_ms = -10**12

    def _preferred_candidates(
        self,
        observations: list[HandObservation],
    ) -> list[HandObservation]:
        preferred = self.config.preferred_handedness.strip().lower()
        if preferred in {"left", "right"}:
            return [item for item in observations if item.handedness == preferred]
        return observations

    def _closest_locked_candidate(
        self,
        candidates: list[HandObservation],
    ) -> HandObservation | None:
        assert self._locked_point is not None

        closest = min(
            candidates,
            key=lambda item: _distance(self._locked_point, flick_point_from_landmarks(item.landmarks)),
        )
        distance = _distance(self._locked_point, flick_point_from_landmarks(closest.landmarks))
        if distance > self.config.lock_max_distance:
            return None
        return closest

    def _lock(self, observation: HandObservation, timestamp_ms: int) -> HandObservation:
        self._locked_point = flick_point_from_landmarks(observation.landmarks)
        self._last_seen_ms = timestamp_ms
        return observation

    def _unlock_if_stale(self, timestamp_ms: int) -> None:
        if self._is_stale(timestamp_ms):
            self.reset()

    def _is_stale(self, timestamp_ms: int) -> bool:
        return timestamp_ms - self._last_seen_ms > self.config.lock_timeout_ms


def _distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])
