from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlretrieve


HAND_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


@dataclass(frozen=True)
class HandObservation:
    landmarks: list[object]
    confidence: float
    handedness: str | None = None


class HandTracker:
    def __init__(
        self,
        min_confidence: float = 0.5,
        model_path: Path | None = None,
    ) -> None:
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError(
                "mediapipe is required for camera hand tracking. Install with `pip install -e .`."
            ) from exc

        self._mp = mp
        model = _ensure_model(model_path)
        base_options = mp.tasks.BaseOptions(model_asset_path=str(model))
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def process_bgr(self, frame, timestamp_ms: int) -> list[HandObservation]:
        cv2 = _cv2()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.hand_landmarks:
            return []

        observations: list[HandObservation] = []
        for index, landmarks in enumerate(result.hand_landmarks):
            confidence = 1.0
            handedness = None
            if index < len(result.handedness) and result.handedness[index]:
                category = result.handedness[index][0]
                confidence = float(category.score)
                handedness = str(category.category_name).lower()
            observations.append(
                HandObservation(
                    landmarks=list(landmarks),
                    confidence=confidence,
                    handedness=handedness,
                )
            )
        return observations

    def close(self) -> None:
        self._landmarker.close()


def _cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python is required for the camera preview. Install with `pip install -e .`."
        ) from exc
    return cv2


def _ensure_model(model_path: Path | None) -> Path:
    path = model_path or Path.home() / ".flickdj" / "models" / "hand_landmarker.task"
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        urlretrieve(HAND_LANDMARKER_MODEL_URL, path)
    except Exception as exc:
        raise RuntimeError(
            "Could not download the MediaPipe Hand Landmarker model. "
            "Set HAND_LANDMARKER_MODEL_PATH to a local hand_landmarker.task file."
        ) from exc
    return path
