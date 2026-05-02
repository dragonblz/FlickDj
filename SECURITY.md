# Security

## Supported Versions

FlickDJ is currently pre-1.0. Security fixes should target the latest version on `main`.

## Reporting a Vulnerability

Please open a private security advisory on GitHub if available. If not, open an issue with a minimal description and avoid posting secrets, tokens, or private Spotify app credentials.

## Local Secrets

Never commit:

- `.env`
- Spotify client ids/secrets
- OAuth token cache files
- webcam screenshots containing private information

FlickDJ uses Spotify OAuth PKCE and stores tokens locally under `%USERPROFILE%\.flickdj`.
