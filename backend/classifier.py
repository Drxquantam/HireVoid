"""
classifier.py — Job Application Email Classifier
=================================================
Pipeline design (cheapest → most expensive):

  Layer 1  passes_sender_filter()   — denylist/allowlist on sender domain
  Layer 2  is_application_email()   — heuristics: broadcast vs. personal
  Layer 3  detect_status()          — keyword matching on subject + body
  Layer 4  classify_with_llm()      — Groq LLM for ambiguous residuals only
  Layer 5  resolve_entity()         — dedup against existing applications

Each layer is a standalone function so it can be unit-tested independently.
Constants (DENYLIST, ATS_DOMAINS, STATUS_KEYWORDS) are at the top so you can
tune them against your real inbox without touching any logic.
"""

import json
import os
import re
import unicodedata
from typing import Any

from groq import Groq  # pip install groq

# ---------------------------------------------------------------------------
# GROQ CLIENT
# Read the key from the environment so it's never hard-coded.
# ---------------------------------------------------------------------------
_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.3-70b-versatile"  # fast, cheap, accurate enough for this task

# ---------------------------------------------------------------------------
# LAYER 1 CONSTANTS
# ---------------------------------------------------------------------------

# Domains / sender strings that are definitively NOT individual application
# acknowledgements. Any email whose sender_domain is in this set (or whose
# sender address contains a DENYLIST_SENDER string) is discarded immediately.
# Add to this freely — it's the single highest-leverage tuning knob.
DENYLIST_DOMAINS: set[str] = {
    # Job-alert / aggregator platforms
    "naukri.com",
    "naukrimailer.com",
    "linkedin.com",          # LinkedIn job-alert digests; individual recruiter
    "notifications.linkedin.com",  # mail also comes from here — keep both
    "internshala.com",
    "indeed.com",
    "glassdoor.com",
    "shine.com",
    "monster.com",
    "foundit.in",            # formerly Monster India
    "timesjobs.com",
    "hirist.com",
    "cutshort.io",
    "instahyre.com",
    "wellfound.com",         # AngelList Talent alerts
    "angellist.com",
    # Coding-platform / contest mail (not job applications)
    "leetcode.com",
    "hackerrank.com",
    "hackerearth.com",
    "geeksforgeeks.org",
    "codechef.com",
    "codeforces.com",
    "topcoder.com",
    "kaggle.com",
    # Scholarship / educational newsletters
    "scholarshipowl.com",
    "opportunitydesk.org",
    "youthop.com",
    "aicte-india.org",
    # Generic newsletter / marketing platforms (often spoofed by job boards too)
    "mailchimp.com",
    "sendgrid.net",          # only block when combined with job-alert subjects
    "marketing.greenhouse.io",  # Greenhouse *marketing* vs application mail
    # AI/tech product newsletters — model updates, not job mail
    "groq.com",
    "groq.co",
    "openai.com",
    "anthropic.com",
    "mistral.ai",
    "huggingface.co",
    # Job-discovery / company-review platforms (alerts, not ATS confirmations)
    "ambitionbox.com",
    "iimjobs.com",
    "apna.co",
    "freshersworld.com",
    "placementindia.com",
    # Other noisy senders seen in typical Indian job-seeker inboxes
    "unstop.com",            # formerly D2C / competitions
    "interviewbit.com",
    "scaler.com",
    "simplilearn.com",
    "upgrad.com",
    "coursera.org",
    "edx.org",
    "udemy.com",
}

# Substrings checked against the full sender address (not just domain).
# Useful for catching "alerts@", "noreply@jobs.", "no-reply@notifications." etc.
DENYLIST_SENDER_PATTERNS: list[str] = [
    "job-alert",
    "jobalert",
    "jobs-noreply",
    "noreply@jobs",
    "alerts@",
    "digest@",
    "newsletter@",
    "no-reply@notifications",
    "weekly@",
    "dailydigest",
    "jobsearch",
    "recommended@",
]

