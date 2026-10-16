"""Pure gesture recognition and cursor-control primitives."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import hypot
from typing import Sequence


@dataclass(frozen=True)
class Point:
    x: float
    y: float


def distance(a: Point, b: Point) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class Gesture(str, Enum):
    IDLE = "READY"
    MOVE = "MOVE"
    LEFT = "LEFT CLICK"
    RIGHT = "RIGHT CLICK"
    SCROLL = "SCROLL"
    PAUSE = "OPEN PALM / PAUSE"


@dataclass(frozen=True)
class Reading:
    gesture: Gesture
    pointer: Point
    pinch_ratio: float
    hand_scale: float


def finger_extended(points: Sequence[Point], tip: int, pip: int, mcp: int) -> bool:
    """Approximate extension using distances, robust to hand rotation."""
    return distance(points[tip], points[mcp]) > distance(points[pip], points[mcp]) * 1.16


def recognize(points: Sequence[Point], pinch_threshold: float = 0.39) -> Reading:
    """Classify a single hand using 21 MediaPipe landmarks.

    Thresholds are heuristic. Distances are normalized by palm width.
    """
    if len(points) != 21:
        raise ValueError("Expected exactly 21 hand landmarks")

    index = finger_extended(points, 8, 6, 5)
    middle = finger_extended(points, 12, 10, 9)
    ring = finger_extended(points, 16, 14, 13)
    pinky = finger_extended(points, 20, 18, 17)
    hand_scale = max(distance(points[5], points[17]), 0.035)
    ix = distance(points[4], points[8]) / hand_scale
    md = distance(points[4], points[12]) / hand_scale
    tip = points[8]

    if index and middle and ring and pinky:
        gesture = Gesture.PAUSE
    elif middle and md < pinch_threshold and md + 0.06 < ix:
        gesture = Gesture.RIGHT
    elif index and ix < pinch_threshold and ix + 0.06 < md:
        gesture = Gesture.LEFT
    elif index and middle and not ring and not pinky:
        gesture = Gesture.SCROLL
    elif index and not middle and not ring:
        gesture = Gesture.MOVE
    else:
        gesture = Gesture.IDLE

    return Reading(gesture, tip, min(ix, md), hand_scale)


@dataclass
class AdaptiveSmoother:
    """Low jitter at rest, responsive motion across larger distances."""
    x: float | None = None
    y: float | None = None

    def reset(self) -> None:
        self.x = self.y = None

    def update(self, target_x: float, target_y: float, screen_width: int, screen_height: int) -> tuple[int, int]:
        target_x = clamp(target_x, 12, screen_width - 13)
        target_y = clamp(target_y, 12, screen_height - 13)
        if self.x is None or self.y is None:
            self.x, self.y = target_x, target_y
        else:
            delta = hypot(target_x - self.x, target_y - self.y)
            alpha = 0.16 + 0.52 * clamp(delta / 260.0, 0, 1)
            self.x += alpha * (target_x - self.x)
            self.y += alpha * (target_y - self.y)
        return round(self.x), round(self.y)


@dataclass
class ClickLatch:
    """One click per pinch, not a click on every video frame."""
    last_action: Gesture = Gesture.IDLE
    last_click_at: float = float("-inf")
    cooldown_s: float = 0.42

    def consume(self, gesture: Gesture, now: float) -> Gesture | None:
        event = None
        if gesture in (Gesture.LEFT, Gesture.RIGHT):
            if gesture != self.last_action and now - self.last_click_at >= self.cooldown_s:
                event = gesture
                self.last_click_at = now
        self.last_action = gesture
        return event

    def reset(self) -> None:
        self.last_action = Gesture.IDLE


@dataclass
class DwellClick:
    """Optional mode: hold an almost-stationary finger to click."""
    anchor: tuple[float, float] | None = None
    started: float = 0
    fired: bool = False
    dwell_s: float = 1.7
    radius_px: float = 24

    def reset(self) -> None:
        self.anchor = None
        self.fired = False
        self.started = 0

    def update(self, pos: tuple[float, float], now: float) -> tuple[bool, float]:
        if self.anchor is None or hypot(pos[0] - self.anchor[0], pos[1] - self.anchor[1]) > self.radius_px:
            self.anchor = pos
            self.started = now
            self.fired = False
            return False, 0.0
        progress = clamp((now - self.started) / self.dwell_s, 0, 1)
        if progress >= 1 and not self.fired:
            self.fired = True
            return True, 1.0
        return False, progress


def map_pointer(point: Point, screen_width: int, screen_height: int, margin: float = 0.12) -> tuple[float, float]:
    """Map center camera active area to the primary monitor."""
    nx = clamp((point.x - margin) / (1 - 2 * margin), 0, 1)
    ny = clamp((point.y - margin) / (1 - 2 * margin), 0, 1)
    return 12 + nx * (screen_width - 25), 12 + ny * (screen_height - 25)
