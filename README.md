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

## Run on Windows (Python 3.15)

1. Install the latest **64-bit Python 3.15** from [python.org](https://www.python.org/downloads/). Enable the Python launcher / Add Python to PATH when offered.
2. Download this repository using **Code → Download ZIP**, then extract it. If you have an older copy, download a fresh ZIP to obtain the updated files.
3. Double-click **run_windows.bat**. It selects Python 3.15, creates a private `.venv`, updates pip, installs dependencies, and starts the camera preview.
4. On the **first** run, the official [MediaPipe Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) model downloads once over HTTPS to your user cache. Subsequent runs can be offline.
5. Allow Windows camera access. Focus the preview and press **P** to arm the pointer. Press **P** to lock, **Q** or **Esc** to quit.

Alternatively, in Command Prompt inside the project folder:

```bat
py -3.15 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m airmouse
```

For a different camera: `python -m airmouse --camera 1` (run in an activated venv or use `.venv\Scripts\python.exe`).
Other flags: `--no-mirror`, `--dwell`, `--model C:\\path\\to\\hand_landmarker.task` for offline/custom model use.

**Upgrading from Python 3.11:** the Windows launcher automatically replaces an old project-specific `.venv` so old binary packages do not break the new interpreter. Do not copy an old `.venv` into the new download.

**Compatibility:** the code now uses the MediaPipe **Tasks Hand Landmarker** API rather than the removed `mp.solutions` API. The GitHub Actions matrix runs pure-unit tests on 3.13–3.15 and checks Windows dependency installation on 3.14–3.15. Automated checks do not replace a real webcam test. If package installation fails on a newly released interpreter, check CI and the error message before attempting to downgrade.

## Technology

Webcam/OpenCV → MediaPipe Tasks Hand Landmarker (21 landmarks) → gesture state machine and smoothing → PyAutoGUI cursor control → OpenCV preview/HUD.

The logic in **airmouse/core.py** has no webcam or GUI dependencies and can be tested separately.

## Automated tests

    python -m unittest discover -s tests -v

Twelve original unit tests exercise gesture classification, click cooldown, dwell timing, and pointer smoothing. New adapter tests verify Tasks landmark conversion, strictly increasing video timestamps, and offline model selection. GitHub Actions checks these on commits and pull requests.

## Safety

- The program starts with mouse movement disabled; press P deliberately to arm it.
- PyAutoGUI's upper-left screen-corner fail-safe remains enabled.
- Keep the camera preview accessible, and do not use this prototype for safety-critical work.
- Camera recognition and gestures can be imperfect depending on lighting, hand pose, and camera angle.
- The first launch downloads only the public hand-landmarker model; webcam images stay local in memory and are not uploaded.
- Keyboard shortcuts require focus on the camera preview window.

## Author and attribution

**Sameer Shrivastava** — Project creator, concept lead, and maintainer. The initial implementation and documentation were produced with AI assistance. See **[AUTHORS.md](AUTHORS.md)** and **[MIT License](LICENSE)**.
