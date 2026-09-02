# Railway Deployment Plan — Google MCP Server

Plan for deploying the FastAPI Google Docs + Gmail MCP-style server on [Railway](https://railway.app).

**Project:** `google-mcp-server`  
**Stack:** FastAPI + Uvicorn + Google OAuth (Docs + Gmail compose)  
**Target:** Public HTTPS API on Railway

---

## 1. Goal

Deploy `server.py` so these endpoints are reachable on a Railway public URL:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Health check |
| `POST` | `/append_to_doc` | Append text to a Google Doc |
| `POST` | `/create_email_draft` | Create a Gmail draft |
| `GET` | `/docs` | Swagger UI |

Example base URL after deploy: `https://<service>.up.railway.app`

---

## 2. Recommended architecture on Railway

```text
Client (curl / frontend / agent)
        │
        ▼
Railway Service (Uvicorn → FastAPI server.py)
        │
        ├── auth via env secrets (refresh token)
        ├── docs_tool → Google Docs API
        └── gmail_tool → Gmail API
```

**Do not** run Streamlit and FastAPI in the same Railway service unless you intentionally add a second service. For this plan, deploy **FastAPI only**.

---

## 3. Blockers in the current code (must fix before deploy)

| Issue | Why it breaks on Railway | Required change |
|-------|--------------------------|-----------------|
| `input("Approve? (y/n)")` in `server.py` | No interactive terminal on Railway | Replace with env flag, API key gate, or remove for production |
| Desktop OAuth (`run_local_server`) | No browser session on the server | Use pre-generated `refresh_token` from secrets |
| `credentials.json` / `token.json` on disk | Ephemeral filesystem; secrets in git are unsafe | Load from Railway Variables / Volume only if needed |
| `host="127.0.0.1"` | Not reachable externally | Bind `0.0.0.0` and use Railway `$PORT` |

Until approval and auth are cloud-safe, the app will hang, crash, or fail OAuth on every request.

---

## 4. Pre-deploy code checklist

### 4.1 Start command (bind all interfaces + Railway port)

Use one of these:

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

Or in `server.py`:

```python
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
```

### 4.2 Add Railway config files

**`Procfile`** (optional if using `railway.toml`):

```text
web: uvicorn server:app --host 0.0.0.0 --port $PORT
```

**`railway.toml`** (recommended):

```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn server:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 5
```

### 4.3 Make auth secrets-based

Update `auth.py` to build credentials from environment variables when present:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_CLIENT_ID` | OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Long-lived refresh token (from local `auth.py` run) |
| `GOOGLE_TOKEN_URI` | Default `https://oauth2.googleapis.com/token` |

Local `token.json` can remain for development; Railway should prefer env vars.

### 4.4 Replace terminal approval for production

Pick one approach:

1. **Env toggle (simplest)**  
   - `REQUIRE_APPROVAL=false` on Railway  
   - Keep terminal approval only for local runs  

2. **API key gate (recommended minimum)**  
   - Require header `X-API-Key: <secret>` on mutating endpoints  
   - Store `API_KEY` in Railway Variables  

3. **Async approval queue (advanced)**  
   - Store pending actions; approve via a separate admin UI — usually unnecessary for v1  

### 4.5 Dependencies

Keep current `requirements.txt`. No Redis/DB required for v1.

Ensure `.gitignore` includes:

```text
credentials.json
token.json
.venv/
__pycache__/
.env
```

---

## 5. Google Cloud setup (before Railway)

1. Enable **Google Docs API** and **Gmail API**.
2. OAuth consent screen: **Testing** + your account as a **test user** (unless verified).
3. OAuth client:
   - Local token generation: Desktop client (already used).
   - Keep the same client ID/secret values for refresh-token usage on Railway.
4. Run locally once:

   ```bash
   python auth.py
   ```

5. From `token.json`, copy:
   - `client_id` → `GOOGLE_CLIENT_ID`
   - `client_secret` → `GOOGLE_CLIENT_SECRET`
   - `refresh_token` → `GOOGLE_REFRESH_TOKEN`

Never commit `token.json` or `credentials.json`.

---

## 6. Railway setup steps

### Phase A — Create project

1. Sign in at [railway.app](https://railway.app).
2. **New Project** → **Deploy from GitHub repo** (recommended)  
   - Or **Empty Project** + Railway CLI upload.
3. Select the repo / folder that contains `google-mcp-server`  
   - If the repo root is the parent folder, set **Root Directory** to `google-mcp-server`.

### Phase B — Configure service

1. Set start command (if not using `railway.toml`):

   ```bash
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

2. Add Variables (Railway → Service → Variables):

   | Name | Example / notes |
   |------|-----------------|
   | `GOOGLE_CLIENT_ID` | from token/credentials |
   | `GOOGLE_CLIENT_SECRET` | from credentials |
   | `GOOGLE_REFRESH_TOKEN` | from token.json |
   | `GOOGLE_TOKEN_URI` | `https://oauth2.googleapis.com/token` |
   | `REQUIRE_APPROVAL` | `false` |
   | `API_KEY` | long random string (if using API key gate) |
   | `PORT` | usually injected by Railway automatically |

3. Generate a **public domain**: Settings → Networking → **Generate Domain**.

### Phase C — Deploy & verify

1. Trigger deploy; watch build logs for dependency install + start.
2. Health check:

   ```bash
   curl https://<your-app>.up.railway.app/
   ```

3. Smoke test (after approval/API-key changes are in place):

   ```bash
   curl -X POST https://<your-app>.up.railway.app/append_to_doc \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $API_KEY" \
     -d '{"doc_id":"YOUR_DOC_ID","content":"\nHello from Railway"}'
   ```

   ```bash
   curl -X POST https://<your-app>.up.railway.app/create_email_draft \
     -H "Content-Type: application/json" \
     -H "X-API-Key: $API_KEY" \
     -d '{"to":"you@example.com","subject":"Railway test","body":"Draft from Railway"}'
   ```

---

## 7. Deployment phases (timeline)

| Phase | Work | Est. time |
|-------|------|-----------|
| **1. Cloud-ready code** | `$PORT` / `0.0.0.0`, secrets-based auth, disable terminal approval, optional API key | 2–4 hrs |
| **2. Railway project** | Connect repo, root dir, variables, public domain | 30–60 min |
| **3. Smoke tests** | Health, Docs append, Gmail draft | 30 min |
| **4. Hardening** | API key rotation, rate limits, logging, private networking if needed | 1–2 hrs |

---

## 8. Security requirements

- Store all Google secrets and `API_KEY` only in Railway Variables.
- Do not expose the service publicly without at least an API key (or Railway private networking + trusted frontend).
- Remember: anyone who can call `/create_email_draft` or `/append_to_doc` acts as your Google account.
- Rotate `GOOGLE_REFRESH_TOKEN` / `API_KEY` if leaked.
- Keep OAuth app in **Testing** for personal use; verification is required only for broad public Google-user access.

---

## 9. Cost & runtime notes

- Railway bills for usage (hobby/pro plans). A single small FastAPI service is usually low cost at light traffic.
- Filesystem is ephemeral: do not rely on writing `token.json` long-term; refresh from env on each process start.
- Single replica is enough for v1; scale only if you have concurrent load (and then remove any process-local approval state).

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Deploy healthy but requests hang | Still calling `input()` | Set `REQUIRE_APPROVAL=false` or remove terminal gate |
| `Missing credentials.json` | Auth still file-based | Switch auth to env vars |
| `invalid_grant` / refresh errors | Bad or revoked refresh token | Re-run local `auth.py`, update `GOOGLE_REFRESH_TOKEN` |
| App not reachable | Bound to `127.0.0.1` or wrong port | Use `0.0.0.0` and `$PORT` |
| Build fails on import | Wrong root directory | Set Railway root to `google-mcp-server` |
| Google 403 on Doc | Account lacks edit access | Share Doc with the OAuth Google account |

---

## 11. Go-live checklist

- [ ] Terminal approval disabled or replaced for production
- [ ] Auth loads from Railway Variables (refresh token)
- [ ] Uvicorn listens on `0.0.0.0:$PORT`
- [ ] `credentials.json` / `token.json` not in git
- [ ] Railway Variables set (`GOOGLE_*`, optional `API_KEY`)
- [ ] Public domain generated
- [ ] `GET /` returns OK
- [ ] `POST /append_to_doc` works against a test Doc
- [ ] `POST /create_email_draft` creates a draft in Gmail
- [ ] API key (or equivalent) required on mutating routes

---

## 12. Out of scope for this plan

- Streamlit UI on Railway (separate service / separate plan)
- Full Google OAuth verification for production multi-user access
- Sending Gmail messages (drafts only, by design)
- Multi-region / autoscaling

---

## 13. Next implementation steps

1. Update `auth.py` to support env-based credentials.
2. Update `server.py` for `$PORT`, `0.0.0.0`, and non-interactive approval / API key.
3. Add `railway.toml` (and optional `Procfile`).
4. Push to GitHub and deploy on Railway with Variables from local `token.json`.
5. Run the smoke tests in §6 Phase C.
