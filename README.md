# Snack Overflow 🍿

An office pantry tracker and stock management system built as a production-minded full-stack application.

Snack Overflow provides real-time pantry inventory visibility, atomic stock consumption, employee snack voting, and transactional audit logging with server-enforced role authorization.

---

## Tech Stack

| Layer | Technology | Key Details |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite | Mobile-first SPA, Tailwind CSS, Lucide icons, React Router v6, typed API client (zero UI kits, zero Redux) |
| **Backend** | FastAPI (Python 3.10+ / 3.11+) | SQLAlchemy 2.0 (Sync), Alembic, Pydantic v2, PyJWT, direct `bcrypt` hashing |
| **Database** | PostgreSQL (hosted on Supabase) | Accessed strictly as raw PostgreSQL via SQLAlchemy; no Supabase client libraries or Supabase Auth |
| **Testing** | Pytest, TestClient | Dedicated `snack_overflow_test` database, multi-threaded concurrency testing with `threading.Barrier` |

---

## System Architecture Diagram

```text
+----------------------------------------------------------------------------------------------------+
|                                         CLIENT BROWSERS                                            |
|   Desktop Web (Table View)  |  Mobile Web (Card View / 375px)  |  Admin Console (Modals & Actions) |
+----------------------------------------------------------------------------------------------------+
                                                  │
                                                  │ HTTP / JSON (Bearer JWT in Authorization Header)
                                                  ▼
+----------------------------------------------------------------------------------------------------+
|                                       FASTAPI APPLICATION LAYER                                    |
|                                                                                                    |
|  [CORS Middleware] ────────► [Global Error Envelope Handler] {"error": {"code", "message"}}        |
|                                                                                                    |
|  [Routers]                                                                                         |
|    ├── /auth/login, /auth/me       (Direct bcrypt validation, PyJWT HS256 tokens)                  |
|    ├── /health                     (SELECT 1 database connectivity ping)                           |
|    └── /snacks                     (Catalogue, summary, consume, restock, votes)                   |
|                                                                                                    |
|  [Dependencies & Guards]                                                                           |
|    ├── get_db                      (Per-request SQLAlchemy session with connection checkout)       |
|    ├── get_current_user            (Decodes JWT, fetches fresh User from DB on EVERY request)      |
|    └── require_admin               (Enforces role == 'admin', 403 FORBIDDEN if violated)           |
+----------------------------------------------------------------------------------------------------+
                                                  │
                                                  │ SQLAlchemy 2.0 (Session Mode Pooler: 5432)
                                                  ▼
+----------------------------------------------------------------------------------------------------+
|                                    POSTGRESQL DATABASE (SUPABASE)                                  |
|                                                                                                    |
|  [Atomic Transactions]                                                                             |
|    • Single conditional UPDATE: WHERE id = :id AND quantity >= :amount RETURNING quantity, name   |
|    • Exclusive row-level write locks (FOR UPDATE) under READ COMMITTED isolation                   |
|    • Immediate activity audit row insert within the EXACT SAME transaction                         |
|                                                                                                    |
|  [Tables & Invariants]                                                                             |
|    ├── users       (id PK, email UNIQUE, password_hash, role ENUM)                                 |
|    ├── snacks      (id PK, name UNIQUE, category ENUM, quantity >= 0, threshold >= 0)              |
|    ├── votes       (PRIMARY KEY (user_id, snack_id) - DB enforced 1 vote per user per snack)       |
|    └── activities  (id PK, snack_id NULLABLE ON DELETE SET NULL, snack_name snapshot, amount > 0)  |
+----------------------------------------------------------------------------------------------------+
```

---

## Quickstart Setup Guide (5 Minutes)

### 1. Prerequisites
- Python 3.10+ or 3.11+
- Node.js 18+ or 20+ (with `npm`)
- PostgreSQL database instance (Supabase or local PostgreSQL)

---

### 2. Backend Setup & Configuration

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Activate on macOS/Linux:
# source venv/bin/activate