# ATS / recruiting-software domains whose mail is almost certainly a real
# application acknowledgement or status update. Emails from these domains
# skip the denylist check and are treated as confirmed application mail.
ATS_DOMAINS: set[str] = {
    "greenhouse.io",
    "greenhouse-mail.io",
    "lever.co",
    "myworkday.com",
    "wd1.myworkdayjobs.com",
    "ashbyhq.com",
    "smartrecruiters.com",
    "icims.com",
    "workable.com",
    "jobvite.com",
    "taleo.net",
    "successfactors.com",
    "brassring.com",
    "bamboohr.com",
    "recruitee.com",
    "dover.com",
    "rippling.com",
    "oracle.com",          # Oracle HCM / Taleo
    "sap.com",             # SAP SuccessFactors
    "hire.withgoogle.com",
}

# ---------------------------------------------------------------------------
# LAYER 3 CONSTANTS
# ---------------------------------------------------------------------------

# Each status maps to phrases that strongly indicate it.
# Phrases are matched case-insensitively against (subject + " " + body).
# Longer / more specific phrases are better — they reduce false positives.
STATUS_KEYWORDS: dict[str, list[str]] = {
    "applied": [
        "we received your application",
        "thank you for applying",
        "application submitted",
        "application has been received",
        "your application is under review",
        "we have received your application",
        "thanks for applying",
        "successfully applied",
        "application confirmation",
        "you have applied",
        "we'll review your application",
        "we will review your application",
        "application is being reviewed",
        "your resume has been received",
    ],
    "rejected": [
        "move forward with other candidates",
        "not be moving forward",
        "decided not to proceed",
        "unfortunately",                          # broad but useful in context
        "not selected",
        "will not be moving forward",
        "not moving forward with your application",
        "we have decided to pursue other candidates",
        "we won't be moving forward",
        "regret to inform",
        "after careful consideration",
        "position has been filled",
        "we will not be proceeding",
        "not a match for",
        "we have chosen to move forward with another",
        "keep your resume on file",
        "we've decided to go in a different direction",
        "no longer being considered",
    ],
    "interview": [
        "schedule a call",
        "schedule an interview",
        "interview invitation",
        "invited to interview",
        "next round",
        "next step",
        "online assessment",
        "coding challenge",
        "technical assessment",
        "take-home assignment",
        "would like to speak with you",
        "would love to connect",
        "phone screen",
        "video interview",
        "virtual interview",
        "hiring manager would like",
        "recruiter would like",
        "move you forward",
        "advance to the next",
        "proceed to the next stage",
        "hackerrank test",
        "codesignal assessment",
        "amcat test",
        "please select a time",
        "book a slot",
        "calendly",                               # scheduling link
        "please use the link below to schedule",
    ],
    "offer": [
        "pleased to offer",
        "offer letter",
        "extend an offer",
        "we are delighted to offer",
        "job offer",
        "offer of employment",
        "we'd like to offer you",
        "we would like to offer you",
        "congratulations",                         # context-dependent; LLM backs up
        "compensation package",
        "start date",
        "welcome aboard",
        "joining date",
        "onboarding",
    ],
}

# Minimum number of keyword hits required to return a confident status match.
# Set to 1 because each phrase is specific enough; raise to 2 if you get
# false positives in your inbox.
STATUS_CONFIDENCE_THRESHOLD = 1

# ---------------------------------------------------------------------------
# LAYER 2 CONSTANTS
# ---------------------------------------------------------------------------

# Phrases that indicate a broadcast / alert rather than a personal response.
# If any of these appear prominently in the email, it's not a real application
# acknowledgement — it's marketing or a job-recommendation digest.
BROADCAST_PHRASES: list[str] = [
    "jobs recommended for you",
    "based on your profile",
    "you may be interested in",
    "hi jobseeker",
    "dear jobseeker",
    "dear candidate",
    "new jobs matching",
    "similar jobs",
    "jobs matching your search",
    "top picks for you",
    "jobs you might like",
    "explore these opportunities",
    "view all jobs",
    "unsubscribe",          # newsletters almost always have this
    "weekly digest",
    "daily digest",
    "job alert",
    "contest alert",        # LeetCode / HackerRank weekly contests
    "weekly contest",
    "coding contest",
    "register now",         # event invites, not application acks
    "register for free",
]

