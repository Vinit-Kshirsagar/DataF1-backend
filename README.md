# DataF1 Backend

FastAPI backend for the DataF1 telemetry interpretation and insight system.

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values

# 4. Run database migrations
alembic upgrade head

# 5. Start server
uvicorn app.main:app --reload
```

## API Docs

Once running: http://localhost:8000/docs

## Dev Commands

```bash
black app/          # format
flake8 app/         # lint
mypy app/           # type check
pytest tests/       # run tests
```

## Architecture

- **FastAPI** — async REST API
- **SQLAlchemy (async)** — ORM with PostgreSQL
- **Redis** — telemetry + race data caching
- **FastF1** — F1 session and telemetry data
- **Claude Haiku** — AI insight summary generation
- **Alembic** — database migrations