# 3. Install pinned Python dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
```

Edit `backend/.env` with your PostgreSQL credentials:
```env
# Primary PostgreSQL connection (Supabase IPv4 connection pooler)
DATABASE_URL=postgresql://postgres.gjwabguslluaylykcnnu:bkJ8EAy9R46vtEqp@aws-1-ap-south-1.pooler.supabase.com:5432/postgres

# Dedicated test database (must be different from DATABASE_URL)
TEST_DATABASE_URL=postgresql://postgres.gjwabguslluaylykcnnu:bkJ8EAy9R46vtEqp@aws-1-ap-south-1.pooler.supabase.com:5432/snack_overflow_test

JWT_SECRET=production-grade-snack-overflow-secret-key-32-bytes
JWT_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

### 3. Run Database Migrations & Seed Data

```bash
# Apply database schema migrations
alembic upgrade head

# Seed initial admin, member, and 13 sample pantry snacks (idempotent)
python scripts/seed.py
```

---

### 4. Start the Backend Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Verify the health check endpoint:
```bash
curl http://localhost:8000/health
# Response: {"status":"ok","database":"connected"}
```

---

### 5. Frontend Setup & Launch

Open a separate terminal window:
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Create .env from template
cp .env.example .env

# 4. Start Vite development server
npm run dev
```
Open **http://localhost:5173** in your browser.

---

### 6. Run the Test Suite

The test suite runs against the dedicated `TEST_DATABASE_URL` (`snack_overflow_test`) and refuses to run against the production database:
```bash
cd backend
.\venv\Scripts\python.exe -m pytest
```
*Result: 26 passed tests including multi-threaded concurrency with `threading.Barrier`.*

---

## Demo User Credentials

The seed script creates two demo accounts with pre-hashed bcrypt passwords:

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Admin** | `admin@snack.local` | `Admin@123` | Full access: Add snacks, edit metadata, restock inventory, delete snacks, consume, vote |
| **Member** | `member@snack.local` | `Member@123` | Standard access: Browse pantry, filter, search, consume stock, vote/unvote |

*Note: The login page includes quick-fill buttons to auto-populate either account in one click.*

---

## API Endpoint Reference

All endpoints return uniform error envelopes `{"error": {"code": "...", "message": "..."}}`.

| Method | Endpoint | Authorization | Description | Status Codes |
|---|---|---|---|---|
| `GET` | `/health` | Public | Connectivity probe (`SELECT 1`) | `200` |
| `POST` | `/auth/login` | Public | Authenticate user, returns JWT and user payload | `200`, `401`, `422` |
| `GET` | `/auth/me` | Bearer Token | Fetch current authenticated user record from DB | `200`, `401` |
| `GET` | `/snacks/summary` | Bearer Token | Grouped stock metrics & Snack of the Week | `200`, `401` |
| `GET` | `/snacks` | Bearer Token | Paginated inventory listing with SQL search & filters | `200`, `401`, `422` |
| `GET` | `/snacks/{id}` | Bearer Token | Fetch single snack with derived status and vote state | `200`, `401`, `404` |
| `POST` | `/snacks` | Admin Only | Add new snack to catalogue | `201`, `401`, `403`, `409`, `422` |
| `PATCH` | `/snacks/{id}` | Admin Only | Edit snack metadata (quantity update forbidden) | `200`, `401`, `403`, `404`, `409`, `422` |
| `DELETE`| `/snacks/{id}` | Admin Only | Delete snack (cascades votes, sets activity ID null) | `204`, `401`, `403`, `404` |
| `POST` | `/snacks/{id}/consume` | Bearer Token | **Atomic stock decrement** & activity audit log | `200`, `401`, `404`, `409`, `422` |
| `POST` | `/snacks/{id}/restock` | Admin Only | **Atomic stock increment** & activity audit log | `200`, `401`, `403`, `404`, `422` |
| `POST` | `/snacks/{id}/vote` | Bearer Token | Cast vote (enforces 1 vote per user per snack) | `201`, `401`, `404`, `409` |
| `DELETE`| `/snacks/{id}/vote` | Bearer Token | Withdraw existing vote | `200`, `401`, `404` |

---

## Database Schema & Integrity Guarantees

```text
               +-------------------------+
               |          users          |
               +-------------------------+
               | id (PK)                 |
               | name                    |
               | email (UNIQUE, INDEX)   |
               | password_hash           |
               | role (ENUM)             |
               | created_at              |
               +-------------------------+
                 │                     │
      1:N        │                     │ 1:N
   (CASCADE)     │                     │ (SET NULL)
                 ▼                     ▼
        +------------------+    +--------------------------------+
        |      votes       |    |           activities           |
        +------------------+    +--------------------------------+
        | user_id (PK, FK) |    | id (PK)                        |
        | snack_id (PK, FK)│    | user_id (FK, NULLABLE)         |
        | created_at       |    | snack_id (FK, NULLABLE)        |
        +------------------+    | snack_name (VARCHAR snapshot)  |
                 ▲              | action (ENUM: restock/consume) |
                 │              | amount (CHECK > 0)             |
                 │ 1:N (CASCADE)| quantity_after                 |
                 │              | created_at                     |
        +------------------+    +--------------------------------+
        |      snacks      |
        +------------------+
        | id (PK)          |
        | name (UNIQUE)    |
        | category (ENUM)  |
        | quantity (>= 0)  |
        | low_stock_thresh |
        | created_at       |
        | updated_at       |
        +------------------+