# Regex to detect multiple distinct job listing links in the body.
# A real application acknowledgement email contains AT MOST one job link
# (the one you applied to). A digest/alert contains several.
_JOB_LINK_RE = re.compile(
    r'https?://[^\s"\'<>]*(?:job|position|opening|career|apply)[^\s"\'<>]*',
    re.IGNORECASE,
)
BROADCAST_LINK_THRESHOLD = 3  # ≥ this many job links → treat as broadcast


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace. Used for matching."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text.lower()).strip()


def _full_text(email: dict) -> str:
    """Concatenate subject + snippet + body into one searchable string."""
    parts = [
        email.get("subject", ""),
        email.get("snippet", ""),
        email.get("body", ""),
    ]
    return _normalise(" ".join(p for p in parts if p))


def _sender_domain(email: dict) -> str:
    """Extract domain from sender address, lower-cased."""
    raw = email.get("sender_domain", "") or email.get("sender", "")
    # If it looks like a full address, pull the domain part
    match = re.search(r"@([\w.\-]+)", raw)
    if match:
        return match.group(1).lower()
    return raw.lower()


# ---------------------------------------------------------------------------
# LAYER 1 — Sender Filter
# ---------------------------------------------------------------------------

def passes_sender_filter(email: dict) -> bool:
    """
    LAYER 1 — cheapest gate, runs first, kills the most noise.

    Strategy:
      • If the sender is a known ATS domain → immediately pass (True).
        We skip further checks because Greenhouse / Lever / Workday etc.
        only send mail about applications you submitted.
      • If the sender domain is in DENYLIST_DOMAINS → reject (False).
        This covers job-alert platforms, coding-contest sites, newsletters.
      • If the sender address contains a DENYLIST_SENDER_PATTERN substring
        → reject (False). This catches generic "alerts@" and "digest@"
        addresses that don't share a denylisted domain.
      • Otherwise → pass (True) for deeper inspection.

    Why first? A domain check is O(1) and eliminates ~60-70 % of inbox noise
    before we even look at the email body.
    """
    domain = _sender_domain(email)
    sender = _normalise(email.get("sender", ""))

    # ATS domains are whitelisted — always a real application email
    if domain in ATS_DOMAINS:
        return True

    # Denylist domain check
    if domain in DENYLIST_DOMAINS:
        return False

    # Substring patterns in the full sender address
    for pattern in DENYLIST_SENDER_PATTERNS:
        if pattern in sender:
            return False

    return True


# ---------------------------------------------------------------------------
# LAYER 2 — Broadcast / Alert Detector
# ---------------------------------------------------------------------------

def is_application_email(email: dict) -> bool:
    """
    LAYER 2 — heuristics distinguishing a personal application response
    from a broadcast digest or job-recommendation alert.

    Signals (each is individually sufficient to return False):

      1. BROADCAST_PHRASES in body/subject — explicit alert/digest language.
         e.g. "jobs recommended for you", "based on your profile"

      2. Multiple job-listing links — a real acknowledgement email has ONE
         job URL (the role you applied to). Digests have many. We count
         distinct URLs containing job-related keywords.

    If none fire → assume it could be a real application email and let
    later layers decide.

    Why second? String matching is cheap (microseconds). We still want it
    AFTER the sender filter because some ATS platforms send marketing mail
    from the same domain as their application mail.
    """
    text = _full_text(email)
    body = _normalise(email.get("body", "") + " " + email.get("snippet", ""))

    # Signal 1: explicit broadcast / alert language
    for phrase in BROADCAST_PHRASES:
        if phrase in text:
            return False

    # Signal 2: too many distinct job-listing links → it's a digest
    job_links = _JOB_LINK_RE.findall(email.get("body", ""))
    if len(set(job_links)) >= BROADCAST_LINK_THRESHOLD:
        return False

    # Signal 3: unsolicited-phrasing check (weaker; must appear in body)
    unsolicited = [
        "based on your resume",
        "we found your profile",
        "your profile matches",
        "you might be a great fit",
        "we think you'd be a great",
    ]
    for phrase in unsolicited:
        if phrase in body:
            return False

    return True


