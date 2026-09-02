"""Google Docs tool — append text to a document."""

from __future__ import annotations

from googleapiclient.discovery import build

from auth import get_credentials


def append_to_doc(doc_id: str, content: str) -> dict:
    """
    Append `content` to the end of the Google Doc identified by `doc_id`.

    Returns a summary of the Docs API batchUpdate response.
    """
    creds = get_credentials()
    service = build("docs", "v1", credentials=creds)

    document = service.documents().get(documentId=doc_id).execute()
    end_index = document.get("body", {}).get("content", [{}])[-1].get(
        "endIndex", 1
    )
    # Insert before the final newline that Google Docs keeps at the end.
    insert_index = max(1, end_index - 1)

    requests = [
        {
            "insertText": {
                "location": {"index": insert_index},
                "text": content,
            }
        }
    ]

    result = (
        service.documents()
        .batchUpdate(documentId=doc_id, body={"requests": requests})
        .execute()
    )

    return {
        "doc_id": doc_id,
        "appended": content,
        "insert_index": insert_index,
        "replies": result.get("replies", []),
    }
