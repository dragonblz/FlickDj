from __future__ import annotations

from dataclasses import dataclass

from smartcamera.commands import PlaybackCommand
from smartcamera.media_keys import MediaKeyError, send_media_key
from smartcamera.spotify import SpotifyClient, SpotifyError


@dataclass(frozen=True)
class PlaybackResult:
    command: PlaybackCommand
    method: str
    ok: bool
    message: str


class PlaybackController:
    def __init__(
        self,
        spotify: SpotifyClient,
        enable_media_key_fallback: bool = True,
        media_key_sender=send_media_key,
    ) -> None:
        self.spotify = spotify
        self.enable_media_key_fallback = enable_media_key_fallback
        self.media_key_sender = media_key_sender

    def execute(self, command: PlaybackCommand) -> PlaybackResult:
        if self.spotify.has_client_id():
            try:
                self.spotify.skip(command)
                return PlaybackResult(command, "spotify", True, "Spotify API command sent")
            except SpotifyError as exc:
                if not self.enable_media_key_fallback:
                    return PlaybackResult(command, "spotify", False, str(exc))
                fallback_reason = str(exc)
        else:
            fallback_reason = "SPOTIFY_CLIENT_ID is missing"

        if not self.enable_media_key_fallback:
            return PlaybackResult(command, "none", False, fallback_reason)

        try:
            self.media_key_sender(command)
            return PlaybackResult(
                command,
                "media-key",
                True,
                f"Media key fallback sent after: {fallback_reason}",
            )
        except MediaKeyError as exc:
            return PlaybackResult(command, "media-key", False, str(exc))
