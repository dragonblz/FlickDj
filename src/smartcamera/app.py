from __future__ import annotations

import time
from dataclasses import dataclass

from smartcamera.camera import HandTracker, _cv2
from smartcamera.config import Settings
from smartcamera.gestures import GestureConfig, GestureDetector
from smartcamera.hand_selector import ControlHandConfig, ControlHandSelector
from smartcamera.media_keys import send_media_key
from smartcamera.playback import PlaybackController, PlaybackResult
from smartcamera.spotify import SpotifyClient, SpotifyConfig


HAND_CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),
)


@dataclass
class RuntimeStatus:
    hand_status: str = "No hand"
    last_command: str = "None"
    playback_status: str = "Ready"
    fallback_status: str = "Enabled"


def run(settings: Settings) -> int:
    cv2 = _cv2()
    tracker = HandTracker(
        min_confidence=settings.gesture_min_confidence,
        model_path=settings.hand_landmarker_model_path,
    )
    detector = GestureDetector(
        GestureConfig(
            cooldown_ms=settings.gesture_cooldown_ms,
            window_ms=settings.gesture_window_ms,
            min_horizontal_displacement=settings.gesture_min_horizontal_displacement,
            min_horizontal_velocity=settings.gesture_min_horizontal_velocity,
            max_vertical_ratio=settings.gesture_max_vertical_ratio,
            min_confidence=settings.gesture_min_confidence,
        )
    )
    hand_selector = ControlHandSelector(
        ControlHandConfig(
            preferred_handedness=settings.control_hand,
            lock_max_distance=settings.hand_lock_max_distance,
        )
    )
    spotify = SpotifyClient(
        SpotifyConfig(
            client_id=settings.spotify_client_id,
            redirect_uri=settings.spotify_redirect_uri,
            token_cache_path=settings.token_cache_path,
        )
    )
    playback = PlaybackController(
        spotify=spotify,
        enable_media_key_fallback=settings.enable_media_key_fallback,
        media_key_sender=lambda command: send_media_key(
            command,
            previous_press_count=settings.previous_media_key_presses,
        ),
    )
    status = RuntimeStatus(
        fallback_status="Enabled" if settings.enable_media_key_fallback else "Disabled"
    )

    capture = cv2.VideoCapture(settings.camera_index)
    if not capture.isOpened():
        tracker.close()
        raise RuntimeError(f"Could not open camera index {settings.camera_index}.")

    window_name = "FlickDJ"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 540)

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                status.hand_status = "Camera frame unavailable"
                _draw_overlay(cv2, frame, status)
                continue
            if settings.camera_mirror:
                frame = cv2.flip(frame, 1)

            timestamp_ms = int(time.monotonic() * 1000)
            observations = tracker.process_bgr(frame, timestamp_ms)
            observation = hand_selector.select(observations, timestamp_ms)
            _draw_hands(cv2, frame, observations, observation)
            if observation is None:
                detector.reset()
                if observations:
                    status.hand_status = f"Ignoring {len(observations)} other hand(s)"
                else:
                    status.hand_status = "No hand"
            else:
                label = observation.handedness or "hand"
                status.hand_status = (
                    f"Control {label} {observation.confidence:.2f}"
                    f" ({len(observations)} seen)"
                )
                event = detector.add_landmarks(
                    observation.landmarks,
                    timestamp_ms=timestamp_ms,
                    confidence=observation.confidence,
                )
                if event is not None:
                    result = playback.execute(event.command)
                    _apply_result(status, result)

            _draw_overlay(cv2, frame, status)
            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in {27, ord("q")}:
                return 0
    finally:
        capture.release()
        tracker.close()
        cv2.destroyAllWindows()


def _apply_result(status: RuntimeStatus, result: PlaybackResult) -> None:
    status.last_command = f"{result.command.value} via {result.method}"
    status.playback_status = result.message if result.ok else f"Failed: {result.message}"


def _draw_hands(cv2, frame, observations, control_observation) -> None:
    if frame is None:
        return

    for observation in observations:
        is_control = observation is control_observation
        line_color = (40, 230, 255) if is_control else (130, 130, 130)
        point_color = (0, 255, 120) if is_control else (190, 190, 190)
        line_thickness = 3 if is_control else 2
        point_radius = 4 if is_control else 3
        _draw_hand(
            cv2,
            frame,
            observation.landmarks,
            line_color,
            point_color,
            line_thickness,
            point_radius,
        )


def _draw_hand(
    cv2,
    frame,
    landmarks,
    line_color: tuple[int, int, int],
    point_color: tuple[int, int, int],
    line_thickness: int,
    point_radius: int,
) -> None:
    height, width = frame.shape[:2]
    points = [_landmark_to_pixel(landmark, width, height) for landmark in landmarks]

    for start, end in HAND_CONNECTIONS:
        if start >= len(points) or end >= len(points):
            continue
        cv2.line(frame, points[start], points[end], line_color, line_thickness, cv2.LINE_AA)

    for point in points:
        cv2.circle(frame, point, point_radius, point_color, -1, cv2.LINE_AA)


def _landmark_to_pixel(landmark, width: int, height: int) -> tuple[int, int]:
    x = min(max(float(landmark.x), 0.0), 1.0)
    y = min(max(float(landmark.y), 0.0), 1.0)
    return int(x * (width - 1)), int(y * (height - 1))


def _draw_overlay(cv2, frame, status: RuntimeStatus) -> None:
    if frame is None:
        return

    lines = [
        "FlickDJ - press q or Esc to quit",
        f"Detection: {status.hand_status}",
        f"Last command: {status.last_command}",
        f"Playback: {status.playback_status}",
        f"Media key fallback: {status.fallback_status}",
    ]
    x = 18
    y = 30
    for line in lines:
        cv2.putText(
            frame,
            line,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 0),
            4,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            line,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        y += 28