# ---------------------------------------------------------------------------
# LAYER 3 — Keyword Status Detector
# ---------------------------------------------------------------------------

def detect_status(email: dict) -> str | None:
    """
    LAYER 3 — keyword matching against STATUS_KEYWORDS.

    Returns a status string ("applied" | "rejected" | "interview" | "offer")
    when a confident match is found, or None to hand off to the LLM.

    Design notes:
      • We match against the combined subject + snippet + body so short emails
        (where the subject carries the intent) are handled correctly.
      • We count hits per status and pick the one with the most hits. Ties
        are broken by priority order: offer > interview > rejected > applied
        (higher-stakes statuses win ties).
      • Why is keyword matching NOT sufficient alone?
        - "LeetCode Weekly Contest" contains words like "challenge" that
          could superficially match "interview". Layers 1-2 already killed
          that email before we get here.
        - "Congratulations on completing our assessment" could be applied
          or interview. The LLM resolves genuinely ambiguous cases.
      • STATUS_CONFIDENCE_THRESHOLD lets you require ≥ N hits before
        returning a match (default 1 — each phrase is specific enough).
    """
    text = _full_text(email)

    # Priority order: if scores tie, higher index wins
    priority = ["applied", "rejected", "interview", "offer"]
    scores: dict[str, int] = {s: 0 for s in priority}

    for status, phrases in STATUS_KEYWORDS.items():
        for phrase in phrases:
            if phrase in text:
                scores[status] += 1

    # Pick the highest-scoring status that meets the threshold
    best_status = None
    best_score = 0
    for status in priority:          # iterate in priority order
        if scores[status] >= STATUS_CONFIDENCE_THRESHOLD:
            if scores[status] >= best_score:
                best_score = scores[status]
                best_status = status

    return best_status  # None if no confident match


# ---------------------------------------------------------------------------
# LAYER 4 — LLM Classifier (Groq)
# ---------------------------------------------------------------------------

_LLM_PROMPT_TEMPLATE = """You are a classifier for a personal job-application tracker.

Your task: decide whether the email below is about a job application that the
RECIPIENT personally submitted (not a job alert, newsletter, or contest).

If YES, return strict JSON:
{{
  "company": "<company name, or null if unclear>",
  "role": "<job title / role, or null if unclear>",
  "status": "<one of: applied | rejected | interview | offer>"
}}

If NO (alert, newsletter, contest, unrelated, or ambiguous), return exactly:
null

Rules:
- Return ONLY the JSON object or the word null. No markdown, no explanation.
- "applied"  → acknowledgement that the application was received.
- "rejected" → the company is not moving the recipient forward.
- "interview"→ the company wants to schedule a call / assessment / next step.
- "offer"    → the company is extending a job offer.
- If you cannot determine status with reasonable confidence, return null.

---
FROM:    {sender}
SUBJECT: {subject}
DATE:    {date}

BODY (truncated to 1200 chars):
{body}
"""

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def classify_with_llm(email: dict) -> dict | None:
    """
    LAYER 4 — LLM classification via Groq.

    Fires ONLY when layers 1-3 couldn't make a confident decision.
    This keeps API costs low — the LLM processes only the ~10-20 % of emails
    that are genuinely ambiguous (e.g. a cold outreach from a recruiter, or
    an email with no clear status keywords).

    Prompt design:
      • We ask for strict JSON or the word "null" to make parsing reliable.
      • We truncate the body to 1200 chars — enough context, minimal tokens.
      • We strip markdown code fences and handle malformed output gracefully.
      • On any error (API failure, JSON parse error) we return None so the
        caller can decide to skip rather than crash the pipeline.
    """
    body_snippet = (email.get("body") or email.get("snippet") or "")[:1200]

    prompt = _LLM_PROMPT_TEMPLATE.format(
        sender=email.get("sender", ""),
        subject=email.get("subject", ""),
        date=email.get("date", ""),
        body=body_snippet,
    )

    try:
        response = _groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,      # deterministic — we want consistent JSON
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()
    except Exception as exc:
        # Network error, rate-limit, etc. — fail gracefully
        print(f"[classifier] Groq API error: {exc}")
        return None

    # Strip markdown code fences if the model wrapped its answer
    fence_match = _CODE_FENCE_RE.search(raw)
    if fence_match:
        raw = fence_match.group(1).strip()

    # Handle explicit null response
    if raw.lower() in ("null", "none", ""):
        return None

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Malformed output — treat as unclassifiable
        print(f"[classifier] Could not parse LLM output: {raw!r}")
        return None

    if not isinstance(parsed, dict):
        return None

    # Validate required fields
    status = parsed.get("status", "").lower()
    if status not in ("applied", "rejected", "interview", "offer"):
        return None

    return {
        "company": parsed.get("company"),
        "role": parsed.get("role"),
        "status": status,
    }


