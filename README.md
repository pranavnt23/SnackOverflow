# Snack Overflow 🍿

An office pantry tracker built as a production-minded full-stack application.

## Tech Stack
- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0 (Sync), Alembic, Pydantic v2
- **Database**: PostgreSQL (hosted on Supabase, connected as plain Postgres)
- **Frontend**: React + TypeScript (Vite) *(scaffolded in subsequent step)*

---

## Repository Structure

```text
SnackOverflow/
├── backend/
│   ├── alembic/              # Database migration scripts & configuration
│   ├── app/
│   │   ├── routers/          # API route definitions
│   │   ├── services/         # Business logic layer
│   │   ├── config.py         # Pydantic Settings & environment config
│   │   ├── database.py       # SQLAlchemy engine & session factory
│   │   ├── deps.py           # Dependency injection (DB session, auth)
│   │   ├── errors.py         # Standardized error definitions & handlers
│   │   ├── main.py           # FastAPI application entrypoint & /health
│   │   ├── models.py         # SQLAlchemy ORM declarative models
│   │   └── schemas.py        # Pydantic schemas (request/response)
│   ├── scripts/              # Utility & management scripts
│   ├── tests/                # Test suite
│   ├── .env.example          # Environment variable template
│   ├── alembic.ini           # Alembic migration configuration
│   └── requirements.txt      # Pinned Python dependencies
├── frontend/                 # React + TypeScript placeholder
├── docs/
│   └── CONTEXT.md            # System architecture & domain rules
├── .gitignore
└── README.md
```

---

## Quickstart Guide

### 1. Backend Setup

From the root directory:

```bash
# Navigate to backend
cd backend

# Create virtual environment (Python 3.10+ / 3.11+)
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS/Linux:
# source venv/bin/activate

# Install pinned dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env with your PostgreSQL credentials and JWT secret
```

### 2. Run Database Migrations

```bash
# Run migrations using Alembic
alembic upgrade head
```

### 3. Start Development Server

```bash
# Start FastAPI with Uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify that the server and database are healthy:
```bash
curl http://localhost:8000/health
# Response: {"status":"ok","database":"connected"}
```

---

## Architectural Guarantees & Domain Rules

See [docs/CONTEXT.md](file:///d:/Projects/SnackOverflow/docs/CONTEXT.md) for full context.

1. **Derived Snack Status**: Status (`stocked`, `running_low`, `gone`) is calculated dynamically from `quantity` and `low_stock_threshold`. It is never stored in the database to prevent stale state.
2. **Atomic Stock Consumption**: Consume operations execute as single conditional `UPDATE` statements at the database level (`WHERE quantity >= :amount`), avoiding in-memory race conditions.
3. **One Vote Per User Per Snack**: Enforced by a composite primary key `(user_id, snack_id)` on the `votes` table.
4. **Audit Trail**: Every restock and consume transaction logs an immutable `activities` row in the same atomic database transaction.
5. **Uniform Error Format**: All API error responses return `{"error": {"code": "...", "message": "..."}}`.
