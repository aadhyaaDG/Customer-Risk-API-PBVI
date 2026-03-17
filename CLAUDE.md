# CLAUDE.md
## Customer Risk API — Build Reference
**Architecture:** A — Single FastAPI Container + Postgres  
**Source:** ARCHITECTURE.md v1.0 · INVARIANTS.md v1.0 · EXECUTION_PLAN.md v1.0

---

## What You Are Building

A read-only HTTP API that looks up customer risk profiles from a Postgres
database. One FastAPI container serves both the API and a static HTML UI.
One Postgres container holds the data. Two containers total.

```
Browser → FastAPI (port 8000) → Postgres (internal only)
            ├── GET /              static UI
            ├── GET /health        no auth
            └── GET /customer/{id} requires X-API-Key header
```

---

## Constraints That Cannot Be Violated

| # | Rule |
|---|---|
| I-01 | No INSERT, UPDATE, DELETE, or DDL at runtime. DB user holds SELECT only. |
| I-02 | Return data exactly as fetched. No transformation, re-ordering, or normalisation. |
| I-03 | `X-API-Key` header required on every `/customer/` request. Enforced at router level. |
| I-04 | Unauthenticated requests receive 401 before any DB interaction. No data leaks. |
| I-05 | API key never in logs, URLs, or any response body. FastAPI must not log the header. |
| I-06 | Every response is JSON with `Content-Type: application/json`. No exceptions. |
| I-07 | Unknown customer → 404. Malformed customer_id → 400. Distinct cases. |
| I-08 | Postgres publishes no ports to the host. Reachable only within Compose network. |
| I-09 | Seed data must contain at least one LOW, one MEDIUM, one HIGH record at all times. |

---

## Stack and Versions

| Component | Decision |
|---|---|
| Python | 3.11-slim |
| FastAPI | 0.111.0 |
| Uvicorn | 0.29.0 |
| psycopg2 | 2.9.9-binary — no ORM |
| Postgres | 15 |
| Auth | `hmac.compare_digest` — no timing attacks |

---

## Key Implementation Rules

- **Auth dependency** — apply `Depends(verify_api_key)` at the router level, not per-route.
  A route without it is silently unauthenticated and immediately port-exposed.
- **SQL** — parameterised queries only (`%s` placeholders). No f-strings or concatenation into SQL.
- **Errors** — global `@app.exception_handler(Exception)` must return `{"detail": "Internal server error"}`.
  Never pass `str(e)` or any exception detail into a response. Do not log request headers.
- **DB connection** — `try/finally` on every query path. Wrap psycopg2 exceptions in
  `RuntimeError("Database connection failed")` before they reach the caller.
- **Startup** — `pg_isready` polling loop before `uvicorn` starts. Must have a finite retry
  count and exit non-zero on exhaustion. Do not loop indefinitely.
- **Secrets** — `.env` injected at runtime only. Never `COPY` it in a Dockerfile.
  `.env` is in `.gitignore`. `.env.example` is committed with placeholder values.

---

## File Layout

```
customer-risk-api/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── db/
│   └── init.sql          # schema + 15 seed records (5 LOW, 5 MEDIUM, 5 HIGH)
└── api/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py            # routes, auth dependency, exception handler
    ├── db.py              # get_connection() only — no query logic
    └── static/
        └── index.html     # vanilla HTML/JS — no frameworks
```

---

## Environment Variables

| Variable | Used By | Example |
|---|---|---|
| `API_KEY` | FastAPI | `change-me-before-use` |
| `POSTGRES_USER` | Postgres, FastAPI | `riskuser` |
| `POSTGRES_PASSWORD` | Postgres, FastAPI | `changeme` |
| `POSTGRES_DB` | Postgres, FastAPI | `riskdb` |
| `POSTGRES_HOST` | FastAPI | `postgres` |
| `POSTGRES_PORT` | FastAPI | `5432` |

---

## Data Model

**Table:** `customers`

| Column | Type | Notes |
|---|---|---|
| `customer_id` | `VARCHAR(20) PK` | Pattern `[A-Za-z0-9_-]{1,20}` |
| `risk_tier` | `TEXT NOT NULL` | CHECK: `LOW`, `MEDIUM`, or `HIGH` only |
| `risk_factors` | `TEXT[] NOT NULL` | May be empty array. Never null. Never omitted from response. |

---

## Build Order

`S1` Infrastructure → `S2` FastAPI + DB layer → `S3` Auth + error handling → `S4` UI + static serving → `S5` Verification + README

Do not begin S3 until S2 integration check passes. Do not begin S4 until S3.T3 (write-path audit) is complete.