```

### Why These Schema Invariants Exist:
1. **Derived Snack Status (Never Stored)**:
   Status is calculated in SQL using a `CASE` expression:
   - `gone`: `quantity == 0`
   - `running_low`: `1 <= quantity <= low_stock_threshold`
   - `stocked`: `quantity > low_stock_threshold`
   *Why:* Storing status as a column causes state synchronization drift whenever quantity changes.
2. **Database CHECK Constraints**:
   - `ck_snacks_quantity_non_negative`: `quantity >= 0`
   - `ck_snacks_threshold_non_negative`: `low_stock_threshold >= 0`
   - `ck_activities_amount_positive`: `amount > 0`
   *Why:* Guarantees corrupt data cannot enter storage even if application code fails.
3. **Composite Primary Key on `votes(user_id, snack_id)`**:
   *Why:* Enforces at the database storage engine level that a user can vote for a given snack at most once. Concurrent duplicate clicks trigger a PostgreSQL unique violation mapped cleanly to `409 ALREADY_VOTED`.
4. **Activity Audit Trail with Name Snapshotting**:
   *Why:* `snack_id` has `ON DELETE SET NULL`, while `snack_name` is snapshotted as a string column. If an admin deletes a snack, past restock and consume audit history remains intact.

---

## How Concurrency & Atomicity Are Handled

### 1. The Atomic Conditional UPDATE
Stock consumption avoids Time-of-Check to Time-of-Use (TOCTOU) race conditions by executing a single atomic conditional update:
```sql
UPDATE snacks
SET quantity = quantity - :amount, updated_at = now()
WHERE id = :id AND quantity >= :amount
RETURNING quantity, name;
```

#### Row Locking & `READ COMMITTED` Mechanics:
- When 10 concurrent requests arrive for the last 3 packets, each transaction attempts this `UPDATE`.
- PostgreSQL acquires an **exclusive row-level write lock** (`FOR UPDATE`) for the first transaction.
- The remaining 9 transactions **block** on the row lock.
- When Transaction 1 commits, Transaction 2 wakes up and evaluates the `WHERE` clause against the newly committed row state.
- Once stock reaches 0, the `quantity >= :amount` clause evaluates to `FALSE` for subsequent transactions.
- Zero rows are updated, `RETURNING` produces empty results, the transaction rolls back, and FastAPI returns `409 INSUFFICIENT_STOCK`.

### 2. Atomic Audit Logging in the Same Transaction
In [snack_service.py](file:///d:/Projects/SnackOverflow/backend/app/services/snack_service.py):
The decrement and the activity insert occur in the **exact same database transaction**:
```python
# 1. Atomic conditional update
result = db.execute(stmt)
row = result.first()

if row is not None:
    quantity_after, snack_name = row
    # 2. Insert audit log in same transaction
    activity = Activity(user_id=current_user_id, snack_id=snack_id, snack_name=snack_name, ...)
    db.add(activity)
    db.commit() # Atomic commit for both changes
