"""Task API adapter tests without camera, network, or MediaPipe installation."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from airmouse.tracking import HAND_CONNECTIONS, HandTracker, ensure_model


class DummyDetector:
    def __init__(self, result):
        self.result = result
        self.timestamps = []
        self.closed = False

    def detect_for_video(self, image, timestamp_ms):
        self.timestamps.append(timestamp_ms)
        return self.result

    def close(self):
        self.closed = True


class TrackingTests(unittest.TestCase):
    def test_connections_reference_21_landmarks(self):
        self.assertGreaterEqual(len(HAND_CONNECTIONS), 20)
        self.assertTrue(all(0 <= index < 21 for edge in HAND_CONNECTIONS for index in edge))

    def test_explicit_missing_model_never_downloads(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('airmouse.tracking.urlopen') as download:
                with self.assertRaisesRegex(RuntimeError, 'Model not found'):
                    ensure_model(Path(directory) / 'missing.task')
                download.assert_not_called()

    def test_explicit_model_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.task'
            path.write_bytes(b'example model')
            with patch('airmouse.tracking.urlopen') as download:
                self.assertEqual(ensure_model(path), path)
                download.assert_not_called()

    def test_video_timestamps_monotonic_and_landmarks_converted(self):
        points = [SimpleNamespace(x=i / 20, y=(20 - i) / 20) for i in range(21)]
        detector = DummyDetector(SimpleNamespace(hand_landmarks=[points]))
        vision = SimpleNamespace(
            RunningMode=SimpleNamespace(VIDEO='VIDEO'),
            HandLandmarkerOptions=lambda **kwargs: kwargs,
            HandLandmarker=SimpleNamespace(create_from_options=lambda opts: detector),
        )
        mp = SimpleNamespace(
            tasks=SimpleNamespace(vision=vision, BaseOptions=lambda **kwargs: kwargs),
            Image=lambda **kwargs: kwargs,
            ImageFormat=SimpleNamespace(SRGB='SRGB'),
        )
        with HandTracker(mp, Path('model.task')) as tracker:
            result = tracker.process('rgb-frame', 100)
            tracker.process('rgb-frame', 100)
        self.assertEqual(len(result), 21)
        self.assertAlmostEqual(result[8].x, 0.4)
        self.assertEqual(detector.timestamps, [100, 101])
        self.assertTrue(detector.closed)


if __name__ == '__main__':
    unittest.main()
