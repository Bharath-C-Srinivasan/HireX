# HIREX — AI Interview Workflow & Evaluation API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Tests-17%20Passed-brightgreen.svg)]()

Production-grade, asynchronous backend engine for AI-assisted technical interviews. Built with **FastAPI**, **SQLAlchemy 2.0**, and **Pydantic v2**, HIREX manages the entire interview lifecycle: assessment setup, candidate screening, adaptive question sequencing, persistent answer storage, deterministic LLM evaluation, idempotency enforcement, and authorized recruiter reports.

---

## 🚀 Key Highlights & Capabilities

- **Finite State Machine:** Deterministic interview state progression (`created` ➔ `in_progress` ➔ `completed` / `failed` / `cancelled`).
- **Answer Persistence Before Evaluation:** Every candidate answer is durably saved in the database before invoking LLM adapters, ensuring zero data loss during external timeouts.
- **Strict Idempotency Engine:** `Idempotency-Key` header and payload tracking caches responses and prevents duplicate evaluations or duplicate database records on retries.
- **Adaptive Question Sequencing:** Automatically serves follow-up questions when an evaluation identifies ambiguous answers (e.g., detecting missing transaction boundaries).
- **Session Resumption After Refresh:** Candidates refreshing their browser or reconnecting seamlessly resume on their active question without state loss or double-advancement.
- **Recruiter Report with Direct Evidence:** Aggregates weighted competency scores, direct verbatim quotes from candidate transcripts, rubric criteria, and adapter versioning.
- **Strict Multi-Tenant RBAC:** Candidates can only access their own interviews and are strictly forbidden from viewing internal recruiter reports (`403 Forbidden`).
- **Defense-in-Depth Security:** Untrusted candidate answers are fenced inside strict XML delimiters to neutralize prompt injection; ethical guardrails prohibit demographic scoring.
- **LiveKit Voice Integration:** Clean adapter interface for WebRTC sessions, including token minting, HMAC-SHA256 webhook signature verification, and timestamp replay attack protection.
- **Structured Correlation Logging:** Every HTTP request is tagged with an `X-Request-ID` and logs output in structured JSON with automatic credential and PII masking.

---

## 📁 Repository Structure

