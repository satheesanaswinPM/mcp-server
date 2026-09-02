"""Google OAuth 2.0 authentication for Docs and Gmail.

Local: credentials.json + token.json (browser flow once).
Railway: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET / GOOGLE_REFRESH_TOKEN env vars.
"""

from __future__ import annotations

import json
import os
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
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"


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


def _env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _credentials_from_env() -> Credentials | None:
    """Build refreshable credentials from Railway / hosted secrets."""
    client_id = _env("GOOGLE_CLIENT_ID")
    client_secret = _env("GOOGLE_CLIENT_SECRET")
    refresh_token = _env("GOOGLE_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        return None
    token_uri = _env("GOOGLE_TOKEN_URI") or DEFAULT_TOKEN_URI
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


def _is_hosted() -> bool:
    return bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_PROJECT_ID")
        or _env("GOOGLE_REFRESH_TOKEN")
    )


def get_credentials() -> Credentials:
    """
    Return valid Google OAuth credentials.

    Priority:
    1. Env-based refresh token (Railway / production)
    2. token.json on disk (local)
    3. Local browser OAuth via credentials.json (local only)
    """
    env_creds = _credentials_from_env()
    if env_creds is not None:
        if not env_creds.valid:
            env_creds.refresh(Request())
        return env_creds

    creds: Credentials | None = None
    credentials_file = _credentials_path()

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if _is_hosted():
        raise FileNotFoundError(
            "Hosted auth requires GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, "
            "and GOOGLE_REFRESH_TOKEN (run python auth.py locally once, then "
            "copy values from token.json into Railway Variables)."
        )

    if not credentials_file.exists():
        raise FileNotFoundError(
            f"Missing credentials.json. Place it in {BASE_DIR} or "
            f"{BASE_DIR.parent} (downloaded from Google Cloud Console)."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
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
    # Help operators copy Railway variables without printing secrets in full.
    raw = json.loads(TOKEN_FILE.read_text(encoding="utf-8")) if TOKEN_FILE.exists() else {}
    print("Set these Railway variables from token.json / credentials.json:")
    print("  GOOGLE_CLIENT_ID")
    print("  GOOGLE_CLIENT_SECRET")
    print("  GOOGLE_REFRESH_TOKEN")
    print("  GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token")
    if raw.get("refresh_token"):
        print("(refresh_token is present in token.json)")
