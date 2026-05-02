from __future__ import annotations

from types import SimpleNamespace

from smartcamera.commands import PlaybackCommand
from smartcamera.gestures import GestureConfig, GestureDetector, GestureDirection


def landmarks_at(x: float, y: float) -> list[SimpleNamespace]:
    landmarks = [SimpleNamespace(x=x, y=y) for _ in range(21)]
    landmarks[0] = SimpleNamespace(x=x, y=y)
    landmarks[5] = SimpleNamespace(x=x, y=y)
    landmarks[17] = SimpleNamespace(x=x, y=y)
    return landmarks


def landmarks_with_stable_wrist(
    wrist_x: float,
    wrist_y: float,
    fingertip_x: float,
    fingertip_y: float,
) -> list[SimpleNamespace]:
    landmarks = [SimpleNamespace(x=wrist_x, y=wrist_y) for _ in range(21)]
    for index in (8, 12, 16, 20):
        landmarks[index] = SimpleNamespace(x=fingertip_x, y=fingertip_y)
    return landmarks


def detector() -> GestureDetector:
    return GestureDetector(
        GestureConfig(
            cooldown_ms=950,
            window_ms=350,
            min_horizontal_displacement=0.07,
            min_horizontal_velocity=0.85,
            max_vertical_ratio=1.25,
            min_samples=3,
        )
    )


def feed_path(detector: GestureDetector, xs: list[float], ys: list[float] | None = None):
    ys = ys or [0.5] * len(xs)
    first_event = None
    for timestamp_ms in (-300, -200, -100, 0):
        detector.add_landmarks(landmarks_at(xs[0], ys[0]), timestamp_ms=timestamp_ms)
    for index, (x, y) in enumerate(zip(xs, ys)):
        event = detector.add_landmarks(landmarks_at(x, y), timestamp_ms=50 + index * 50)
        if first_event is None and event is not None:
            first_event = event
    return first_event


def test_right_slap_triggers_next_once() -> None:
    event = feed_path(detector(), [0.20, 0.25, 0.30])

    assert event is not None
    assert event.direction is GestureDirection.RIGHT
    assert event.command is PlaybackCommand.NEXT


def test_left_slap_triggers_previous_once() -> None:
    event = feed_path(detector(), [0.72, 0.67, 0.62])

    assert event is not None
    assert event.direction is GestureDirection.LEFT
    assert event.command is PlaybackCommand.PREVIOUS


def test_slow_hand_movement_does_not_trigger() -> None:
    event = None
    subject = detector()
    for index, x in enumerate([0.20, 0.24, 0.27, 0.30, 0.33]):
        event = subject.add_landmarks(landmarks_at(x, 0.5), timestamp_ms=index * 250)

    assert event is None


def test_vertical_movement_does_not_trigger() -> None:
    event = feed_path(
        detector(),
        [0.20, 0.25, 0.30],
        ys=[0.35, 0.49, 0.63],
    )

    assert event is None


def test_cooldown_prevents_repeated_skip() -> None:
    subject = detector()
    first = feed_path(subject, [0.20, 0.25, 0.30])

    second = None
    for offset, x in enumerate([0.20, 0.25, 0.30], start=1):
        second = subject.add_landmarks(landmarks_at(x, 0.5), timestamp_ms=200 + offset * 50)

    assert first is not None
    assert second is None


def test_wrist_flick_can_trigger_after_snap_back() -> None:
    event = feed_path(detector(), [0.40, 0.46, 0.52, 0.48])

    assert event is not None
    assert event.direction is GestureDirection.RIGHT


def test_rotation_flick_triggers_when_wrist_stays_stable() -> None:
    subject = detector()
    event = None
    frames = [
        landmarks_with_stable_wrist(0.36, 0.56, 0.38, 0.38),
        landmarks_with_stable_wrist(0.36, 0.56, 0.45, 0.43),
        landmarks_with_stable_wrist(0.36, 0.56, 0.53, 0.48),
    ]
    for timestamp_ms in (-300, -200, -100, 0):
        subject.add_landmarks(frames[0], timestamp_ms=timestamp_ms)
    for index, landmarks in enumerate(frames):
        detected = subject.add_landmarks(landmarks, timestamp_ms=50 + index * 50)
        if event is None and detected is not None:
            event = detected

    assert event is not None
    assert event.direction is GestureDirection.RIGHT


def test_hand_leaving_camera_edge_does_not_trigger() -> None:
    subject = detector()
    event = None
    for timestamp_ms in (-300, -200, -100, 0):
        subject.add_landmarks(landmarks_at(0.18, 0.5), timestamp_ms=timestamp_ms)
    for index, x in enumerate([0.18, 0.10, 0.03]):
        event = subject.add_landmarks(landmarks_at(x, 0.5), timestamp_ms=50 + index * 50)

    assert event is None


def test_return_to_ready_position_does_not_trigger_until_hand_settles() -> None:
    subject = detector()
    first = feed_path(subject, [0.40, 0.46, 0.52])

    return_event = None
    for index, x in enumerate([0.52, 0.46, 0.40], start=1):
        return_event = subject.add_landmarks(
            landmarks_at(x, 0.5),
            timestamp_ms=1100 + index * 50,
        )

    assert first is not None
    assert return_event is None


def test_can_flick_again_after_settling() -> None:
    subject = detector()
    first = feed_path(subject, [0.40, 0.46, 0.52])

    for index, timestamp_ms in enumerate([1300, 1400, 1500, 1600]):
        subject.add_landmarks(landmarks_at(0.40, 0.5), timestamp_ms=timestamp_ms)
    second = None
    for index, x in enumerate([0.40, 0.46, 0.52]):
        second = subject.add_landmarks(
            landmarks_at(x, 0.5),
            timestamp_ms=1700 + index * 50,
        )

    assert first is not None
    assert second is not None
    assert second.command is PlaybackCommand.NEXT
