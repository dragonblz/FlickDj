from __future__ import annotations

import ctypes
import sys
import time

from smartcamera.commands import PlaybackCommand


VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
KEYEVENTF_KEYUP = 0x0002


class MediaKeyError(RuntimeError):
    pass


def send_media_key(
    command: PlaybackCommand,
    previous_press_count: int = 1,
) -> None:
    if sys.platform != "win32":
        raise MediaKeyError("Media key fallback is only implemented for Windows.")

    vk_code = {
        PlaybackCommand.NEXT: VK_MEDIA_NEXT_TRACK,
        PlaybackCommand.PREVIOUS: VK_MEDIA_PREV_TRACK,
    }[command]

    user32 = ctypes.windll.user32
    for _ in range(media_key_press_count(command, previous_press_count)):
        _press_media_key(user32, vk_code)
        time.sleep(0.08)


def media_key_press_count(
    command: PlaybackCommand,
    previous_press_count: int = 1,
) -> int:
    if command is PlaybackCommand.PREVIOUS:
        return max(1, previous_press_count)
    return 1


def _press_media_key(user32, vk_code: int) -> None:
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
