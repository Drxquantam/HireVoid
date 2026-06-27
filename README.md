# HireVoid — Job Application Tracker

Automatically tracks job applications by reading your Gmail inbox. A kanban board shows every application by status: Applied → In Progress → Interview → Offer / Rejected.

**Stack:** FastAPI · SQLAlchemy · PostgreSQL · React · Tailwind CSS · Gmail API (read-only)

---

## 1. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **New Project**.
2. Enable **Gmail API** (APIs & Services → Library → search "Gmail API" → Enable).
3. Configure the OAuth Consent Screen:
   - User Type: **External**
   - Add your Gmail address as a **Test User** (required while app is in testing mode)
   - Scopes: add `https://www.googleapis.com/auth/gmail.readonly`
4. Create credentials: APIs & Services → Credentials → **Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8000/auth/callback`
5. Copy the **Client ID** and **Client Secret**.

---

## 2. Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in your values:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

DATABASE_URL=postgresql://postgres:password@localhost:5432/hirevoid

TOKEN_FILE=./token.json
APP_SECRET=change-me-to-a-long-random-secret
```

> **Never commit `.env` or `token.json`** — both are in `.gitignore`.

---

## 3. Database

Make sure PostgreSQL is running, then create the database:

```bash
psql -U postgres -c "CREATE DATABASE hirevoid;"
```

Tables are created automatically on first backend start.

---

## 4. Running the Backend

```bash
cd backend

# Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` to see the auto-generated API docs.

---

## 5. Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## 6. First-time Auth

1. Open `http://localhost:5173` — you'll see a "Connect Gmail" screen.
2. Click **Connect Gmail** → you'll be redirected to Google's consent page.
3. Sign in with the Google account you added as a Test User.
4. After approval, you're redirected back to the dashboard.
5. Click **Sync Gmail** to pull your 30 most recent emails.

---

## 7. How It Works

```
Gmail API (read-only)
       ↓
gmail_client.py   — fetch + parse 30 emails into structured dicts
       ↓
classifier.py     ← ★ YOU BUILD THIS (see below)
       ↓
pipeline.py       — upsert to DB, skip already-processed message IDs
       ↓
PostgreSQL        — applications + processed_messages tables
       ↓
FastAPI           — REST API served at :8000
       ↓
React + Tailwind  — kanban board at :5173
```

---

## 8. ★ Where to Build the Real Classifier

**File:** `backend/classifier.py`  
**Function:** `classify_email(email: dict) -> dict`

The current implementation is a naive stub that returns the sender domain as company and the subject as role. Everything around it — ingestion, dedup, database, API, UI — is fully working.

### Input

```python
{
    "message_id":    "...",
    "thread_id":     "...",
    "sender":        "Jane Recruiter <jane@acme.com>",
    "sender_domain": "acme.com",
    "subject":       "Your application to Software Engineer at Acme",
    "snippet":       "Hi ...",
    "body":          "Full email text (truncated to 4000 chars)...",
    "date":          datetime(2024, 6, 15, 10, 30),
}
```

### Expected Output

```python
{
    "company":  "Acme Corp",       # str
    "role":     "Software Engineer",  # str
    "status":   "applied",         # one of: applied | in_progress | interview | rejected | offer | unknown
    "deadline": None,              # ISO date string or None
}
```

### Status Values

| Value        | Meaning                                  |
|--------------|------------------------------------------|
| `applied`    | Confirmation of an application submitted |
| `in_progress`| Recruiter screen, take-home, etc.        |
| `interview`  | Interview scheduled                      |
| `offer`      | Offer letter received                    |
| `rejected`   | Rejection email                          |
| `unknown`    | Couldn't determine                       |

Replace the body of `classify_email()` with your logic (LLM call, regex rules, etc.). **No other file needs to change.**

---

## 9. API Reference

| Method | Path                   | Description                         |
|--------|------------------------|-------------------------------------|
| GET    | `/auth/login`          | Redirect to Google OAuth            |
| GET    | `/auth/callback`       | OAuth redirect handler              |
| GET    | `/auth/status`         | Check authentication status         |
| POST   | `/sync`                | Pull Gmail + classify + upsert      |
| GET    | `/applications`        | List applications grouped by status |
| GET    | `/applications/{id}`   | Single application                  |
| PATCH  | `/applications/{id}`   | Update status / deadline / role     |
| GET    | `/stats`               | Counts per status                   |

---

## 10. Project Structure

```
HireVoid/
├── backend/
│   ├── main.py          # FastAPI app + endpoints
│   ├── auth.py          # Google OAuth (token storage, refresh)
│   ├── gmail_client.py  # Gmail API fetch + parse
│   ├── classifier.py    # ★ STUB — replace this
│   ├── pipeline.py      # Orchestrates fetch → classify → upsert
│   ├── models.py        # SQLAlchemy ORM models
│   ├── database.py      # Engine + session factory
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── api.ts
    │   ├── types.ts
    │   └── components/
    │       ├── TopBar.tsx
    │       ├── KanbanBoard.tsx
    │       ├── StatusColumn.tsx
    │       └── ApplicationCard.tsx
    ├── package.json
    ├── vite.config.ts
    └── tailwind.config.js
```
