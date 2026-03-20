# DataF1 — Backend

> Formula 1 telemetry interpretation and insight system — FastAPI backend

DataF1 is **not** an F1 stats app. It is a telemetry interpretation system that converts raw F1 data into visual graphs and plain-English AI summaries that any fan can understand. This repo is the Python backend that powers it.

---

## Tech Stack

| Concern | Library | Version |
|---|---|---|
| Framework | FastAPI + Uvicorn | 0.110.0 / 0.29.0 |
| Database ORM | SQLAlchemy (async) | 2.0.28 |
| Migrations | Alembic | 1.13.1 |
| F1 Data | FastF1 | 3.3.0 |
| Cache | Redis via redis-py | 7.2.4 / 5.0.1 |
| Auth | python-jose (JWT) + passlib (bcrypt) | 3.3.0 / 1.7.4 |
| AI Summaries | Anthropic Claude Haiku | — |
| Validation | Pydantic v2 | — |

---

## Project Structure

```
dataf1-backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, router includes
│   ├── config.py            # Environment variables via pydantic-settings
│   ├── database.py          # SQLAlchemy async engine and get_db() dependency
│   ├── redis_client.py      # Redis async connection singleton
│   ├── dependencies.py      # get_current_user() and shared FastAPI deps
│   ├── models/              # SQLAlchemy ORM models (database tables)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # FastAPI route handlers
│   └── services/            # Business logic layer
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files (one per schema change)
│   └── env.py               # Alembic config — uses psycopg2 for sync migrations
├── tests/                   # pytest test suite
├── Dockerfile               # Container for deployment
├── requirements.txt         # Python dependencies with pinned versions
└── .env.example             # Environment variable template
```

---

## Local Setup

### Prerequisites
- Python 3.11
- Redis (local or remote)
- PostgreSQL (Supabase free tier recommended)

### Steps

```bash
# 1. Clone and enter the project
git clone https://github.com/YOUR_USERNAME/dataf1-backend.git
cd dataf1-backend

# 2. Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your real values (see Environment Variables section)

# 5. Run database migrations
alembic upgrade head

# 6. Start the development server
uvicorn app.main:app --reload --host 0.0.0.0
```

Server runs at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
# PostgreSQL — use postgresql+asyncpg:// prefix (required for async SQLAlchemy)
DATABASE_URL="postgresql+asyncpg://postgres:password@db.xxx.supabase.co:5432/postgres"

# Redis — local or managed
REDIS_URL="redis://localhost:6379"

# JWT — use a long random string, keep this secret
JWT_SECRET="change_me_to_a_secure_random_string"

# FastF1 — local disk cache directory for F1 session data
FASTF1_CACHE_DIR="/tmp/fastf1"

# Anthropic — Claude API key for AI insight generation
ANTHROPIC_API_KEY="sk-ant-..."
```

> ⚠️ Never commit `.env` to Git. It is in `.gitignore`.

---

## API Endpoints

### Health
| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Basic health check |
| GET | `/health` | Health check including Redis status |

### Auth
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/auth/register` | Create new account | No |
| POST | `/auth/login` | Login, returns access + refresh tokens | No |
| POST | `/auth/refresh` | Exchange refresh token for new access token | No |
| GET | `/auth/me` | Get current authenticated user | Yes |

> More endpoints added in Blocks 2–6 (races, telemetry, predictions, user preferences)

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Check current migration state
alembic current

# View migration history
alembic history

# Auto-generate migration after changing a model
alembic revision --autogenerate -m "description of change"
```

> **Note:** Alembic uses `psycopg2` (sync) internally. The app uses `asyncpg` (async) at runtime. The `DATABASE_URL` in `.env` uses `postgresql+asyncpg://` — `alembic/env.py` swaps the driver automatically for migrations.

---

## Development Commands

```bash
# Format code
black app/

# Lint
flake8 app/

# Type check
mypy app/

# Run tests
pytest tests/

# Run with auto-reload (development)
uvicorn app.main:app --reload --host 0.0.0.0
```

All four must pass before any feature is considered complete.

---

## Architecture

```
Flutter App
    │  HTTP/REST (Dio)
    ▼
FastAPI Backend  ◄─── this repo
    ├── Redis          → telemetry cache (< 1s cached response)
    ├── PostgreSQL     → user accounts, saved preferences
    ├── FastF1         → F1 session and telemetry data
    └── Claude Haiku   → AI insight summary per graph
```

**Performance targets:**
- Cached API response: < 1 second
- Graph render end-to-end: < 3 seconds
- Graph render success rate: ≥ 95%

---

## Deployment

Backend deploys to **Render** (free tier).
Database hosted on **Supabase** (free tier).
Redis hosted on **Railway** (free tier).

---

## Build Status

| Block | Feature | Status |
|---|---|---|
| 0 | Project scaffold | ✅ Complete |
| 1 | Authentication | ✅ Complete |
| 2 | Home screen + Race selection | ✅ Complete |
| 3 | Telemetry graph + AI summary | ✅ Complete |
| 4 | Race results + Driver comparison | ⏳ Pending |
| 5 | Race prediction module | ⏳ Pending |
| 6 | Profile, preferences + polish | ⏳ Pending |
