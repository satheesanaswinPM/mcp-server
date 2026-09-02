"""Write Railway Google Variables from a local token.json (never prints secrets).

Usage:
  python scripts/export_railway_google_env.py [path/to/token.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "railway-google.env"


def main() -> int:
    token_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "token.json"
    if not token_path.exists():
        print(f"Missing {token_path}")
        print("Run: python auth.py  (once, locally), then re-run this script.")
        return 1

    raw = json.loads(token_path.read_text(encoding="utf-8"))
    client_id = (raw.get("client_id") or "").strip()
    client_secret = (raw.get("client_secret") or "").strip()
    refresh_token = (raw.get("refresh_token") or "").strip()
    token_uri = (raw.get("token_uri") or "https://oauth2.googleapis.com/token").strip()

    missing = [
        name
        for name, value in [
            ("client_id", client_id),
            ("client_secret", client_secret),
            ("refresh_token", refresh_token),
        ]
        if not value
    ]
    if missing:
        print(f"token.json missing fields: {', '.join(missing)}")
        return 1

    OUT.write_text(
        "\n".join(
            [
                f"GOOGLE_CLIENT_ID={client_id}",
                f"GOOGLE_CLIENT_SECRET={client_secret}",
                f"GOOGLE_REFRESH_TOKEN={refresh_token}",
                f"GOOGLE_TOKEN_URI={token_uri}",
                "REQUIRE_APPROVAL=false",
                "AUTO_APPROVE=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUT} (gitignored).")
    print("Paste these into Railway → Service → Variables, then redeploy.")
    print("Do not commit or paste this file into chat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
