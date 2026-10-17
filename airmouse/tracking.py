"""MediaPipe Tasks hand-tracking adapter for modern Python.

The official model is downloaded once; camera frames are processed locally.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
from urllib.error import URLError
from urllib.request import urlopen

from .core import Point

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_NAME = "hand_landmarker.task"
MAX_MODEL_BYTES = 64 * 1024 * 1024
MIN_MODEL_BYTES = 100_000

# MediaPipe hand skeleton, kept locally to avoid deprecated drawing APIs.
HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
)


def default_model_path() -> Path:
    """Put the downloaded model in a per-user cache, not in the repo."""
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return root / "AirMouseLab" / "models" / MODEL_NAME
    return Path(os.getenv("XDG_CACHE_HOME") or (Path.home() / ".cache")) / "airmouse-lab" / MODEL_NAME


def ensure_model(model_path: Path | None = None) -> Path:
    """Use a local model or download the official bundle once.

    Providing --model never triggers a network download.
    """
    if model_path is not None:
        path = Path(model_path).expanduser()
        if not path.is_file():
            raise RuntimeError(f"Model not found: {path}. Remove --model to download the default model.")
        return path

    path = default_model_path()
    if path.is_file() and path.stat().st_size >= MIN_MODEL_BYTES:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading the official MediaPipe hand model once to {path} ...")
    temp_name = None
    try:
        with urlopen(MODEL_URL, timeout=30) as response:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix="hand_", suffix=".tmp", delete=False) as tmp:
                temp_name = tmp.name
                downloaded = 0
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > MAX_MODEL_BYTES:
                        raise RuntimeError("The hand model download is unexpectedly large; aborted.")
                    tmp.write(chunk)
                if downloaded < MIN_MODEL_BYTES:
                    raise RuntimeError("The hand model download was incomplete.")
        os.replace(temp_name, path)
    except (OSError, URLError, RuntimeError) as exc:
        raise RuntimeError(
            f"Cannot download the hand-tracking model from {MODEL_URL}: {exc}. "
            "Check your connection, or supply an existing model using --model PATH."
        ) from exc
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


class HandTracker:
    """Wrap MediaPipe Tasks VIDEO mode and return 21 Point objects."""

    def __init__(self, mp, model_path: Path):
        vision = mp.tasks.vision
        options = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=0.65,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self._mp = mp
        self._detector = vision.HandLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._detector.close()

    def process(self, rgb_frame, timestamp_ms: int) -> list[Point] | None:
        # The Task API requires strictly increasing timestamps.
        timestamp_ms = max(int(timestamp_ms), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._detector.detect_for_video(image, timestamp_ms)
        if not result.hand_landmarks:
            return None
        return [Point(p.x, p.y) for p in result.hand_landmarks[0]]


def draw_hand(cv2, frame, points: list[Point]) -> None:
    """Draw 21 landmarks and their connections without mp.solutions."""
    height, width = frame.shape[:2]
    pixels = [(int(p.x * width), int(p.y * height)) for p in points]
    for first, second in HAND_CONNECTIONS:
        cv2.line(frame, pixels[first], pixels[second], (70, 190, 245), 2, cv2.LINE_AA)
    for xy in pixels:
        cv2.circle(frame, xy, 4, (55, 230, 125), -1, cv2.LINE_AA)
