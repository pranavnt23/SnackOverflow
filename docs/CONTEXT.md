# Snack Overflow - System Context & Architecture Rules

## 1. Project Overview
"Snack Overflow" is an office pantry tracker built as a production-minded full-stack application.
- **Frontend**: React + TypeScript (Vite)
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL hosted on Supabase (accessed strictly as standard PostgreSQL via SQLAlchemy 2.0; no Supabase SDKs, client libraries, or Supabase Auth are used)

---

## 2. Core Architectural & Domain Rules

### Rule 1: Snack Status is Derived, Never Stored
Snack status is dynamically calculated from `quantity` and `low_stock_threshold`. It is **never** stored as a column in the database to prevent state drift and synchronization bugs.
- `stocked`: `quantity > low_stock_threshold`
- `running_low`: `1 <= quantity <= low_stock_threshold`
- `gone`: `quantity == 0`

### Rule 2: Stock Consumption Must Be Atomic at the DB Level
- Stock consumption must execute as a single atomic conditional SQL UPDATE statement (e.g., `UPDATE snacks SET quantity = quantity - :amount WHERE id = :id AND quantity >= :amount RETURNING ...`).
- Never perform in-memory quantity checks (e.g., read quantity -> check if >= amount in Python -> update quantity), which are susceptible to race conditions under concurrent requests.
- If zero rows are updated, raise an `OUT_OF_STOCK` / `INSUFFICIENT_STOCK` error.

### Rule 3: Exactly One Vote Per User Per Snack (DB Enforced)
- Each user can vote for a snack at most once.
- Enforced at the database level using a **Composite Primary Key** on the `votes` table: `(user_id, snack_id)`.
- Foreign keys use `ON DELETE CASCADE` so deleting a user or snack cleanly cascades to their votes without leaving orphans.

### Rule 4: Atomic Activity Audit Logging in the Same Transaction
- Every stock change (`consumed` or `restocked`) **must** insert an `activity` record within the **exact same database transaction** as the stock update.
- If either fails, the transaction is rolled back completely.
- `snack_name` is snapshotted as a string column in `activities` alongside nullable `snack_id` (`ON DELETE SET NULL`), ensuring historical audit logs remain intact even if a snack is deleted.
- Amount in `activities` must be strictly positive (`CHECK (amount > 0)`).

### Rule 5: Uniform API Error Response Format
All API error responses must adhere strictly to the standardized envelope:
```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable explanation of the error."
  }
}
```
Standard error codes include:
- `VALIDATION_ERROR`: Input payload failed schema validation
- `NOT_FOUND`: Resource does not exist
- `UNAUTHORIZED`: Missing or invalid credentials
- `FORBIDDEN`: Insufficient role/permissions
- `CONFLICT`: Unique constraint violation or duplicate resource
- `INSUFFICIENT_STOCK`: Requested consumption exceeds current stock
- `INTERNAL_SERVER_ERROR`: Unhandled exception or unexpected server failure

### Rule 6: Server-Side Authorization & Secret Management
- Authorization and roles (`admin`, `member`) are strictly validated on the server for all protected routes using JWT tokens signed with `JWT_SECRET`.
- Never trust client-reported roles or IDs.
- Zero secrets committed to the repository: all secrets (`DATABASE_URL`, `JWT_SECRET`, etc.) are loaded from environment variables via `pydantic-settings`.

---

## 3. Database Schema Reference

### `users`
- `id` (INTEGER, PK, autoincrement)
- `name` (VARCHAR(100), NOT NULL)
- `email` (VARCHAR(255), UNIQUE, INDEX, NOT NULL)
- `password_hash` (VARCHAR(255), NOT NULL)
- `role` (ENUM: `'admin'`, `'member'`, NOT NULL, DEFAULT `'member'`)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)

### `snacks`
- `id` (INTEGER, PK, autoincrement)
- `name` (VARCHAR(150), UNIQUE, INDEX, NOT NULL)
- `category` (ENUM: `'sweet'`, `'savoury'`, `'drink'`, `'healthy-ish'`, INDEX, NOT NULL)
- `quantity` (INTEGER, INDEX, NOT NULL, DEFAULT 0)
- `low_stock_threshold` (INTEGER, NOT NULL, DEFAULT 5)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- `updated_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- **Constraints**:
  - `CHECK (quantity >= 0)`
  - `CHECK (low_stock_threshold >= 0)`

### `votes`
- `user_id` (INTEGER, FK -> `users.id` ON DELETE CASCADE, NOT NULL)
- `snack_id` (INTEGER, FK -> `snacks.id` ON DELETE CASCADE, NOT NULL, INDEX)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- **Primary Key**: `(user_id, snack_id)` (Composite PK)

### `activities`
- `id` (INTEGER, PK, autoincrement)
- `user_id` (INTEGER, FK -> `users.id` ON DELETE SET NULL, NULLABLE)
- `snack_id` (INTEGER, FK -> `snacks.id` ON DELETE SET NULL, NULLABLE)
- `snack_name` (VARCHAR(150), NOT NULL) -- snapshot
- `action` (ENUM: `'restocked'`, `'consumed'`, NOT NULL)
- `amount` (INTEGER, NOT NULL)
- `quantity_after` (INTEGER, NOT NULL)
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT `now()`)
- **Constraints**:
  - `CHECK (amount > 0)`

---

## 4. Performance & Database Pool Tuning
- SQLAlchemy 2.0 sync engine with connection pooling:
  - `pool_size >= 15` (default: 20)
  - `max_overflow = 10`
  - `pool_pre_ping = True` (protects against stale/dropped Supabase connections)
- Indexes defined on high-cardinality and filter fields:
  - `snacks.name`
  - `snacks.category`
  - `snacks.quantity`
  - `votes.snack_id`
