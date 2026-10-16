"""AirMouse Lab: webcam -> hand landmarks -> safe desktop cursor gestures.

Camera frames stay in memory; the app never saves video or sends telemetry.
"""
from __future__ import annotations

import argparse
import math
import platform
import sys
import time

from .core import AdaptiveSmoother, ClickLatch, DwellClick, Gesture, Point, map_pointer, recognize


def imports():
    try:
        import cv2
        import mediapipe as mp
        import pyautogui
    except ImportError as exc:
        raise SystemExit("Missing dependency. Install with: python -m pip install -r requirements.txt") from exc
    if not hasattr(mp, "solutions"):
        raise SystemExit("This project requires MediaPipe 0.10.21 (legacy hand-tracking API). Install requirements.txt with Python 3.11.")
    return cv2, mp, pyautogui


def draw_hud(cv2, image, gesture: str, is_armed: bool, dwell: bool, show_help: bool,
             fps: float, dwell_progress: float, pointer_xy: tuple[int, int] | None,
             points, active_margin: float = 0.12) -> None:
    h, w = image.shape[:2]
    overlay = image.copy()
    cv2.rectangle(overlay, (0, 0), (w, 118), (16, 23, 37), -1)
    cv2.addWeighted(overlay, 0.76, image, 0.24, 0, image)
    c_cyan = (235, 211, 96)
    c_white = (245, 246, 247)
    cv2.putText(image, "AIR MOUSE LAB", (20, 37), cv2.FONT_HERSHEY_SIMPLEX, 0.9, c_white, 2, cv2.LINE_AA)
    cv2.putText(image, "ARMED" if is_armed else "PAUSED", (w - 137, 35), cv2.FONT_HERSHEY_SIMPLEX,
                0.78, (90, 225, 130) if is_armed else (100, 155, 255), 2, cv2.LINE_AA)
    cv2.putText(image, f"Gesture: {gesture}", (22, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.60, c_cyan, 2, cv2.LINE_AA)
    cv2.putText(image, f"FPS: {fps:.0f}   Dwell: {'ON' if dwell else 'OFF'}", (22, 98),
                cv2.FONT_HERSHEY_SIMPLEX, 0.53, c_white, 1, cv2.LINE_AA)

    left, top = int(w * active_margin), int(h * active_margin)
    right, bottom = int(w * (1 - active_margin)), int(h * (1 - active_margin))
    cv2.rectangle(image, (left, top), (right, bottom), (80, 120, 140), 1)

    if points is not None:
        tip = points[8]
        px, py = int(tip.x * w), int(tip.y * h)
        cv2.circle(image, (px, py), 15, c_cyan, 2)
        if dwell_progress > 0:
            cv2.ellipse(image, (px, py), (27, 27), -90, 0, int(360 * dwell_progress),
                        (85, 220, 113), 4)
        cv2.putText(image, "TRACK", (px + 20, py - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.43, c_white, 1)

    if show_help:
        instructions = [
            "POINT index finger   -> move cursor",
            "PINCH thumb + index  -> left click",
            "PINCH thumb + middle -> right click",
            "TWO fingers vertical -> scroll",
            "OPEN palm           -> temporary pause",
            "P = lock/unlock control, D = dwell click",
            "H = show/hide help, Q or ESC = quit",
            "Privacy: all processing stays on this device",
        ]
        y0 = h - 19 * len(instructions) - 16
        cv2.rectangle(image, (10, y0 - 18), (min(w - 10, 600), h - 5), (14, 22, 35), -1)
        for i, item in enumerate(instructions):
            cv2.putText(image, item, (19, y0 + i * 19), cv2.FONT_HERSHEY_SIMPLEX,
                        0.47, c_white, 1, cv2.LINE_AA)
    elif pointer_xy:
        cv2.putText(image, f"Cursor {pointer_xy[0]}, {pointer_xy[1]}", (15, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, c_white, 1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Control your desktop mouse with a webcam and hand gestures.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--no-mirror", action="store_true", help="Disable mirrored selfie-view")
    parser.add_argument("--dwell", action="store_true", help="Enable optional dwell-to-click mode")
    args = parser.parse_args(argv)
    cv2, mp, pyautogui = imports()
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0
    try:
        screen_width, screen_height = pyautogui.size()
    except Exception as exc:
        raise SystemExit(f"Desktop cursor not available: {exc}") from exc
    if screen_width < 80 or screen_height < 80:
        raise SystemExit("Screen resolution unexpectedly small")

    backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
    cam = cv2.VideoCapture(args.camera, backend)
    if not cam.isOpened():
        raise SystemExit(f"Could not open webcam #{args.camera}. Check camera permissions or try --camera 1.")
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    smooth = AdaptiveSmoother()
    click_latch = ClickLatch()
    dwell = DwellClick()
    armed, dwell_enabled, show_help = False, args.dwell, True
    previous_scroll_y: float | None = None
    scroll_buffer = 0.0
    previous_frame_time = time.monotonic()
    last_tracking_time = previous_frame_time
    pointer_xy: tuple[int, int] | None = None
    start_hint = "PRESS P TO ARM"

    print("AirMouse Lab ready. Press P in the camera window to enable cursor control; Q to quit.")
    try:
        with mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1,
                                      model_complexity=1, min_detection_confidence=0.65,
                                      min_tracking_confidence=0.6) as hands:
            while True:
                ok, frame = cam.read()
                if not ok:
                    print("Webcam frame read failed. Exiting safely.", file=sys.stderr)
                    break
                if not args.no_mirror:
                    frame = cv2.flip(frame, 1)
                frame = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_LINEAR)
                now = time.monotonic()
                dt = max(now - previous_frame_time, 1e-4)
                fps = 1.0 / dt
                previous_frame_time = now

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                detected = hands.process(rgb)
                rgb.flags.writeable = True
                points = None
                gesture_text = "NO HAND"
                progress = 0.0
                if detected.multi_hand_landmarks:
                    hand = detected.multi_hand_landmarks[0]
                    points = [Point(p.x, p.y) for p in hand.landmark]
                    reading = recognize(points)
                    gesture_text = reading.gesture.value
                    last_tracking_time = now
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, hand, mp.solutions.hands.HAND_CONNECTIONS,
                        mp.solutions.drawing_styles.get_default_hand_landmarks_style(),
                        mp.solutions.drawing_styles.get_default_hand_connections_style(),
                    )
                    if armed:
                        event = click_latch.consume(reading.gesture, now)
                        if reading.gesture in (Gesture.MOVE, Gesture.LEFT, Gesture.RIGHT):
                            sx, sy = map_pointer(reading.pointer, screen_width, screen_height)
                            pointer_xy = smooth.update(sx, sy, screen_width, screen_height)
                            pyautogui.moveTo(*pointer_xy, duration=0)
                            if event == Gesture.LEFT:
                                pyautogui.click(button="left")
                            elif event == Gesture.RIGHT:
                                pyautogui.click(button="right")
                            if dwell_enabled and reading.gesture == Gesture.MOVE:
                                should_click, progress = dwell.update(pointer_xy, now)
                                if should_click:
                                    pyautogui.click(button="left")
                            else:
                                dwell.reset()
                            previous_scroll_y = None
                            scroll_buffer = 0
                        elif reading.gesture == Gesture.SCROLL:
                            dwell.reset()
                            if previous_scroll_y is not None:
                                scroll_buffer += (previous_scroll_y - reading.pointer.y) / 0.035
                                wheel_units = math.trunc(scroll_buffer)
                                if wheel_units:
                                    pyautogui.scroll(max(-5, min(5, wheel_units)))
                                    scroll_buffer -= wheel_units
                            previous_scroll_y = reading.pointer.y
                        else:
                            dwell.reset()
                            smooth.reset()
                            previous_scroll_y = None
                            scroll_buffer = 0
                    else:
                        click_latch.reset()
                        dwell.reset()
                        smooth.reset()
                        previous_scroll_y = None
                        scroll_buffer = 0
                else:
                    click_latch.reset()
                    dwell.reset()
                    previous_scroll_y = None
                    scroll_buffer = 0
                    if now - last_tracking_time > 0.25:
                        smooth.reset()

                draw_hud(cv2, frame, gesture_text if armed else start_hint, armed,
                         dwell_enabled, show_help, fps, progress, pointer_xy, points)
                cv2.imshow("AirMouse Lab | Q=Quit P=Arm/Pause D=Dwell H=Help", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("p"):
                    armed = not armed
                    start_hint = "LOCKED / PRESS P TO ARM"
                    click_latch.reset()
                    dwell.reset()
                    smooth.reset()
                    previous_scroll_y = None
                elif key == ord("d"):
                    dwell_enabled = not dwell_enabled
                    dwell.reset()
                elif key == ord("h"):
                    show_help = not show_help
    except pyautogui.FailSafeException:
        print("Emergency stop: cursor reached top-left safety corner.")
    except KeyboardInterrupt:
        print("Stopped by keyboard interrupt.")
    finally:
        cam.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
