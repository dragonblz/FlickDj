from __future__ import annotations

from enum import Enum


class PlaybackCommand(str, Enum):
    NEXT = "next"
    PREVIOUS = "previous"
