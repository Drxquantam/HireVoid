"""
gmail_client.py — Fetch emails from Gmail API and parse them into structured dicts.

Uses the read-only scope only. Never modifies labels, messages, or threads.

Each returned email dict has:
  message_id, thread_id, sender, sender_domain, subject, snippet, body, date
"""
import base64
import email as email_lib
import re
from datetime import datetime
from typing import Generator

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import auth


MAX_RESULTS = 30   # pull at most this many emails per sync


def _get_service():
    """Build the Gmail API service object from stored credentials."""
    creds = auth.get_credentials()
    if not creds:
        raise RuntimeError("Not authenticated. Visit /auth/login first.")
    return build("gmail", "v1", credentials=creds)


def _extract_sender_domain(sender: str) -> str:
    """Extract domain from 'Name <user@domain.com>' or 'user@domain.com'."""
    match = re.search(r"@([\w.-]+)", sender)
    return match.group(1).lower() if match else ""


def _decode_body(payload: dict) -> str:
    """Recursively decode the email body, preferring plain text over HTML."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    if mime_type == "text/html" and body_data:
        html = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        # Strip HTML tags for a rough plain-text version
        return re.sub(r"<[^>]+>", " ", html)

    # Multipart — recurse into parts
    parts = payload.get("parts", [])
    # Prefer text/plain part
    for part in parts:
        if part.get("mimeType") == "text/plain":
            result = _decode_body(part)
            if result:
                return result
    # Fall back to any part
    for part in parts:
        result = _decode_body(part)
        if result:
            return result

    return ""


def _parse_message(raw: dict) -> dict:
    """Convert a raw Gmail API message object into a clean structured dict."""
    headers = {h["name"].lower(): h["value"] for h in raw.get("payload", {}).get("headers", [])}

    sender = headers.get("from", "")
    subject = headers.get("subject", "")
    date_str = headers.get("date", "")

    # Parse the date header; fall back to internalDate (epoch ms)
    parsed_date: datetime | None = None
    try:
        parsed_date = email_lib.utils.parsedate_to_datetime(date_str) if date_str else None
    except Exception:
        pass
    if parsed_date is None:
        try:
            parsed_date = datetime.utcfromtimestamp(int(raw.get("internalDate", 0)) / 1000)
        except Exception:
            parsed_date = datetime.utcnow()

    body = _decode_body(raw.get("payload", {}))

    return {
        "message_id": raw["id"],
        "thread_id": raw.get("threadId", ""),
        "sender": sender,
        "sender_domain": _extract_sender_domain(sender),
        "subject": subject,
        "snippet": raw.get("snippet", ""),
        "body": body[:4000],   # truncate for storage; classifier can use snippet for now
        "date": parsed_date,
    }


def fetch_recent_emails(max_results: int = MAX_RESULTS) -> list[dict]:
    """
    Fetch the most recent `max_results` emails from the user's Gmail inbox.
    Returns a list of structured email dicts.
    """
    service = _get_service()

    try:
        response = service.users().messages().list(
            userId="me",
            maxResults=max_results,
            labelIds=["INBOX"],
        ).execute()
    except HttpError as e:
        raise RuntimeError(f"Gmail API error listing messages: {e}") from e

    messages = response.get("messages", [])
    results = []

    for msg_stub in messages:
        try:
            raw = service.users().messages().get(
                userId="me",
                id=msg_stub["id"],
                format="full",
            ).execute()
            results.append(_parse_message(raw))
        except HttpError as e:
            # Log and skip individual failures rather than aborting the whole sync
            print(f"[gmail_client] Skipping message {msg_stub['id']}: {e}")
            continue

    return results