```
d:\Project\HireX/
├── alembic/                      # Database migrations
│   ├── versions/                 # Versioned migration scripts
│   └── env.py                    # Alembic environment configuration
├── app/
│   ├── api/
│   │   └── v1/                   # API v1 route controllers
│   │       ├── assessments.py    # Assessment setup & question bank
│   │       ├── candidates.py     # Candidate registration & lookup
│   │       ├── interviews.py     # Interview lifecycle, answers, next-q, reports
│   │       ├── integrations.py   # LiveKit webhooks (HMAC verification)
│   │       └── auth.py           # JWT token generation helper
│   ├── core/
│   │   ├── config.py             # Pydantic Settings & environment variables
│   │   ├── database.py           # SQLAlchemy engine, session maker, WAL pragma
│   │   ├── logging.py            # Structured JSON logger with secret masking
│   │   ├── middleware.py         # Request correlation ID & timing middleware
│   │   └── security.py           # JWT encoding/decoding & RBAC dependencies
│   ├── db/
│   │   └── seed_data.py          # Sample assessment (Backend Engineering Intern)
│   ├── models/                   # SQLAlchemy database models
│   │   ├── entities.py           # Organization, Assessment, Interview, Answer, Evaluation...
│   │   └── enums.py              # Domain enumerations (InterviewStatus, UserRole...)
│   ├── schemas/                  # Pydantic v2 schemas for request/response validation
│   │   ├── assessment.py         # Assessment, Competency, Rubric schemas
│   │   ├── candidate.py          # Candidate schemas
│   │   ├── interview.py          # Interview, Answer, NextQuestion schemas
│   │   ├── llm.py                # LLMEvaluationResult schema (Score bounds 1-5)
│   │   ├── report.py             # Recruiter Report schemas
│   │   └── livekit.py            # LiveKit Token & Webhook schemas
│   ├── services/                 # Domain business logic
│   │   ├── assessment_service.py
│   │   ├── candidate_service.py
│   │   ├── interview_service.py  # Sequencing, adaptive follow-ups, resumption
│   │   ├── idempotency_service.py# Lock management & cached response replay
│   │   ├── evaluation_service.py # LLM adapter dispatch & timeout handling
│   │   ├── report_service.py     # Recruiter report aggregation
│   │   ├── livekit_service.py    # HMAC verification & token generation
│   │   └── llm/
│   │       ├── adapter.py        # LLM adapter interface & deterministic engine
│   │       ├── guardrails.py     # Anti-prompt injection & anti-bias defenses
│   │       └── exceptions.py     # LLMTimeoutError, LLMMalformedOutputError
│   └── main.py                   # FastAPI application initialization & lifespan
├── tests/                        # Automated test suite (17 comprehensive tests)
│   ├── conftest.py               # Isolated test database & fixtures
│   ├── test_assessments_auth.py  # Test 1: Recruiter-only assessment management
│   ├── test_candidate_access.py  # Test 2: Candidate resource isolation & privacy
│   ├── test_idempotency.py       # Test 3: Duplicate submission prevention
│   ├── test_llm_malformed.py     # Test 4: Malformed LLM output handling
│   ├── test_llm_timeout.py       # Test 5: LLM timeout recovery
│   ├── test_completed_interview.py # Test 6: Rejection on completed interviews
│   ├── test_concurrency.py       # Test 7: Race condition & double-advance defense
│   ├── test_report_integrity.py  # Test 8: Report data matches persisted evaluations
│   ├── test_adaptive_flow.py     # Test 9: Adaptive follow-up workflow
│   ├── test_livekit.py           # Test 10: LiveKit tokens & webhook replay protection
│   └── test_state_resume.py      # Test 11: State resumption after browser refresh
├── demo_walkthrough.py           # End-to-end interactive demo script
├── ARCHITECTURE.md               # 3-page in-depth technical architecture note
├── requirements.txt              # Production & test dependencies
├── pytest.ini                   # Pytest configuration
├── alembic.ini                   # Alembic configuration
└── README.md                     # Documentation
```

---

## 🛠️ Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.13)
- SQLite (built-in) or PostgreSQL

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/hirex/hirex-backend.git
cd HireX

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file from `.env.example`:
```bash
copy .env.example .env
```
Default configuration values:
```ini
DATABASE_URL=sqlite:///./hirex.db
SECRET_KEY=hirex-super-secret-development-key-change-in-production-2026
LLM_ADAPTER_TYPE=deterministic
LLM_ADAPTER_VERSION=hirex-adapter-v1.2.0
LLM_TIMEOUT_SECONDS=15.0
LIVEKIT_WEBHOOK_SECRET=whsec_hirex_webhook_secret_key
```

### 4. Database Setup & Seeding
Initialize the database and populate the **Backend Engineering Intern** assessment:
```bash
# Apply database migrations
alembic upgrade head

# Seed sample assessment, competencies, rubrics, and questions
python -m app.db.seed_data
```

### 5. Run Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc Documentation: `http://127.0.0.1:8000/redoc`

---

## 🧪 Automated Testing

HIREX includes **17 automated tests** (exceeding the 8 required minimum), covering edge cases, race conditions, timeout recoveries, and security checks:

```bash
pytest -v
```

