import unittest
from airmouse.core import (AdaptiveSmoother, ClickLatch, DwellClick, Gesture,
                           Point, clamp, map_pointer, recognize)


class CoreTests(unittest.TestCase):
    def test_clamp(self):
        self.assertEqual(clamp(-1, 0, 1), 0)
        self.assertEqual(clamp(2, 0, 1), 1)
        self.assertEqual(clamp(.4, 0, 1), .4)

    def test_map_pointer_bounds(self):
        self.assertEqual(map_pointer(Point(-8, -8), 1920, 1080), (12, 12))
        self.assertEqual(map_pointer(Point(9, 9), 1920, 1080), (1907, 1067))

    def test_click_latch_single_event_per_pinch(self):
        latch = ClickLatch()
        self.assertEqual(latch.consume(Gesture.LEFT, 1), Gesture.LEFT)
        self.assertIsNone(latch.consume(Gesture.LEFT, 2))
        self.assertIsNone(latch.consume(Gesture.MOVE, 2.1))
        self.assertEqual(latch.consume(Gesture.LEFT, 2.2), Gesture.LEFT)
        self.assertEqual(latch.consume(Gesture.RIGHT, 3), Gesture.RIGHT)

    def test_click_cooldown(self):
        latch = ClickLatch(cooldown_s=.4)
        self.assertEqual(latch.consume(Gesture.LEFT, 1), Gesture.LEFT)
        latch.consume(Gesture.IDLE, 1.05)
        self.assertIsNone(latch.consume(Gesture.LEFT, 1.1))

    def test_dwell_click_once_until_movement(self):
        d = DwellClick(dwell_s=1, radius_px=10)
        self.assertEqual(d.update((80, 80), 1), (False, 0.0))
        self.assertFalse(d.update((81, 80), 1.5)[0])
        self.assertEqual(d.update((81, 80), 2.1), (True, 1))
        self.assertFalse(d.update((81, 80), 3.0)[0])
        self.assertFalse(d.update((99, 80), 3.1)[0])
        self.assertEqual(d.update((99, 80), 4.2), (True, 1))

    def test_smoother(self):
        smoother = AdaptiveSmoother()
        self.assertEqual(smoother.update(100, 100, 1920, 1080), (100, 100))
        second = smoother.update(400, 100, 1920, 1080)
        self.assertGreater(second[0], 100)
        self.assertLess(second[0], 400)
        smoother.reset()
        self.assertEqual(smoother.update(200, 150, 1920, 1080), (200, 150))

    def test_wrong_landmark_count(self):
        with self.assertRaises(ValueError):
            recognize([Point(0, 0)] * 4)

    def _hand(self, fingers=(False, False, False, False), thumb_target=None):
        p = [Point(.5, .7) for _ in range(21)]
        p[0] = Point(.50, .85)
        p[4] = Point(.18, .57)
        p[5], p[9], p[13], p[17] = [Point(x, .66) for x in (.34, .45, .56, .67)]
        for extended, tip, pip, mcp in zip(fingers, (8,12,16,20), (6,10,14,18), (5,9,13,17)):
            x = p[mcp].x
            p[pip] = Point(x, .52)
            p[tip] = Point(x, .37 if extended else .61)
        if thumb_target is not None:
            p[4] = p[thumb_target]
        return p

    def test_move_gesture(self):
        self.assertEqual(recognize(self._hand((True, False, False, False))).gesture, Gesture.MOVE)

    def test_open_palm_pause(self):
        self.assertEqual(recognize(self._hand((True, True, True, True))).gesture, Gesture.PAUSE)

    def test_two_finger_scroll(self):
        self.assertEqual(recognize(self._hand((True, True, False, False))).gesture, Gesture.SCROLL)

    def test_left_pinch(self):
        self.assertEqual(recognize(self._hand((True, False, False, False), 8)).gesture, Gesture.LEFT)

    def test_right_pinch(self):
        self.assertEqual(recognize(self._hand((True, True, False, False), 12)).gesture, Gesture.RIGHT)


if __name__ == "__main__":
    unittest.main()
