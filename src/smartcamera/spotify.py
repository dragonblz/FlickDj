from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import requests

from smartcamera.commands import PlaybackCommand


AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE_URL = "https://api.spotify.com/v1"
SCOPE = "user-modify-playback-state"


class SpotifyError(RuntimeError):
    pass


class SpotifyAuthError(SpotifyError):
    pass


class SpotifyCommandError(SpotifyError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str
    redirect_uri: str
    token_cache_path: Path


class SpotifyClient:
    def __init__(
        self,
        config: SpotifyConfig,
        session: requests.Session | None = None,
        browser_open=webbrowser.open,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.browser_open = browser_open
        self._token: dict[str, Any] | None = None

    def has_client_id(self) -> bool:
        return bool(self.config.client_id)

    def skip(self, command: PlaybackCommand) -> None:
        endpoint = {
            PlaybackCommand.NEXT: "/me/player/next",
            PlaybackCommand.PREVIOUS: "/me/player/previous",
        }[command]
        self._request("POST", endpoint)

    def _request(self, method: str, endpoint: str) -> requests.Response:
        token = self.get_access_token()
        response = self.session.request(
            method,
            f"{API_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if response.status_code == 401:
            token = self.get_access_token(force_refresh=True)
            response = self.session.request(
                method,
                f"{API_BASE_URL}{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
        if response.status_code not in {200, 202, 204}:
            raise SpotifyCommandError(response.status_code, _response_message(response))
        return response

    def get_access_token(self, force_refresh: bool = False) -> str:
        if not self.config.client_id:
            raise SpotifyAuthError("SPOTIFY_CLIENT_ID is missing.")

        token = self._token if self._token is not None else self._load_token()
        if token and not force_refresh and not _is_expired(token):
            self._token = token
            return str(token["access_token"])

        if token and token.get("refresh_token"):
            refreshed = self._refresh_token(str(token["refresh_token"]))
            if "refresh_token" not in refreshed:
                refreshed["refresh_token"] = token["refresh_token"]
            self._save_token(refreshed)
            self._token = refreshed
            return str(refreshed["access_token"])

        authorized = self._authorize()
        self._save_token(authorized)
        self._token = authorized
        return str(authorized["access_token"])

    def _authorize(self) -> dict[str, Any]:
        verifier = _pkce_verifier()
        challenge = _pkce_challenge(verifier)
        state = secrets.token_urlsafe(16)
        redirect = urllib.parse.urlparse(self.config.redirect_uri)
        server = HTTPServer((redirect.hostname or "127.0.0.1", redirect.port or 8765), _OAuthHandler)
        server.auth_code = None
        server.auth_error = None
        server.expected_state = state

        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": self.config.redirect_uri,
            "scope": SCOPE,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
        }
        self.browser_open(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")
        server.handle_request()
        server.server_close()

        if server.auth_error:
            raise SpotifyAuthError(str(server.auth_error))
        if not server.auth_code:
            raise SpotifyAuthError("Spotify authorization did not return a code.")

        response = self.session.post(
            TOKEN_URL,
            data={
                "client_id": self.config.client_id,
                "grant_type": "authorization_code",
                "code": server.auth_code,
                "redirect_uri": self.config.redirect_uri,
                "code_verifier": verifier,
            },
            timeout=10,
        )
        if response.status_code != 200:
            raise SpotifyAuthError(_response_message(response))
        return _with_expiry(response.json())

    def _refresh_token(self, refresh_token: str) -> dict[str, Any]:
        response = self.session.post(
            TOKEN_URL,
            data={
                "client_id": self.config.client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=10,
        )
        if response.status_code != 200:
            raise SpotifyAuthError(_response_message(response))
        return _with_expiry(response.json())

    def _load_token(self) -> dict[str, Any] | None:
        path = self.config.token_cache_path
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_token(self, token: dict[str, Any]) -> None:
        path = self.config.token_cache_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(token, indent=2), encoding="utf-8")


class _OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        state = params.get("state", [""])[0]
        if state != self.server.expected_state:
            self.server.auth_error = "Spotify OAuth state mismatch."
        elif "error" in params:
            self.server.auth_error = params["error"][0]
        else:
            self.server.auth_code = params.get("code", [""])[0]

        body = b"SmartCamera Spotify login complete. You can close this tab."
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _pkce_verifier() -> str:
    return secrets.token_urlsafe(64)


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _with_expiry(token: dict[str, Any]) -> dict[str, Any]:
    expires_in = int(token.get("expires_in", 3600))
    token["expires_at"] = time.time() + expires_in - 60
    return token


def _is_expired(token: dict[str, Any]) -> bool:
    return float(token.get("expires_at", 0)) <= time.time()


def _response_message(response: requests.Response) -> str:
    if response.status_code == 403:
        return "Spotify rejected the playback command. Falling back if enabled."

    try:
        data = response.json()
    except ValueError:
        return f"Spotify request failed with HTTP {response.status_code}: {response.text}"

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if error:
            return str(error)
    return f"Spotify request failed with HTTP {response.status_code}"
