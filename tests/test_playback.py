from __future__ import annotations

from smartcamera.commands import PlaybackCommand
from smartcamera.playback import PlaybackController
from smartcamera.spotify import SpotifyCommandError


class FakeSpotify:
    def __init__(self, has_client_id: bool = True, error: Exception | None = None) -> None:
        self._has_client_id = has_client_id
        self.error = error
        self.commands: list[PlaybackCommand] = []

    def has_client_id(self) -> bool:
        return self._has_client_id

    def skip(self, command: PlaybackCommand) -> None:
        self.commands.append(command)
        if self.error:
            raise self.error


def test_playback_uses_spotify_first() -> None:
    spotify = FakeSpotify()
    sent_media_keys: list[PlaybackCommand] = []
    controller = PlaybackController(spotify, media_key_sender=sent_media_keys.append)

    result = controller.execute(PlaybackCommand.NEXT)

    assert result.ok is True
    assert result.method == "spotify"
    assert spotify.commands == [PlaybackCommand.NEXT]
    assert sent_media_keys == []


def test_playback_falls_back_to_media_keys_on_spotify_error() -> None:
    spotify = FakeSpotify(error=SpotifyCommandError(403, "Spotify command failed"))
    sent_media_keys: list[PlaybackCommand] = []
    controller = PlaybackController(spotify, media_key_sender=sent_media_keys.append)

    result = controller.execute(PlaybackCommand.PREVIOUS)

    assert result.ok is True
    assert result.method == "media-key"
    assert sent_media_keys == [PlaybackCommand.PREVIOUS]


def test_playback_falls_back_when_client_id_missing() -> None:
    spotify = FakeSpotify(has_client_id=False)
    sent_media_keys: list[PlaybackCommand] = []
    controller = PlaybackController(spotify, media_key_sender=sent_media_keys.append)

    result = controller.execute(PlaybackCommand.NEXT)

    assert result.ok is True
    assert result.method == "media-key"
    assert spotify.commands == []
    assert sent_media_keys == [PlaybackCommand.NEXT]
