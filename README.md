# TopLine — Verified Gulf Construction Jobs Backend

TopLine is a job-access and application platform targeting Kenyan construction workers seeking employment opportunities in Gulf countries (Saudi Arabia, UAE, Qatar, Kuwait, Oman, Bahrain).

This backend replaces the static frontend mock data with a production-grade, database-backed modular monolith written in FastAPI and PostgreSQL.

---

## 1. Key Architecture & Features

- **Database-Backed Jobs**: Public jobs are served dynamically from PostgreSQL. Categorization, country filtering, search, and pagination are fully validated.
- **Separate Job Verification Process**: Jobs are not marked verified merely by publication. Verification decisions are recorded in an audit table (`job_verifications`) by authorized reviewers/administrators with evidence references (e.g. Ministry / Chamber of Commerce registration IDs).
- **Worker Registration & Security**:
  - Full name, normalized phone numbers (E.164 / Kenyan format `+254...`), trade, and preferred country.
  - OTP challenge verification with attempt limits and expiry.
  - Argon2id password hashing and JWT / HttpOnly session management.
  - Public registration strictly enforces the `worker` role; administrative privileges cannot be escalated publicly.
- **Platform Access Fee & Entitlement System**:
  - Worker pays server-controlled fee of **KSh 1,000** (stored strictly as `100,000` minor units).
  - Clean abstraction (`PaymentProvider`) separating Mock development from M-Pesa Daraja STK Push.
  - Idempotent callback processing preventing duplicate access or replay exploits.
  - Entitlements recorded independently from payment records.
- **Job Applications & Private Document Storage**:
  - Activated workers can apply to open jobs with a statement/cover letter and uploaded documents (CV, trade certificates).
  - Duplicate applications to the same job are rejected with HTTP 409.
  - Private filesystem / object storage abstraction using random cryptographic storage keys rather than user filenames.
  - Magic byte verification, MIME validation, and size limit checks (5MB).
  - Secure downloads authenticated via backend permission checks (IDOR protection).
- **Administrative Controls & Security Auditing**:
  - Complete `/api/v1/admin` suite for job authoring, publication, pausing, closing, verification, application status review, and audit trail inspection.

---

## 2. Getting Started (Local Development)

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or Docker)

### Installation

1. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Configure Environment Variables:
   ```bash
   cp .env.example .env
   ```

4. Database Setup & Migrations:
   Ensure PostgreSQL is running and the database user exists:
   ```sql
   CREATE USER topline WITH PASSWORD 'topline_secret';
   CREATE DATABASE topline_dev OWNER topline;
   CREATE DATABASE topline_test OWNER topline;
   ```
   Apply Alembic migrations:
   ```bash
   alembic upgrade head
   ```

5. Seed Demo Data:
   Seed default administrator account and 10 verified demonstration construction jobs:
   ```bash
   python scripts/seed_demo_data.py
   ```

6. Start Application Server:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   - Frontend UI: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - Interactive Swagger API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 3. Running Automated Tests

Run the complete test suite:
```bash
pytest -v tests/
```

Tests cover:
- Public job retrieval and exclusion of drafts/closed listings.
- Role escalation prevention on public registration.
- Worker permission boundary checks (preventing job creation/modification).
- Administrator lifecycle: create, publish, pause, and verify jobs.
- Entitlement checks preventing unactivated workers from applying.
- Activated worker application flow and duplicate application rejection.
- Secure private document upload, signature validation, size limit checks, and authorized download.
- Idempotent M-Pesa callback handling, validation of amount/currency, and prevention of duplicate entitlements.

---

## 4. Default Demonstration Credentials

- **Administrator**:
  - Phone: `+254700000001`
  - Password: `TopLineAdmin2026!`
- **Worker (Auto-created during UI test)**:
  - Default password for quick verify: `TopLineWorker2026!`

