"""Google OAuth 2.0 authentication for Docs and Gmail."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose",
]

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "token.json"


def _credentials_path() -> Path:
    """Prefer local credentials.json, then parent workspace folder."""
    candidates = [
        BASE_DIR / "credentials.json",
        BASE_DIR.parent / "credentials.json",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


CREDENTIALS_FILE = _credentials_path()


def get_credentials() -> Credentials:
    """
    Return valid Google OAuth credentials.

    - Loads token.json if present and still valid.
    - Refreshes the token when expired (if a refresh token exists).
    - Otherwise opens a browser for the OAuth consent flow and saves token.json.
    """
    creds: Credentials | None = None
    credentials_file = _credentials_path()

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not credentials_file.exists():
            raise FileNotFoundError(
                f"Missing credentials.json. Place it in {BASE_DIR} or "
                f"{BASE_DIR.parent} (downloaded from Google Cloud Console)."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_file), SCOPES
        )
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


if __name__ == "__main__":
    print("Starting Google OAuth flow...")
    print(f"Credentials: {_credentials_path()}")
    print(f"Token will be saved to: {TOKEN_FILE}")
    credentials = get_credentials()
    print("Authentication successful.")
    print(f"Token saved to {TOKEN_FILE}")
    if credentials.expiry:
        print(f"Token expiry: {credentials.expiry}")
