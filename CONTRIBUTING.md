# Contributing

Thanks for considering a contribution to FlickDJ.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

On Command Prompt, activate with:

```bat
.venv\Scripts\activate.bat
```

## Pull Requests

- Keep changes focused.
- Add or update tests for gesture detection, playback routing, or hand selection behavior.
- Do not commit `.env`, Spotify tokens, virtual environments, generated model files, or screenshots with private information.
- If a gesture behavior changes, update the README tuning section.

## Good First Issues

- Add support for other music apps.
- Add a calibration flow for personal gesture tuning.
- Add an optional tray/background mode.
- Improve visual debugging overlays.
