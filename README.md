# HireVoid: Gmail Job Application Tracker

**HireVoid reads your Gmail and builds a kanban board of every job application, sorted by status:** Applied → In Progress → Interview → Offer / Rejected. I built it during placement season because I was applying to a lot of companies and losing track of which ones had replied.

**Stack:** FastAPI · SQLAlchemy · PostgreSQL · React + TypeScript · Tailwind CSS · Gmail API (read-only) · Groq (Llama 3.3 70B)
**Deployed:** backend on Railway, frontend on Vercel

---

## The interesting part: a layered email classifier

Most of a student's inbox during placements is *noise* that looks like job email: Naukri/LinkedIn job alerts, contest reminders, newsletters, "jobs recommended for you" digests. Sending every email to an LLM would be slow and expensive. It would also be unreliable on emails that are clearly not applications.

So `backend/classifier.py` runs every email through a pipeline that goes from cheap checks to expensive ones. Each layer is a standalone, unit-testable function:

```
Gmail message
   │
   ▼
Layer 1  passes_sender_filter()   O(1) set lookups on the sender domain
         • known ATS domain (Greenhouse, Lever, Workday…) → always keep
         • denylisted domain / "alerts@", "digest@" patterns → drop
   │
   ▼
Layer 2  is_application_email()   string heuristics, broadcast vs. personal
         • digest language ("jobs recommended for you") → drop
         • 3+ distinct job-listing links → it's a digest → drop
         • unsolicited phrasing ("your profile matches") → drop
   │
   ▼
Layer 3  detect_status()          keyword scoring on subject + body
         • counts hits per status; ties go to the higher-stakes status
           (offer > interview > rejected > applied)
   │
   ▼
Layer 4  classify_with_llm()      Groq, strict-JSON prompt, body capped at 1200 chars
         • extracts company + role
         • decides the status ONLY when Layer 3 had no confident match
         • any API/parse error returns None, so it never crashes the sync
   │
   ▼
Layer 5  resolve_entity()         dedup against tracked applications
         • same Gmail thread_id → same application
         • same normalised company ("Inc", "LLC", ".com" stripped)
           + ≥ 40% role-word overlap → same application
```

**Why this order:** Layers 1–2 throw out non-application mail before any network call happens, so the LLM only sees emails that look like real application responses. Layer 3 settles the status for clear-cut cases ("thank you for applying", "pleased to offer"). That way the model's judgment is only trusted for genuinely ambiguous emails. All the tunable lists (`DENYLIST_DOMAINS`, `ATS_DOMAINS`, `STATUS_KEYWORDS`, thresholds) sit at the top of the file, so you can tune against a real inbox without touching the logic.

**Tests:** `python backend/classifier.py` runs the smoke tests for layers 1–3 and 5. They make no LLM calls, so they're free and fast. They cover job-alert digests, contest emails, rejections, interview invites through Greenhouse, application confirmations, offers, and the dedup cases.

### Sync pipeline

```
Gmail API (read-only) → gmail_client.py → classifier.py → pipeline.py → PostgreSQL → FastAPI → React kanban
```

`pipeline.py` keeps a `processed_messages` table, so every Gmail message is classified **once**. Re-syncing skips anything already seen, including emails that were rejected as irrelevant. This keeps syncs fast and avoids paying for repeat LLM calls.

---

## Run it locally

### 1. Google OAuth setup

1. [Google Cloud Console](https://console.cloud.google.com/) → **New Project**.
2. Enable the **Gmail API** (APIs & Services → Library).
3. OAuth consent screen: User Type **External**, add your Gmail as a **Test User**, and add the scope `https://www.googleapis.com/auth/gmail.readonly`.
4. Credentials → **Create Credentials → OAuth 2.0 Client ID** → *Web application*, with the redirect URI `http://localhost:8000/auth/callback`.
5. Copy the Client ID and Client Secret.

### 2. Environment variables

Copy `backend/.env.example` to `backend/.env`:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
DATABASE_URL=postgresql://postgres:password@localhost:5432/hirevoid
TOKEN_FILE=./token.json
APP_SECRET=change-me-to-a-long-random-secret
GROQ_API_KEY=your-groq-api-key
```

> Never commit `.env` or `token.json`. Both are in `.gitignore`.

### 3. Database

```bash
psql -U postgres -c "CREATE DATABASE hirevoid;"
```

Tables are created automatically on the first backend start.

### 4. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 5. Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

### 6. First sync

Open the app → **Connect Gmail** → approve on Google's consent page → **Sync Gmail** pulls your 30 most recent emails. You can also add an application by hand with the **+** button in the top bar.

---

## API

| Method | Path | Description |
|---|---|---|
| GET | `/auth/login` | Redirect to Google OAuth |
| GET | `/auth/callback` | OAuth redirect handler |
| GET | `/auth/status` | Check authentication status |
| POST | `/sync` | Pull Gmail → classify → upsert |
| GET | `/applications` | List applications grouped by status |
| GET | `/applications/{id}` | Single application |
| PATCH | `/applications/{id}` | Update status / deadline / role |
| GET | `/stats` | Counts per status |

## Project structure

```
HireVoid/
├── backend/
│   ├── main.py          FastAPI app + endpoints
│   ├── auth.py          Google OAuth (token storage, refresh)
│   ├── gmail_client.py  Gmail API fetch + parse
│   ├── classifier.py    5-layer classifier + smoke tests
│   ├── pipeline.py      fetch → classify → upsert, incremental by message ID
│   ├── models.py        SQLAlchemy models
│   ├── database.py      engine + session factory
│   └── Procfile         Railway start command
└── frontend/
    └── src/components/  TopBar, KanbanBoard, StatusColumn, ApplicationCard, AddJobModal
```

## What I'd do next

- Wire Layer 5 (`resolve_entity`) into `pipeline.py`. Right now the pipeline upserts by message ID, so a later email in the same thread (say, an interview invite after the confirmation) doesn't yet update the original card.
- Skip the LLM call in Layer 3 when the company can be read from a known ATS template.
- Measure precision/recall of the classifier on a labelled sample of my own inbox.

---

Built by **Dhruv Rai** · [GitHub](https://github.com/Drxquantam)
