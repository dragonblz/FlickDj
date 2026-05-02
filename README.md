# FlickDJ

Control Spotify with a webcam hand flick.

FlickDJ watches your hand through your camera, draws a live hand skeleton overlay, and turns sharp left/right flicks into music controls. It is built for the kind of demo people instantly understand: hold up your hand, flick right for next track, flick left for previous track.

## Why It Is Fun

- **No keyboard required**: change tracks without touching your desk.
- **Computer vision overlay**: see the detected hand bones in real time.
- **Control-hand lock**: ignores other hands while tracking your active hand.
- **Spotify-first control**: uses the Spotify Web API when available.
- **Practical fallback**: can send Windows media keys if Spotify API control fails.
- **Hackable tuning**: all gesture thresholds live in `.env`.

## Demo Behavior

| Gesture | Action |
| --- | --- |
| Flick right | Next song |
| Flick left | Previous song |
| Press `q` or `Esc` | Quit |

The active control hand is drawn brighter. Ignored hands are drawn in gray.

## Install

FlickDJ is Windows-first. Use Python 3.10, 3.11, or 3.12 for the smoothest MediaPipe install.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
copy .env.example .env
```

## Spotify Setup

1. Create an app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard).
2. Add this redirect URI exactly:

```text
http://127.0.0.1:8765/callback
```

3. Put the app client id in `.env`:

```text
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8765/callback
```

FlickDJ uses Spotify OAuth PKCE and stores tokens locally under:

```text
%USERPROFILE%\.flickdj\spotify_token.json
```

Do not commit `.env` or token files.

## Run

```powershell
flickdj
```

The old command still works too:

```powershell
smartcamera
```

On first run, FlickDJ downloads the MediaPipe Hand Landmarker model to:

```text
%USERPROFILE%\.flickdj\models\hand_landmarker.task
```

To provide the model manually:

```text
HAND_LANDMARKER_MODEL_PATH=C:\path\to\hand_landmarker.task
```

## Configuration

Default `.env` tuning:

```text
CAMERA_INDEX=0
CAMERA_MIRROR=true
CONTROL_HAND=auto
HAND_LOCK_MAX_DISTANCE=0.30
GESTURE_COOLDOWN_MS=950
ENABLE_MEDIA_KEY_FALLBACK=true
PREVIOUS_MEDIA_KEY_PRESSES=1

GESTURE_WINDOW_MS=350
GESTURE_MIN_HORIZONTAL_DISPLACEMENT=0.07
GESTURE_MIN_HORIZONTAL_VELOCITY=0.85
GESTURE_MAX_VERTICAL_RATIO=1.25
GESTURE_MIN_CONFIDENCE=0.50
```

Useful tweaks:

- Set `CONTROL_HAND=left` or `CONTROL_HAND=right` if auto-lock grabs the wrong hand.
- Raise `GESTURE_MIN_HORIZONTAL_VELOCITY` to reduce accidental triggers.
- Lower `GESTURE_MIN_HORIZONTAL_DISPLACEMENT` if real flicks are missed.
- Set `PREVIOUS_MEDIA_KEY_PRESSES=2` only if previous-track fallback restarts the current song instead of moving back.

## How It Works

FlickDJ uses OpenCV for the webcam preview, MediaPipe for hand landmarks, a fingertip-edge flick detector for sharp left/right movement, Spotify OAuth PKCE for API playback control, and Windows media keys as fallback.

Objects are ignored because they do not produce hand landmarks. If two hands are visible, FlickDJ locks onto one control hand and ignores the other until the lock times out.

## Tests

```powershell
python -m pytest -q
```

Current coverage includes gesture detection, hand selection, edge-frame rejection, Spotify API routing, token refresh retry, and media-key fallback behavior.

## Roadmap

- Calibration mode that learns your personal flick style.
- Tray/background mode.
- Packaging into a Windows executable.
- Support for other music players.
- Optional on-screen gesture trail for better demos.

## License

MIT. See [LICENSE](LICENSE).

## Disclaimer

FlickDJ is an independent project and is not affiliated with Spotify.
