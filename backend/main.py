"""
main.py — FastAPI application.

Endpoints:
  GET  /auth/login           → redirect to Google OAuth consent
  GET  /auth/callback        → handle OAuth redirect, store tokens
  GET  /auth/status          → check if authenticated
  POST /sync                 → pull Gmail, classify, upsert to DB
  GET  /applications         → list all applications grouped by status
  GET  /applications/{id}    → single application detail
  PATCH /applications/{id}   → update status or deadline manually
  GET  /stats                → summary counts per status
"""
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import auth
import pipeline
from database import get_db, engine, Base
from models import Application

# Create tables on startup if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="HireVoid API", version="1.0.0")

# Allow the React dev server on port 5173 to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.get("/auth/login")
def login():
    """Redirect the browser to Google's OAuth consent page."""
    url = auth.get_auth_url()
    return RedirectResponse(url=url)


@app.get("/auth/callback")
def oauth_callback(code: str, state: Optional[str] = None, error: Optional[str] = None):
    """Google redirects here with ?code=... after the user grants access."""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    auth.exchange_code(code)
    # Redirect to the frontend after successful auth
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(url=f"{frontend_url}?auth=success")


@app.get("/auth/status")
def auth_status():
    """Returns whether the app is authenticated with Gmail, plus the connected email."""
    authenticated = auth.is_authenticated()
    email = auth.get_connected_email() if authenticated else None
    return {"authenticated": authenticated, "email": email}


@app.post("/auth/logout")
def logout():
    """Clear stored credentials so the user can connect a different Gmail account."""
    auth.logout()
    return {"success": True}


# ---------------------------------------------------------------------------
# Sync endpoint
# ---------------------------------------------------------------------------

@app.post("/sync")
def trigger_sync(db: Session = Depends(get_db)):
    """
    Pull the latest emails from Gmail, run them through the classifier,
    and upsert results into the database.
    """
    if not auth.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Visit /auth/login first."
        )
    try:
        summary = pipeline.run_sync(db)
        return {"success": True, **summary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Applications endpoints
# ---------------------------------------------------------------------------

STATUS_ORDER = ["applied", "in_progress", "interview", "offer", "rejected", "unknown"]


@app.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    """Return all applications grouped by status."""
    apps = db.query(Application).order_by(Application.applied_date.desc()).all()
    grouped: dict[str, list] = {s: [] for s in STATUS_ORDER}
    for a in apps:
        bucket = a.status if a.status in grouped else "unknown"
        grouped[bucket].append(a.to_dict())
    return grouped


@app.get("/applications/{app_id}")
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    return app.to_dict()


class ApplicationCreate(BaseModel):
    company: str
    role: str
    status: Optional[str] = "applied"
    applied_date: Optional[str] = None   # ISO date string
    deadline: Optional[str] = None


@app.post("/applications", status_code=201)
def create_application(body: ApplicationCreate, db: Session = Depends(get_db)):
    """Manually create a job application (not sourced from Gmail)."""
    import uuid
    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status.")

    applied_date = None
    if body.applied_date:
        try:
            applied_date = datetime.fromisoformat(body.applied_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="applied_date must be ISO format.")

    deadline = None
    if body.deadline:
        try:
            deadline = datetime.fromisoformat(body.deadline)
        except ValueError:
            raise HTTPException(status_code=400, detail="deadline must be ISO format.")

    app = Application(
        company=body.company.strip(),
        role=body.role.strip(),
        status=body.status or "applied",
        source_message_id=f"manual-{uuid.uuid4()}",
        applied_date=applied_date or datetime.utcnow(),
        deadline=deadline,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app.to_dict()


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    deadline: Optional[str] = None   # ISO date string
    role: Optional[str] = None
    company: Optional[str] = None


VALID_STATUSES = {"applied", "in_progress", "interview", "rejected", "offer", "unknown"}


@app.patch("/applications/{app_id}")
def update_application(app_id: int, body: ApplicationUpdate, db: Session = Depends(get_db)):
    """Manually update status, deadline, role, or company."""
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    if body.status:
        if body.status not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Choose from {VALID_STATUSES}")
        app.status = body.status

    if body.deadline:
        try:
            app.deadline = datetime.fromisoformat(body.deadline)
        except ValueError:
            raise HTTPException(status_code=400, detail="deadline must be an ISO date string.")

    if body.role:
        app.role = body.role

    if body.company:
        app.company = body.company

    app.updated_at = datetime.utcnow()
    db.commit()
    return app.to_dict()


# ---------------------------------------------------------------------------
# Delete endpoints
# ---------------------------------------------------------------------------

@app.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    """Permanently delete a single application."""
    app = db.query(Application).filter_by(id=app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")
    db.delete(app)
    db.commit()
    return {"deleted": app_id}


@app.delete("/applications")
def delete_applications_by_status(status: str, db: Session = Depends(get_db)):
    """Delete all applications with a given status."""
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status.")
    deleted = db.query(Application).filter_by(status=status).delete()
    db.commit()
    return {"deleted": deleted, "status": status}


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Return counts per status plus total."""
    apps = db.query(Application).all()
    counts: dict[str, int] = {s: 0 for s in STATUS_ORDER}
    for a in apps:
        bucket = a.status if a.status in counts else "unknown"
        counts[bucket] += 1
    return {"total": len(apps), "by_status": counts}
