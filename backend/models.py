"""
models.py — SQLAlchemy ORM models.

Tables:
  applications       — one row per unique job application detected.
  processed_messages — tracks Gmail message IDs already ingested.
  oauth_token        — stores the Gmail OAuth token in DB (safe for cloud deployment).
"""
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Core application fields
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="applied")

    # Email source metadata
    source_message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    thread_id: Mapped[str] = mapped_column(String(255), nullable=True)
    sender: Mapped[str] = mapped_column(String(512), nullable=True)
    sender_domain: Mapped[str] = mapped_column(String(255), nullable=True)
    email_subject: Mapped[str] = mapped_column(String(512), nullable=True)
    email_snippet: Mapped[str] = mapped_column(Text, nullable=True)

    # Dates
    applied_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    deadline: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "status": self.status,
            "source_message_id": self.source_message_id,
            "thread_id": self.thread_id,
            "sender": self.sender,
            "sender_domain": self.sender_domain,
            "email_subject": self.email_subject,
            "email_snippet": self.email_snippet,
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OAuthToken(Base):
    """Stores the Gmail OAuth token in the database instead of a local file.
    Single-row table — we always upsert with id=1."""
    __tablename__ = "oauth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    token_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProcessedMessage(Base):
    """
    Tracks Gmail message IDs we have already ingested.
    Before processing any email we check this table — if the ID exists, skip it.
    """
    __tablename__ = "processed_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Whether the classifier found this relevant (False = skipped/irrelevant)
    was_relevant: Mapped[bool] = mapped_column(Boolean, default=True)
