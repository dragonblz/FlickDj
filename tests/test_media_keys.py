from __future__ import annotations

from smartcamera.commands import PlaybackCommand
from smartcamera.media_keys import media_key_press_count


def test_next_media_key_is_single_press() -> None:
    assert media_key_press_count(PlaybackCommand.NEXT) == 1


def test_previous_media_key_is_double_press() -> None:
    assert media_key_press_count(PlaybackCommand.PREVIOUS, previous_press_count=2) == 2


def test_previous_media_key_defaults_to_single_press() -> None:
    assert media_key_press_count(PlaybackCommand.PREVIOUS) == 1
