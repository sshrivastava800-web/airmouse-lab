# AirMouse Lab 🖐️

**Maintained by Sameer Shrivastava**

**[Author](AUTHORS.md) · [GitHub](https://github.com/sshrivastava800-web)**

An experimental, privacy-first, webcam-controlled desktop mouse built with Python, OpenCV, MediaPipe, and PyAutoGUI. Control the cursor with an index finger, pinch to click, and scroll with two raised fingers.

> **Status:** prototype with automated unit tests. The gesture engine has been tested without hardware; actual webcam control still needs testing on a Windows computer. Not a certified accessibility product.

## Key features

- **Move:** point with index finger, other fingers curled.
- **Left click:** pinch thumb and index finger.
- **Right click:** pinch thumb and middle finger.
- **Scroll:** extend index + middle and move vertically.
- **Temporary pause:** open palm.
- **Safety lock:** press P in the camera preview to arm/pause (starts locked).
- **Optional dwell click:** press D to toggle; hold a pointing finger still ~1.7 seconds to click.
- **Adaptive cursor smoothing:** limits small hand jitter while responding to larger movement.
- **Privacy:** camera frames are processed locally in memory. No uploads, tracking, or saved recordings.

## Run on Windows

1. Install **Python 3.11**, enabling the **Add Python to PATH** option.
2. Clone this repository or download and extract its ZIP from the green Code menu.
3. Double-click **run_windows.bat** to set up dependencies and launch the preview.
4. Allow webcam access. Press **P** in the preview window to enable mouse control.
5. Press **P** to pause; **Q** or **Esc** to exit.

Alternatively, open a terminal in the project folder and run:

    py -3.11 -m venv .venv
    .venv\Scripts\activate
    python -m pip install -r requirements.txt
    python -m airmouse

Optional camera selection: **python -m airmouse --camera 1**. Other flags: **--no-mirror**, **--dwell**.

## Technology

Webcam/OpenCV → 21 hand landmarks/MediaPipe → gesture state machine and smoothing → PyAutoGUI cursor control → OpenCV preview/HUD.

The logic in **airmouse/core.py** has no webcam or GUI dependencies and can be tested separately.

## Automated tests

    python -m unittest discover -s tests -v

Twelve unit tests exercise gesture classification, click cooldown, dwell timing, and pointer smoothing. The GitHub Actions workflow runs these checks on commits and pull requests.

## Safety

- The program starts with mouse movement disabled; press P deliberately to arm it.
- PyAutoGUI's upper-left screen-corner fail-safe remains enabled.
- Keep the camera preview accessible, and do not use this prototype for safety-critical work.
- Camera recognition and gestures can be imperfect depending on lighting, hand pose, and camera angle.
- Keyboard shortcuts require focus on the camera preview window.

## Author and attribution

**Sameer Shrivastava** — Project creator, concept lead, and maintainer. The initial implementation and documentation were produced with AI assistance. See **[AUTHORS.md](AUTHORS.md)** and **[MIT License](LICENSE)**.
