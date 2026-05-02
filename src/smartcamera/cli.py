from __future__ import annotations

import argparse
import sys
from pathlib import Path

from smartcamera.app import run
from smartcamera.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control Spotify with webcam hand flicks.")
    parser.add_argument(
        "--env",
        type=Path,
        default=Path(".env"),
        help="Path to the environment config file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.load(args.env)
        return run(settings)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"smartcamera: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