### Test Suite Summary
| Test File | Scenario Verified | Status |
| :--- | :--- | :---: |
| `tests/test_assessments_auth.py` | Only authorized recruiters can create/manage assessments (403 for candidate/anonymous) | **PASSED** |
| `tests/test_candidate_access.py` | Candidates cannot access another candidate's interview or recruiter report (403) | **PASSED** |
| `tests/test_idempotency.py` | Duplicate submissions with same key produce identical response; exactly 1 record in DB | **PASSED** |
| `tests/test_llm_malformed.py` | Malformed LLM output is rejected safely without crashing; leaves status `failed` | **PASSED** |
| `tests/test_llm_timeout.py` | LLM timeout leaves interview in recoverable state; does not falsely complete interview | **PASSED** |
| `tests/test_completed_interview.py` | Completed interviews reject further answers unless explicitly reopened by recruiter | **PASSED** |
| `tests/test_concurrency.py` | Concurrent simultaneous submissions do not advance interview twice or double-insert | **PASSED** |
| `tests/test_report_integrity.py` | Report scores and evidence match persisted evaluation database records exactly | **PASSED** |
| `tests/test_adaptive_flow.py` | Adaptive follow-up question is generated when `follow_up_needed` is true | **PASSED** |
| `tests/test_livekit.py` | LiveKit token generation, HMAC-SHA256 signature check & timestamp replay protection | **PASSED** |
| `tests/test_state_resume.py` | Candidate refreshing browser resumes on the exact active question without skipping | **PASSED** |

---

## 🎬 Repeatable End-to-End Walkthrough

Run the standalone demo walkthrough script to verify the entire happy-path, adaptive workflow, idempotency replay, and report generation in seconds:

```bash
python demo_walkthrough.py
```

### What the Walkthrough Proves:
1. Seeds **Backend Engineering Intern** assessment with 5 competencies: Python/FastAPI, SQL/data modeling, API security, testing/debugging, and problem-solving.
2. Mints signed JWTs for **Jane Recruiter** and **Alex Chen**.
3. Creates the interview and requests Question 1: *"Two identical answer submissions arrive after a client timeout. How do you prevent duplicate evaluation?"*
4. Submits an answer with `Idempotency-Key` omitting transaction boundaries.
5. Verifies the LLM evaluation:
   ```json
   {
     "scores": {"api_design": 4, "data_integrity": 3},
     "evidence": ["Candidate described a unique constraint"],
     "follow_up_needed": true,
     "follow_up_topic": "transaction boundaries"
   }
   ```
6. Re-submits with the same key to verify an immediate **Idempotency HIT** without duplicating answers or evaluations.
7. Calls `/next-question` and receives the dynamically generated **Adaptive Follow-Up Question** on transaction boundaries.
8. Answers the follow-up, completes remaining question bank items, and transitions to `completed`.
9. Verifies security: candidate is rejected from accessing recruiter report (`403 Forbidden`).
10. Generates and displays the authorized **Recruiter Evaluation Report** with overall score (4.05/5.0), **STRONG HIRE** recommendation, competency breakdowns, and candidate quotes.

---

## 📡 API Reference & cURL Examples

### 1. Authenticate / Mint Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "recruiter-123",
    "email": "recruiter@acme.com",
    "role": "recruiter",
    "organization_id": "org-456"
  }'
```

### 2. Create Assessment (Recruiter Only)
```bash
curl -X POST "http://localhost:8000/api/v1/assessments" \
  -H "Authorization: Bearer <RECRUITER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backend Engineering Intern",
    "role": "Backend Engineering Intern",
    "job_description": "Screening for Python, SQL, and API security.",
    "competencies": [
      {
        "name": "Python/FastAPI",
        "weight": 1.2,
        "rubric": {
          "min_score": 1,
          "max_score": 5,
          "criteria": "Evaluates knowledge of idempotency, REST design, and FastAPI."
        },
        "questions": [
          {
            "prompt": "Two identical answer submissions arrive after a client timeout. How do you prevent duplicate evaluation?",
            "difficulty": "medium",
            "question_type": "technical"
          }
        ]
      }
    ]
  }'
```

### 3. Register Candidate
```bash
curl -X POST "http://localhost:8000/api/v1/candidates" \
  -H "Authorization: Bearer <RECRUITER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alex.chen@example.com",
    "full_name": "Alex Chen",
    "resume_text": "CS student with FastAPI & PostgreSQL experience."
  }'
```

### 4. Create Interview
```bash
curl -X POST "http://localhost:8000/api/v1/interviews" \
  -H "Authorization: Bearer <RECRUITER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "<ASSESSMENT_ID>",
    "candidate_id": "<CANDIDATE_ID>"
  }'
