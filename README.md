# Google MCP Server

A FastAPI MCP-style server that exposes Google Docs and Gmail tools with **human-in-the-loop approval** in the terminal before any action runs.

## Features

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/append_to_doc` | `POST` | Append text to a Google Doc |
| `/create_email_draft` | `POST` | Create a Gmail draft |
| `/` | `GET` | Health check |
| `/docs` | `GET` | Interactive Swagger UI |

Before every tool call, the server prints the action name and payload.

**Local terminal (interactive):** asks `Approve? (y/n):` — only `y` proceeds; anything else returns HTTP `403`.

**Hosted / non-interactive (e.g. Railway):** automatically approves when:

- `AUTO_APPROVE=1`, or
- `RAILWAY_ENVIRONMENT` / `RAILWAY_PROJECT_ID` is present (Railway deploy), or
- stdin is not a TTY

Set `REQUIRE_INTERACTIVE_APPROVAL=1` to force the local `y/n` prompt even in those environments.

## Project layout

```text
google-mcp-server/
├── server.py          # FastAPI app + approval gate
├── auth.py            # Google OAuth 2.0
├── docs_tool.py       # append_to_doc()
├── gmail_tool.py      # create_email_draft()
├── requirements.txt
├── README.md
├── credentials.json   # from Google Cloud (not committed)
└── token.json         # created after first login (not committed)
```

## 1. Google Cloud setup

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Enable APIs:
   - [Google Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com)
   - [Gmail API](https://console.cloud.google.com/apis/library/gmail.googleapis.com)
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
5. Application type: **Desktop app**.
6. Download the JSON and save it as `credentials.json` in this folder.
7. Configure the OAuth consent screen (External or Internal). Add your Google account as a test user if the app is in Testing mode.
8. Scopes used by this project:
   - `https://www.googleapis.com/auth/documents`
   - `https://www.googleapis.com/auth/gmail.compose`

## 2. Install

```bash
cd google-mcp-server
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Run the server

```bash
python server.py
```

Or:

```bash
uvicorn server:app --host 127.0.0.1 --port 8000
```

On first authenticated tool call, a browser window opens for Google login. After success, `token.json` is written and reused on later runs.

> **Important:** Run with a single worker and **without** `--reload` so the terminal `Approve? (y/n)` prompt works.

## 4. Example requests

### Append to a Google Doc

The `doc_id` is the ID in the Doc URL:

`https://docs.google.com/document/d/<DOC_ID>/edit`

```bash
curl -X POST http://127.0.0.1:8000/append_to_doc ^
  -H "Content-Type: application/json" ^
  -d "{\"doc_id\": \"YOUR_DOC_ID\", \"content\": \"\\nHello from MCP server!\"}"
```

macOS / Linux:

```bash
curl -X POST http://127.0.0.1:8000/append_to_doc \
  -H "Content-Type: application/json" \
  -d '{"doc_id": "YOUR_DOC_ID", "content": "\nHello from MCP server!"}'
```

In the server terminal, type `y` to approve.

### Create a Gmail draft

```bash
curl -X POST http://127.0.0.1:8000/create_email_draft ^
  -H "Content-Type: application/json" ^
  -d "{\"to\": \"someone@example.com\", \"subject\": \"Hello\", \"body\": \"Draft from MCP server.\"}"
```

macOS / Linux:

```bash
curl -X POST http://127.0.0.1:8000/create_email_draft \
  -H "Content-Type: application/json" \
  -d '{"to": "someone@example.com", "subject": "Hello", "body": "Draft from MCP server."}'
```

You can also try the interactive UI at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## 5. Auth behavior

`auth.get_credentials()`:

1. Loads `token.json` if it exists and is valid.
2. Refreshes the token when expired (using the refresh token).
3. Otherwise starts the desktop OAuth flow with `credentials.json` and saves a new `token.json`.

## Security notes

- Never commit `credentials.json` or `token.json` (both are in `.gitignore`).
- Local runs still use terminal approval by default.
- On Railway/containers, non-interactive auto-approve is required for the API to work; protect the public URL (do not leave write endpoints open without auth if the service is exposed).
- Gmail drafts are created only — nothing is sent until you send them in Gmail.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Missing credentials.json` | Download Desktop OAuth client JSON into this folder |
| `Access blocked` / consent errors | Add yourself as a test user; ensure Docs + Gmail APIs are enabled |
| Approval prompt never appears | Avoid `--reload` and multiple uvicorn workers |
| `403` from API | Confirm the Google account has edit access to the Doc |
