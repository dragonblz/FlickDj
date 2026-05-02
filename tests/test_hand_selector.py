from __future__ import annotations

from types import SimpleNamespace

from smartcamera.camera import HandObservation
from smartcamera.hand_selector import ControlHandConfig, ControlHandSelector


def hand(
    x: float,
    y: float = 0.5,
    confidence: float = 0.9,
    handedness: str | None = None,
) -> HandObservation:
    landmarks = [SimpleNamespace(x=x, y=y) for _ in range(21)]
    for index in (8, 12, 16, 20):
        landmarks[index] = SimpleNamespace(x=x, y=y)
    return HandObservation(
        landmarks=landmarks,
        confidence=confidence,
        handedness=handedness,
    )


def test_selector_locks_first_hand() -> None:
    selector = ControlHandSelector()
    selected = selector.select([hand(0.4)], timestamp_ms=0)

    assert selected is not None
    assert selected.landmarks[8].x == 0.4
    assert selector.locked is True


def test_selector_ignores_far_other_hand_while_locked() -> None:
    selector = ControlHandSelector(ControlHandConfig(lock_max_distance=0.2))
    selector.select([hand(0.4)], timestamp_ms=0)

    selected = selector.select([hand(0.8, confidence=1.0)], timestamp_ms=100)

    assert selected is None
    assert selector.locked is True


def test_selector_tracks_closest_hand_not_highest_confidence_while_locked() -> None:
    selector = ControlHandSelector(ControlHandConfig(lock_max_distance=0.2))
    selector.select([hand(0.4)], timestamp_ms=0)

    selected = selector.select(
        [
            hand(0.42, confidence=0.7),
            hand(0.75, confidence=1.0),
        ],
        timestamp_ms=100,
    )

    assert selected is not None
    assert selected.landmarks[8].x == 0.42


def test_selector_reacquires_after_timeout() -> None:
    selector = ControlHandSelector(
        ControlHandConfig(lock_max_distance=0.2, lock_timeout_ms=500)
    )
    selector.select([hand(0.4)], timestamp_ms=0)

    selected = selector.select([hand(0.8)], timestamp_ms=800)

    assert selected is not None
    assert selected.landmarks[8].x == 0.8


def test_selector_can_prefer_handedness() -> None:
    selector = ControlHandSelector(ControlHandConfig(preferred_handedness="right"))

    selected = selector.select(
        [
            hand(0.3, confidence=1.0, handedness="left"),
            hand(0.7, confidence=0.7, handedness="right"),
        ],
        timestamp_ms=0,
    )

    assert selected is not None
    assert selected.handedness == "right"
