"""Google Docs tool — append or replace document text."""

from __future__ import annotations

from googleapiclient.discovery import build

from auth import get_credentials


def _docs_service():
    creds = get_credentials()
    return build("docs", "v1", credentials=creds)


def _end_index(document: dict) -> int:
    return document.get("body", {}).get("content", [{}])[-1].get("endIndex", 1)


def append_to_doc(doc_id: str, content: str) -> dict:
    """
    Append `content` to the end of the Google Doc identified by `doc_id`.

    Returns a summary of the Docs API batchUpdate response.
    """
    service = _docs_service()
    document = service.documents().get(documentId=doc_id).execute()
    end_index = _end_index(document)
    # Insert before the final newline that Google Docs keeps at the end.
    insert_index = max(1, end_index - 1)
    text = content if content.startswith("\n") else f"\n{content}"

    result = (
        service.documents()
        .batchUpdate(
            documentId=doc_id,
            body={
                "requests": [
                    {
                        "insertText": {
                            "location": {"index": insert_index},
                            "text": text,
                        }
                    }
                ]
            },
        )
        .execute()
    )

    return {
        "doc_id": doc_id,
        "mode": "append",
        "appended": text,
        "insert_index": insert_index,
        "replies": result.get("replies", []),
    }


def replace_doc(doc_id: str, content: str) -> dict:
    """
    Replace the entire body of the Google Doc with `content`.

    Clears existing body text (keeps the trailing Docs newline), then inserts
    the new weekly pulse as the full document.
    """
    service = _docs_service()
    document = service.documents().get(documentId=doc_id).execute()
    end_index = _end_index(document)

    requests: list[dict] = []
    # Google Docs always keeps a final newline; deletable range is 1 .. endIndex-1.
    if end_index > 2:
        requests.append(
            {
                "deleteContentRange": {
                    "range": {"startIndex": 1, "endIndex": end_index - 1}
                }
            }
        )
    requests.append(
        {
            "insertText": {
                "location": {"index": 1},
                "text": content if content.endswith("\n") else f"{content}\n",
            }
        }
    )

    result = (
        service.documents()
        .batchUpdate(documentId=doc_id, body={"requests": requests})
        .execute()
    )

    return {
        "doc_id": doc_id,
        "mode": "replace",
        "written": content,
        "previous_end_index": end_index,
        "replies": result.get("replies", []),
    }
