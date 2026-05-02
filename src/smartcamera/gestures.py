from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol

from smartcamera.commands import PlaybackCommand


class LandmarkLike(Protocol):
    x: float
    y: float


class GestureDirection(str, Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class GestureEvent:
    direction: GestureDirection
    command: PlaybackCommand
    timestamp_ms: int
    dx: float
    dy: float
    velocity_x: float


@dataclass(frozen=True)
class HandSample:
    timestamp_ms: int
    x: float
    y: float
    confidence: float
    in_frame: bool


@dataclass(frozen=True)
class GestureConfig:
    cooldown_ms: int = 950
    window_ms: int = 350
    min_horizontal_displacement: float = 0.07
    min_horizontal_velocity: float = 0.85
    max_vertical_ratio: float = 1.25
    min_confidence: float = 0.50
    min_samples: int = 3
    min_pair_ms: int = 40
    edge_margin: float = 0.06


class GestureDetector:
    """Detects short left/right hand flicks over normalized hand landmarks."""

    def __init__(self, config: GestureConfig | None = None) -> None:
        self.config = config or GestureConfig()
        self._samples: deque[HandSample] = deque()
        self._last_trigger_ms = -10**12

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    def reset(self) -> None:
        self._samples.clear()
        self._last_trigger_ms = -10**12

    def add_landmarks(
        self,
        landmarks: Iterable[LandmarkLike],
        timestamp_ms: int,
        confidence: float = 1.0,
    ) -> GestureEvent | None:
        if confidence < self.config.min_confidence:
            self._trim(timestamp_ms)
            return None

        sample = self._sample_from_landmarks(list(landmarks), timestamp_ms, confidence)
        self._samples.append(sample)
        self._trim(timestamp_ms)
        return self._detect(timestamp_ms)

    def _sample_from_landmarks(
        self, landmarks: list[LandmarkLike], timestamp_ms: int, confidence: float
    ) -> HandSample:
        if not landmarks:
            raise ValueError("At least one landmark is required")

        x, y = flick_point_from_landmarks(landmarks)
        in_frame = (
            self.config.edge_margin <= x <= 1.0 - self.config.edge_margin
            and self.config.edge_margin <= y <= 1.0 - self.config.edge_margin
        )
        return HandSample(
            timestamp_ms=timestamp_ms,
            x=x,
            y=y,
            confidence=confidence,
            in_frame=in_frame,
        )

    def _trim(self, timestamp_ms: int) -> None:
        cutoff = timestamp_ms - self.config.window_ms
        while self._samples and self._samples[0].timestamp_ms < cutoff:
            self._samples.popleft()

    def _detect(self, timestamp_ms: int) -> GestureEvent | None:
        if len(self._samples) < self.config.min_samples:
            return None
        if timestamp_ms - self._last_trigger_ms < self.config.cooldown_ms:
            return None

        best = self._best_flick_pair()
        if best is None:
            return None

        dx, dy, velocity_x = best
        direction = GestureDirection.RIGHT if dx > 0 else GestureDirection.LEFT
        command = direction_to_command(direction)
        self._last_trigger_ms = timestamp_ms
        self._samples.clear()
        return GestureEvent(
            direction=direction,
            command=command,
            timestamp_ms=timestamp_ms,
            dx=dx,
            dy=dy,
            velocity_x=velocity_x,
        )

    def _best_flick_pair(self) -> tuple[float, float, float] | None:
        best: tuple[float, float, float] | None = None
        best_speed = 0.0
        samples = list(self._samples)

        for start_index, start in enumerate(samples[:-1]):
            for end in samples[start_index + 1 :]:
                elapsed_ms = end.timestamp_ms - start.timestamp_ms
                if elapsed_ms < self.config.min_pair_ms:
                    continue
                if not start.in_frame or not end.in_frame:
                    continue
                if self._moves_toward_camera_edge(start, end):
                    continue

                elapsed_s = elapsed_ms / 1000.0
                dx = end.x - start.x
                dy = end.y - start.y
                abs_dx = abs(dx)
                velocity_x = dx / elapsed_s
                speed = abs(velocity_x)

                if abs_dx < self.config.min_horizontal_displacement:
                    continue
                if speed < self.config.min_horizontal_velocity:
                    continue
                if abs(dy) > abs_dx * self.config.max_vertical_ratio:
                    continue
                if speed > best_speed:
                    best = (dx, dy, velocity_x)
                    best_speed = speed

        return best

    def _moves_toward_camera_edge(self, start: HandSample, end: HandSample) -> bool:
        return (
            end.x < start.x
            and end.x <= self.config.edge_margin * 2
        ) or (
            end.x > start.x
            and end.x >= 1.0 - self.config.edge_margin * 2
        )


def direction_to_command(direction: GestureDirection) -> PlaybackCommand:
    if direction is GestureDirection.RIGHT:
        return PlaybackCommand.NEXT
    return PlaybackCommand.PREVIOUS


def flick_point_from_landmarks(landmarks: list[LandmarkLike]) -> tuple[float, float]:
    if not landmarks:
        raise ValueError("At least one landmark is required")

    # A wrist-only point misses rotation-style flicks where the wrist stays
    # mostly anchored and the fingers sweep sideways.
    flick_indexes = [idx for idx in (8, 12, 16, 20) if idx < len(landmarks)]
    if not flick_indexes:
        flick_indexes = [0]

    x = sum(landmarks[idx].x for idx in flick_indexes) / len(flick_indexes)
    y = sum(landmarks[idx].y for idx in flick_indexes) / len(flick_indexes)
    return x, y
