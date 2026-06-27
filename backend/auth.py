"""
auth.py — Google OAuth 2.0 flow (single-user, read-only Gmail scope).

Token storage: in production the token is stored in the `oauth_tokens` DB table
so it survives redeploys. Locally it falls back to TOKEN_FILE if set.
"""
import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")
# Legacy local file — used only when DATABASE_URL points to SQLite (local dev without DB)
TOKEN_FILE = Path(os.getenv("TOKEN_FILE", "./token.json"))


def _client_config() -> dict:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set.")
    return {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


# ---------------------------------------------------------------------------
# DB-backed token storage (used in production)
# ---------------------------------------------------------------------------

def _get_db_session():
    """Open a raw DB session without going through FastAPI's dependency injection."""
    from database import SessionLocal
    return SessionLocal()


def _load_token_from_db() -> dict | None:
    try:
        from models import OAuthToken
        db = _get_db_session()
        row = db.query(OAuthToken).filter_by(id=1).first()
        db.close()
        return json.loads(row.token_json) if row else None
    except Exception:
        return None


def _save_token_to_db(data: dict) -> None:
    try:
        from models import OAuthToken
        from datetime import datetime
        db = _get_db_session()
        row = db.query(OAuthToken).filter_by(id=1).first()
        if row:
            row.token_json = json.dumps(data)
            row.updated_at = datetime.utcnow()
        else:
            db.add(OAuthToken(id=1, token_json=json.dumps(data)))
        db.commit()
        db.close()
    except Exception as e:
        print(f"[auth] Warning: could not save token to DB: {e}")


def _delete_token_from_db() -> None:
    try:
        from models import OAuthToken
        db = _get_db_session()
        db.query(OAuthToken).filter_by(id=1).delete()
        db.commit()
        db.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_auth_url() -> str:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code(code: str) -> Credentials:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_credentials(creds)
    return creds


def get_credentials() -> Credentials | None:
    # Try DB first, fall back to local file
    data = _load_token_from_db()
    if data is None and TOKEN_FILE.exists():
        data = json.loads(TOKEN_FILE.read_text())

    if not data:
        return None

    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds)

    return creds


def _save_credentials(creds: Credentials) -> None:
    data = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes) if creds.scopes else SCOPES,
    }
    _save_token_to_db(data)
    # Also write local file for dev convenience
    try:
        TOKEN_FILE.write_text(json.dumps(data))
    except Exception:
        pass


def is_authenticated() -> bool:
    creds = get_credentials()
    return creds is not None and (creds.valid or bool(creds.refresh_token))


def get_connected_email() -> str | None:
    creds = get_credentials()
    if not creds:
        return None
    try:
        import httpx
        resp = httpx.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {creds.token}"},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("emailAddress")
    except Exception:
        pass
    return None


def logout() -> None:
    _delete_token_from_db()
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