# ---------------------------------------------------------------------------
# LAYER 5 — Entity Resolution / Dedup
# ---------------------------------------------------------------------------

# Words stripped from company names before fuzzy comparison so that
# "Acme Inc." and "Acme" match, and "Google LLC" and "Google" match.
_COMPANY_NOISE_RE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|pvt|private|co|technologies|"
    r"solutions|services|group|global|international|software|systems|\.com)\b",
    re.IGNORECASE,
)


def _normalise_company(name: str | None) -> str:
    """Strip noise words and punctuation from a company name for comparison."""
    if not name:
        return ""
    name = _normalise(name)
    name = _COMPANY_NOISE_RE.sub("", name)
    name = re.sub(r"[^a-z0-9 ]", "", name)
    return name.strip()


def _role_overlap(role_a: str | None, role_b: str | None) -> float:
    """
    Simple word-overlap score in [0, 1] between two role strings.
    "Software Engineer Intern" vs "SWE Intern" → low overlap (≈0.25).
    "Software Engineer" vs "Software Engineer II" → high overlap (≈0.67).
    Not a fuzzy library — avoids an extra dependency for a good-enough match.
    """
    if not role_a or not role_b:
        return 0.0
    words_a = set(_normalise(role_a).split())
    words_b = set(_normalise(role_b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


ROLE_OVERLAP_THRESHOLD = 0.4  # ≥ 40 % word overlap → same role (tune if needed)


def resolve_entity(
    result: dict,
    existing_applications: list[dict],
) -> dict:
    """
    LAYER 5 — deduplication against already-tracked applications.

    Matching signals (in priority order):

      1. thread_id exact match — the strongest signal. Gmail threads all
         replies together, so the same thread_id means it's the same
         application conversation.

      2. Normalised company name match + fuzzy role overlap — catches cases
         where a company sends from a different thread (e.g. ATS system
         thread vs recruiter direct thread). We normalise both company names
         (strip "Inc", "LLC", ".com", etc.) and compute word-overlap on roles.

    Returns a dict with:
      {"match": True,  "id": <existing_id>, "existing": <existing_record>}  → update
      {"match": False}                                                        → insert new
    """
    thread_id = result.get("thread_id")
    company_norm = _normalise_company(result.get("company"))
    role = result.get("role")

    for app in existing_applications:
        # Signal 1: exact thread match
        if thread_id and app.get("thread_id") == thread_id:
            return {"match": True, "id": app.get("id"), "existing": app}

        # Signal 2: company name + role overlap
        if company_norm and _normalise_company(app.get("company")) == company_norm:
            overlap = _role_overlap(role, app.get("role"))
            if overlap >= ROLE_OVERLAP_THRESHOLD:
                return {"match": True, "id": app.get("id"), "existing": app}

    return {"match": False}


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def classify_email(email: dict) -> dict | None:
    """
    Classify a single email and return an application record or None.

    Pipeline:
      Layer 1 → Layer 2 → Layer 3 → (Layer 4 if needed)

    Returns:
      None   — discard; not a job application email.
      dict   — {"company", "role", "status", "thread_id"}

    Note: resolve_entity (Layer 5) is intentionally NOT called here.
    The pipeline / caller invokes it separately with the list of existing
    applications so this function stays pure and unit-testable.
    """
    # LAYER 1 — sender filter (O(1) set lookup)
    if not passes_sender_filter(email):
        return None

    # LAYER 2 — broadcast / alert heuristics
    if not is_application_email(email):
        return None

    # LAYER 3 — keyword status detection
    status = detect_status(email)

    if status:
        # Keyword match was confident — extract company/role via LLM
        # but only for entity extraction (status already known).
        # Cost note: this still calls the LLM, but passes the known status
        # so the model only needs to extract company + role.
        llm_result = classify_with_llm(email)
        company = llm_result.get("company") if llm_result else None
        role = llm_result.get("role") if llm_result else None
    else:
        # LAYER 4 — LLM for ambiguous cases
        llm_result = classify_with_llm(email)
        if not llm_result:
            return None
        status = llm_result["status"]
        company = llm_result.get("company")
        role = llm_result.get("role")

    return {
        "company": company,
        "role": role,
        "status": status,
        "thread_id": email.get("thread_id"),
    }


# ---------------------------------------------------------------------------
# UNIT TESTS
# ---------------------------------------------------------------------------

def _run_tests() -> None:
    """
    Quick smoke-tests. Run with:  python classifier.py

    These test layers 1-3 only (no LLM calls) so they're free and fast.
    Layer 4 (LLM) is tested by integration / end-to-end tests.
    """
    PASS = "\033[92mPASS\033[0m"
    FAIL = "\033[91mFAIL\033[0m"

    tests: list[tuple[str, dict, str | None]] = [
        # (description, email_dict, expected_status_or_None)

        # --- Should be discarded (return None) ---
        (
            "Naukri job alert → None",
            {
                "sender": "alerts@naukri.com",
                "sender_domain": "naukri.com",
                "subject": "New jobs matching your profile",
                "snippet": "5 new openings based on your profile",
                "body": "Hi Jobseeker, based on your profile we found jobs recommended for you. View all jobs.",
                "date": "2024-06-01",
                "thread_id": "thread_naukri_1",
                "message_id": "msg_1",
            },
            None,
        ),
        (
            "LeetCode weekly contest → None",
            {
                "sender": "do-not-reply@leetcode.com",
                "sender_domain": "leetcode.com",
                "subject": "LeetCode Weekly Contest 400 starts in 1 hour",
                "snippet": "Join the contest and compete with coders worldwide",
                "body": "Weekly Contest 400 is starting soon. Register now for free. Contest alert!",
                "date": "2024-06-02",
                "thread_id": "thread_lc_1",
                "message_id": "msg_2",
            },
            None,
        ),
        (
            "LinkedIn job alert digest → None",
            {
                "sender": "jobs-noreply@linkedin.com",
                "sender_domain": "linkedin.com",
                "subject": "3 new Software Engineer jobs for you",
                "snippet": "Jobs you might like this week",
                "body": (
                    "Hi, here are jobs matching your search. "
                    "https://linkedin.com/jobs/view/12345 "
                    "https://linkedin.com/jobs/view/67890 "
                    "https://linkedin.com/jobs/view/11111 "
                    "Unsubscribe from job alerts."
                ),
                "date": "2024-06-03",
                "thread_id": "thread_li_1",
                "message_id": "msg_3",
            },
            None,
        ),

        # --- Real application emails ---
        (
            "Rejection email → status rejected",
            {
                "sender": "recruiting@somecompany.com",
                "sender_domain": "somecompany.com",
                "subject": "Your application to Acme Corp",
                "snippet": "Unfortunately we will not be moving forward",
                "body": (
                    "Dear Applicant, thank you for your interest in Acme Corp. "
                    "After careful consideration, we have decided not to proceed "
                    "with your application. We will not be moving forward with "
                    "your candidacy at this time. We wish you the best."
                ),
                "date": "2024-06-04",
                "thread_id": "thread_acme_rej",
                "message_id": "msg_4",
            },
            "rejected",
        ),
        (
            "Interview invite via Greenhouse → status interview",
            {
                "sender": "no-reply@greenhouse.io",
                "sender_domain": "greenhouse.io",
                "subject": "Interview Invitation — Software Engineer at TechCorp",
                "snippet": "We'd like to schedule a call with you",
                "body": (
                    "Hi, congratulations on advancing! We would like to schedule "
                    "a video interview for the Software Engineer position. "
                    "Please use the link below to schedule a time that works for you."
                ),
                "date": "2024-06-05",
                "thread_id": "thread_tc_int",
                "message_id": "msg_5",
            },
            "interview",
        ),
        (
            "Application confirmation → status applied",
            {
                "sender": "careers@startup.io",
                "sender_domain": "startup.io",
                "subject": "We received your application",
                "snippet": "Thank you for applying to Startup Inc.",
                "body": (
                    "Hi, we have received your application for the Backend Engineer "
                    "role. Thank you for applying! We will review your application "
                    "and get back to you soon."
                ),
                "date": "2024-06-06",
                "thread_id": "thread_startup_app",
                "message_id": "msg_6",
            },
            "applied",
        ),
        (
            "Offer letter email → status offer",
            {
                "sender": "hr@bigcorp.com",
                "sender_domain": "bigcorp.com",
                "subject": "Offer Letter — Data Engineer",
                "snippet": "We are pleased to offer you the position",
                "body": (
                    "Dear Candidate, we are pleased to offer you the Data Engineer "
                    "role at BigCorp. Please find the offer letter attached. "
                    "Your start date and compensation package are detailed inside."
                ),
                "date": "2024-06-07",
                "thread_id": "thread_bigcorp_offer",
                "message_id": "msg_7",
            },
            "offer",
        ),
    ]

    # --- Layer 5 dedup tests ---
    existing_apps = [
        {"id": "app_001", "company": "Acme Corp", "role": "Software Engineer", "thread_id": "thread_acme_001"},
        {"id": "app_002", "company": "Google LLC",  "role": "Data Engineer",     "thread_id": "thread_google_002"},
    ]
    dedup_tests: list[tuple[str, dict, bool, str | None]] = [
        (
            "thread_id exact match → merge",
            {"company": "Acme Corp", "role": "SWE", "status": "rejected", "thread_id": "thread_acme_001"},
            True, "app_001",
        ),
        (
            "company+role fuzzy match → merge",
            {"company": "Google", "role": "Data Engineer II", "status": "interview", "thread_id": "thread_new"},
            True, "app_002",
        ),
        (
            "no match → new application",
            {"company": "Unknown Startup", "role": "Frontend Dev", "status": "applied", "thread_id": "thread_new_2"},
            False, None,
        ),
    ]

    print("\n=== Layer 1-3 Tests ===")
    all_pass = True
    for desc, email, expected_status in tests:
        # Manually run layers 1-3 without LLM to keep tests free
        if not passes_sender_filter(email):
            result_status = None
        elif not is_application_email(email):
            result_status = None
        else:
            result_status = detect_status(email)

        ok = result_status == expected_status
        all_pass = all_pass and ok
        icon = PASS if ok else FAIL
        print(f"  {icon}  {desc}")
        if not ok:
            print(f"       expected={expected_status!r}  got={result_status!r}")

    print("\n=== Layer 5 Dedup Tests ===")
    for desc, result, expect_match, expect_id in dedup_tests:
        resolution = resolve_entity(result, existing_apps)
        ok = resolution["match"] == expect_match and resolution.get("id") == expect_id
        all_pass = all_pass and ok
        icon = PASS if ok else FAIL
        print(f"  {icon}  {desc}")
        if not ok:
            print(f"       expected match={expect_match} id={expect_id!r}")
            print(f"       got     match={resolution['match']} id={resolution.get('id')!r}")

    print(f"\n{'All tests passed.' if all_pass else 'Some tests FAILED.'}\n")


if __name__ == "__main__":
    _run_tests()
