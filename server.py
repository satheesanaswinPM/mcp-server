"""FastAPI MCP-style server for Google Docs and Gmail tools."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from docs_tool import append_to_doc
from gmail_tool import create_email_draft

app = FastAPI(
    title="Google MCP Server",
    description="MCP-style FastAPI server for Google Docs and Gmail.",
    version="1.0.0",
)


class AppendToDocRequest(BaseModel):
    doc_id: str = Field(..., description="Google Docs document ID")
    content: str = Field(..., description="Text to append to the document")


class CreateEmailDraftRequest(BaseModel):
    to: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")


def require_approval(action: str, payload: dict[str, Any]) -> None:
    """Print the action and ask for terminal approval before continuing."""
    print("\n" + "=" * 60)
    print(f"ACTION: {action}")
    print("PAYLOAD:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("=" * 60)
    answer = input("Approve? (y/n): ").strip().lower()
    if answer != "y":
        raise HTTPException(status_code=403, detail="Action denied by user")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Google MCP Server is running",
        "endpoints": "/append_to_doc, /create_email_draft, /docs",
    }


@app.post("/append_to_doc")
def append_to_doc_endpoint(request: AppendToDocRequest) -> dict[str, Any]:
    payload = request.model_dump()
    require_approval("append_to_doc", payload)
    try:
        result = append_to_doc(doc_id=request.doc_id, content=request.content)
        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — surface API errors to the client
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/create_email_draft")
def create_email_draft_endpoint(request: CreateEmailDraftRequest) -> dict[str, Any]:
    payload = request.model_dump()
    require_approval("create_email_draft", payload)
    try:
        result = create_email_draft(
            to=request.to, subject=request.subject, body=request.body
        )
        return {"status": "success", "result": result}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — surface API errors to the client
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    # workers=1 and no reload so input() approval works in this terminal
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
