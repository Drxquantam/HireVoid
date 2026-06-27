"""
pipeline.py — Orchestrates: fetch emails → classify → upsert to DB.

Key guarantees:
  - Incremental: we skip any message_id already in processed_messages.
  - Idempotent: running sync twice produces the same DB state (upsert by source_message_id).
  - Classifier isolation: only classify_email() is called here; swapping classifier.py
    requires no changes to this file.
"""
from datetime import datetime
from sqlalchemy.orm import Session

import gmail_client
from classifier import classify_email
from models import Application, ProcessedMessage


VALID_STATUSES = {"applied", "in_progress", "interview", "rejected", "offer", "unknown"}


def _normalize_status(status: str) -> str:
    """Ensure status is one of our known values; default to 'applied'."""
    s = (status or "").lower().strip().replace(" ", "_")
    return s if s in VALID_STATUSES else "applied"


def run_sync(db: Session) -> dict:
    """
    Full sync pipeline.

    Returns a summary dict: { fetched, skipped, new, updated }
    """
    emails = gmail_client.fetch_recent_emails()

    fetched = len(emails)
    skipped = 0
    new_count = 0
    updated = 0

    for email in emails:
        msg_id = email["message_id"]

        # --- Incremental check ---
        already_done = db.query(ProcessedMessage).filter_by(message_id=msg_id).first()
        if already_done:
            skipped += 1
            continue

        # --- Classify ---
        try:
            result = classify_email(email)
        except Exception as exc:
            print(f"[pipeline] classifier error on {msg_id}: {exc}")
            result = None

        # classify_email returns None for non-application emails — skip them
        if result is None:
            db.add(ProcessedMessage(message_id=msg_id, was_relevant=False))
            skipped += 1
            continue

        # --- Parse deadline if classifier returned one ---
        deadline: datetime | None = None
        if result.get("deadline"):
            try:
                deadline = datetime.fromisoformat(str(result["deadline"]))
            except Exception:
                pass

        # --- Upsert Application (keyed on source_message_id) ---
        existing = db.query(Application).filter_by(source_message_id=msg_id).first()
        if existing:
            # Update status/deadline if classifier produced new info
            existing.status = _normalize_status(result.get("status", existing.status))
            existing.deadline = deadline or existing.deadline
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            app = Application(
                company=result.get("company") or email.get("sender_domain") or "Unknown",
                role=result.get("role") or email.get("subject") or "Unknown",
                status=_normalize_status(result.get("status", "applied")),
                source_message_id=msg_id,
                thread_id=email.get("thread_id"),
                sender=email.get("sender"),
                sender_domain=email.get("sender_domain"),
                email_subject=email.get("subject"),
                email_snippet=email.get("snippet"),
                applied_date=email.get("date"),
                deadline=deadline,
            )
            db.add(app)
            new_count += 1

        # --- Mark as processed regardless of relevance ---
        db.add(ProcessedMessage(message_id=msg_id, was_relevant=True))

    db.commit()

    return {
        "fetched": fetched,
        "skipped": skipped,
        "new": new_count,
        "updated": updated,
    }
