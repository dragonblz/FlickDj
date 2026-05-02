from __future__ import annotations

import time
from pathlib import Path

from smartcamera.commands import PlaybackCommand
from smartcamera.spotify import SpotifyClient, SpotifyConfig, SpotifyCommandError


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self.payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, dict]] = []
        self.posts: list[tuple[str, dict]] = []
        self.request_responses: list[FakeResponse] = []
        self.post_responses: list[FakeResponse] = []

    def request(self, method: str, url: str, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.request_responses.pop(0)

    def post(self, url: str, data: dict, **kwargs):
        self.posts.append((url, data))
        return self.post_responses.pop(0)


def spotify_client(tmp_path: Path, session: FakeSession) -> SpotifyClient:
    client = SpotifyClient(
        SpotifyConfig(
            client_id="client-id",
            redirect_uri="http://127.0.0.1:8765/callback",
            token_cache_path=tmp_path / "token.json",
        ),
        session=session,
        browser_open=lambda url: True,
    )
    client._token = {"access_token": "old-token", "expires_at": time.time() + 3600}
    return client


def test_skip_next_sends_spotify_endpoint(tmp_path: Path) -> None:
    session = FakeSession()
    session.request_responses = [FakeResponse(204)]
    client = spotify_client(tmp_path, session)

    client.skip(PlaybackCommand.NEXT)

    method, url, kwargs = session.requests[0]
    assert method == "POST"
    assert url == "https://api.spotify.com/v1/me/player/next"
    assert kwargs["headers"]["Authorization"] == "Bearer old-token"


def test_skip_previous_sends_spotify_endpoint(tmp_path: Path) -> None:
    session = FakeSession()
    session.request_responses = [FakeResponse(204)]
    client = spotify_client(tmp_path, session)

    client.skip(PlaybackCommand.PREVIOUS)

    assert session.requests[0][1] == "https://api.spotify.com/v1/me/player/previous"


def test_unauthorized_request_refreshes_token_and_retries(tmp_path: Path) -> None:
    session = FakeSession()
    session.request_responses = [FakeResponse(401), FakeResponse(204)]
    session.post_responses = [
        FakeResponse(200, {"access_token": "new-token", "expires_in": 3600})
    ]
    client = spotify_client(tmp_path, session)
    client._token["refresh_token"] = "refresh-token"

    client.skip(PlaybackCommand.NEXT)

    assert session.posts[0][1]["grant_type"] == "refresh_token"
    assert session.requests[1][2]["headers"]["Authorization"] == "Bearer new-token"


def test_non_success_response_raises_command_error(tmp_path: Path) -> None:
    session = FakeSession()
    session.request_responses = [
        FakeResponse(403, {"error": {"message": "Forbidden"}})
    ]
    client = spotify_client(tmp_path, session)

    try:
        client.skip(PlaybackCommand.NEXT)
    except SpotifyCommandError as exc:
        assert exc.status_code == 403
        assert "Spotify rejected the playback command" in str(exc)
    else:
        raise AssertionError("Expected SpotifyCommandError")
