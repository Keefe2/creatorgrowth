# CreatorGrowth 🚀

Full-stack creator growth platform — AI content studio, auto-scheduling,
multi-platform account management, analytics dashboard aur comment queue,
ek hi secure app mein.

## Tech Stack

| Layer    | Tech |
|----------|------|
| Backend  | FastAPI (Python 3.12), SQLAlchemy 2.0, Pydantic v2 |
| Frontend | React 18, Vite, Tailwind CSS, Recharts |
| DB       | SQLite (dev) → PostgreSQL-ready via `DATABASE_URL` |
| Jobs     | APScheduler (background auto-publisher, har 60 sec) |
| Tests    | pytest — 21 tests, sab pass |

## Quickstart

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env mein JWT_SECRET aur ENCRYPTION_KEY generate karke dalo:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
API docs: http://127.0.0.1:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (API proxy built-in)
```

### Tests
```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```

## Features
- **Auth**: register/login, JWT access (15 min) + rotating refresh tokens (7 din), logout revocation
- **Content Studio**: AI copy generator (Urdu/English, 4 tones, platform-shaped hashtags), drafts, future scheduling
- **Auto-publisher**: background worker har 60 sec due posts publish karta hai (dry-run adapters — real platform API lagana ek class ka kaam hai, `app/publishers.py` dekho)
- **Accounts**: social accounts connect — tokens Fernet-encrypted at rest, API kabhi raw token wapas nahi bhejta
- **Analytics**: snapshots + auto-aggregated dashboard (followers/impressions/engagement, per-platform charts)
- **Comments**: reply queue with done-tracking
- **Audit log**: har sensitive action IP ke sath log hota hai

## Security (built-in, tested)
- bcrypt cost-12 password hashing, kabhi plaintext nahi
- Rate limiting: login 5/min, register 10/hour (slowapi)
- Security headers: CSP, X-Frame-Options DENY, nosniff, Referrer-Policy, HSTS (prod)
- CORS allowlist (env-configured), credentials-safe
- Pydantic validation on every input — SQL injection surface zero (ORM only, no raw SQL)
- Refresh-token rotation: purana token reuse = instant reject
- Secrets sirf environment se — `.env` kabhi commit mat karo

## Project Structure
```
backend/
  app/
    main.py          # app wiring, CORS, lifespan
    config.py        # env-based settings
    models.py        # 7 tables (users, tokens, accounts, posts, comments, analytics, audit)
    security.py      # bcrypt, JWT, Fernet
    auth.py          # current-user dependency + audit helper
    middleware.py    # security headers
    rate_limit.py    # slowapi limiter
    ai_engine.py     # content generator (LLM-swappable)
    publishers.py    # platform adapters (dry-run → real API)
    scheduler.py     # background auto-publisher
    routers/         # auth, accounts, content, analytics, comments
  tests/             # 21 tests: auth, content, security
frontend/
  src/
    api/client.js        # axios + auto token-refresh
    context/AuthContext  # session state
    components/Layout    # sidebar shell
    pages/               # Login, Register, Dashboard, Studio, Accounts, Analytics, Comments
```