```

### 5. Get Next Question (Candidate / Adaptive)
```bash
curl -X GET "http://localhost:8000/api/v1/interviews/<INTERVIEW_ID>/next-question" \
  -H "Authorization: Bearer <CANDIDATE_TOKEN>"
```

### 6. Submit Answer (with Idempotency-Key)
```bash
curl -X POST "http://localhost:8000/api/v1/interviews/<INTERVIEW_ID>/answers" \
  -H "Authorization: Bearer <CANDIDATE_TOKEN>" \
  -H "Idempotency-Key: idemp-client-tx-999" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "<QUESTION_ID>",
    "transcript_text": "I use an idempotency key with a unique constraint in PostgreSQL and wrap it in a transaction.",
    "idempotency_key": "idemp-client-tx-999"
  }'
```

### 7. Get Authorized Recruiter Report (Recruiter Only)
```bash
curl -X GET "http://localhost:8000/api/v1/interviews/<INTERVIEW_ID>/report" \
  -H "Authorization: Bearer <RECRUITER_TOKEN>"
```

### 8. LiveKit Webhook Receiver (HMAC-SHA256 Signed)
```bash
curl -X POST "http://localhost:8000/api/v1/integrations/livekit/webhook" \
  -H "LiveKit-Signature: <HMAC_SHA256_HEX>" \
  -H "LiveKit-Timestamp: <EPOCH_SECONDS>" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "participant_joined",
    "room": {"name": "hirex-interview-<INTERVIEW_ID>"},
    "participant": {"identity": "candidate-123"}
  }'
```

---

## 🛡️ Reliability & Failure Handling Strategies

1. **Client Timeouts / Network Drops:**
   - The candidate can safely re-send the request with the same `Idempotency-Key`. The backend detects the completed key and returns the identical cached response without invoking the LLM again.
2. **LLM Timeout:**
   - The LLM adapter enforces a timeout threshold (`LLM_TIMEOUT_SECONDS = 15.0`). If a timeout occurs, the evaluation record status is set to `failed`, but the interview **remains in progress**. The answer is preserved, allowing safe retries.
3. **Malformed LLM Output:**
   - LLM responses are parsed and validated via Pydantic schema rules (ensuring score bounds 1-5 and non-empty evidence arrays). If unparseable output is returned, retries are executed up to `LLM_MAX_RETRIES`. Unresolvable failures log structured alerts and flag the evaluation for retry.
4. **Concurrent Requests Race Conditions:**
   - Database unique constraints on `(interview_id, question_id, idempotency_key)` block concurrent double inserts.
   - The `Interview.version` field prevents simultaneous requests from double-advancing the state machine.
5. **State Resumption After Refresh:**
   - If the candidate reloads their browser mid-interview, `GET /next-question` identifies that the current question is still unanswered and re-serves it with `is_resumed: True`.

---

## 🔮 Production Roadmap & Outbox Pattern

For scaling HIREX to high-concurrency production deployments:

1. **Background Evaluation Workers:**
   - Move LLM evaluations from HTTP request cycle to distributed background task queues (Celery, Arq, or Temporal), exposing evaluation progress via WebSocket or Server-Sent Events (SSE).
2. **Transactional Outbox Pattern:**
   - Replace in-process event emission with a database `outbox_events` table written inside the same ACID transaction as the `Answer` commit.
   - Use an Outbox Relay (or Debezium CDC) to stream events into Apache Kafka or RabbitMQ with at-least-once delivery guarantees.
3. **Real-time LiveKit Agent:**
   - Integrate LiveKit Agents Python SDK to connect directly to WebRTC audio rooms, handle real-time Silero VAD (Voice Activity Detection), and stream live speech-to-text transcripts into the HIREX answer ingestion pipeline.
4. **PostgreSQL Read Replicas:**
   - Route read-heavy recruiter report queries and candidate resume checks to read replicas, preserving the primary database for interview state transitions and idempotency locks.

---

## 📄 License
This project is licensed under the MIT License.