```
If logging fails or the process crashes, the transaction rolls back completely—a stock change never exists without its audit log.

### 3. Server-Enforced Authorization
- Tokens are signed with PyJWT HS256 (`sub: user_id`).
- On every protected request, `get_current_user` performs a fresh `db.get(User, user_id)` lookup. If an admin demotes or deletes a user, their privileges are revoked immediately without waiting for token expiration.
- Admin-only routes are protected by `require_admin`, returning `403 FORBIDDEN` for members.

---

## Core Assumptions
1. **Snack of the Week**: Defined as the snack with the most total votes in `votes`. Ties are broken alphabetically by snack name ascending (`ORDER BY count(votes) DESC, name ASC`). Returns `null` if no votes exist.
2. **Quantity Immutability via PATCH**: `PATCH /snacks/{id}` explicitly forbids editing `quantity` (`extra="forbid"`). Stock levels can only change through audited `POST /consume` and `POST /restock` endpoints.
3. **Audit Trail Immutability**: Activity records cannot be edited or deleted via the API.

---

## Design Decisions & Trade-Offs

### 1. JWT in `localStorage` vs. `HttpOnly` Cookies
- **Decision**: Stored JWT in `localStorage` and sent via `Authorization: Bearer <token>`.
- **Trade-off**: Eliminates Cross-Site Request Forgery (CSRF) vulnerabilities entirely since browsers do not attach `localStorage` tokens to cross-origin requests. However, tokens can be accessed if an XSS vulnerability exists.
- **Mitigation**: React automatically escapes JSX expressions, Pydantic sanitizes all inputs, and server-side authorization verifies user identity on every request.

### 2. Synchronous SQLAlchemy 2.0 with Connection Pooling vs. Async
- **Decision**: Used sync SQLAlchemy with `psycopg2` and a tuned connection pool (`pool_size=20, max_overflow=10, pool_pre_ping=True`).
- **Trade-off**: Async Python yields higher theoretical concurrent socket throughput on I/O-bound micro-benchmarks, but sync SQLAlchemy offers battle-tested transaction semantics, simpler connection isolation, and lower debugging complexity.

### 3. Direct PostgreSQL Queries (No Redis Caching)
- **Decision**: Snack status, vote counts, and summary counts are computed directly in SQL using joins and grouping.
- **Trade-off**: Ensures zero stale inventory state across clients. At moderate office scale (dozens of concurrent requests), PostgreSQL handles queries in sub-milliseconds.

---

## What Breaks First at 100x Scale & Mitigations

| Bottleneck at 100x Scale | Failure Mode | Mitigation Strategy |
|---|---|---|
| **Hot-Row Lock Contention** | Hundreds of users consuming the same popular snack causes connection queue pileups waiting for row locks. | 1. Implement queue-based consumption (RabbitMQ/Celery) or Redis atomic decrements (`DECRBY`) with asynchronous DB write-backs.<br>2. Add short-circuit inventory checks in Redis. |
| **PostgreSQL Connection Starvation** | Opening thousands of direct connections exhausts database RAM and file descriptors. | 1. Deploy PgBouncer in transaction pooling mode.<br>2. Utilize Supabase's managed connection pooler with dedicated pool allocations. |
| **Summary & Vote Count Aggregations** | Executing grouped queries and table joins for every catalog view slows down under millions of vote rows. | 1. Cache `/snacks/summary` in Redis with cache invalidation upon vote/consume events.<br>2. Maintain denormalized counter columns updated via trigger or event bus. |

---

## Future Bonus Items
- [ ] **Docker & Docker Compose**: Single `docker-compose up` orchestrating FastAPI, React Nginx frontend, and PostgreSQL.
- [ ] **Idempotency Keys**: Support `Idempotency-Key: <UUID>` header on `POST /consume` to protect against network retry duplication.
- [ ] **Activity Log Page**: Dedicated audit dashboard displaying historical who-ate-what logs with user filters.
- [ ] **Real-Time Inventory (SSE / WebSockets)**: Push instant stock changes and vote updates to all connected browser clients.
