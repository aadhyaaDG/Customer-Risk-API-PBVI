# EXECUTION_PLAN.md — Customer Risk API
**Version:** 1.0  
**Status:** Phase 3 Complete — Awaiting Phase 4 Design Gate  
**Source:** ARCHITECTURE.md v1.0 · INVARIANTS.md v1.0

---

## Resolved Decisions (Open Questions Closed for Build)

Before this plan can proceed to Phase 4, the following open questions from ARCHITECTURE.md are resolved with concrete decisions for the build:

| Question | Decision |
|---|---|
| `customer_id` format | Alphanumeric string, max 20 characters, pattern `[A-Za-z0-9-_]+`. Stored as `VARCHAR(20)`. |
| Risk factor schema | Plain string array stored as Postgres `TEXT[]`. Returned as `["factor_a", "factor_b"]` JSON array. |
| Environment variable names | `API_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` |
| Service port | `8000` (configurable via Docker Compose, not via `.env`) |
| Seed data volume | 15 records: 5 LOW, 5 MEDIUM, 5 HIGH — each with 1–4 distinct risk factor strings |
| Health endpoint | `GET /health` — returns `{"status": "ok"}`, exempt from API key check. Used by Compose health check. |

---

## Session Overview

| Session | Description | Tasks | Est. Duration |
|---|---|---|---|
| S1 | Infrastructure: Docker Compose, Postgres, schema, seed data | T1–T4 | ~2h 10m |
| S2 | FastAPI application: core app, DB layer, customer endpoint | T1–T4 | ~2h 20m |
| S3 | Authentication, error handling, security | T1–T3 | ~1h 50m |
| S4 | UI and integration wiring | T1–T3 | ~1h 40m |
| S5 | System verification and README | T1–T2 | ~1h 00m |

**Total estimated build time across all sessions:** ~9 hours  
No single session exceeds 4 hours. No split required.

---

## Session 1 — Infrastructure: Docker Compose, Postgres, Schema, Seed Data

**Session goal:** A running Postgres container with correct schema and seed data, orchestrated by Docker Compose with a health check. The API container slot is defined but contains a placeholder. `docker compose up` completes without error and Postgres is queryable.

**Estimated duration:** ~2h 10m  
(T1: 28m · T2: 33m · T3: 40m · T4: 28m)

**Integration check (run after all tasks verified):**
```bash
docker compose up -d
docker compose ps
# Expect: postgres container status = healthy
docker exec -it <postgres_container> psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier ORDER BY risk_tier;"
# Expect: HIGH=5, LOW=5, MEDIUM=5
docker compose down -v
```

---

### S1.T1 — Project scaffold and `.env.example`

**Description:**  
Create the top-level directory structure and `.env.example` file. No application logic. Output is a repository skeleton with all required directories and a documented environment variable template.

**Inputs:** None  
**Outputs:** `docker-compose.yml` (stub), `api/`, `db/`, `.env.example`, `.gitignore`

**CC Prompt:**
```
Create the project scaffold for a Customer Risk API. 

Directory structure required:
  customer-risk-api/
    docker-compose.yml       # stub — define services: postgres, api (no build yet)
    .env.example             # document all required variables
    .gitignore               # exclude .env, __pycache__, *.pyc, .DS_Store
    api/                     # empty directory — FastAPI app will go here
    db/                      # empty directory — SQL init scripts will go here

.env.example must contain exactly these variables with placeholder values:
  API_KEY=change-me-before-use
  POSTGRES_USER=riskuser
  POSTGRES_PASSWORD=changeme
  POSTGRES_DB=riskdb
  POSTGRES_HOST=postgres
  POSTGRES_PORT=5432

docker-compose.yml stub: define a `postgres` service using image postgres:15 and
an `api` service with image placeholder "customer-risk-api:latest" (no build block yet).
Both services read from the .env file. No volumes, no health checks yet — this is a scaffold only.

Do not create any Python files, SQL files, or application code.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | All required files and directories exist | `ls` shows `docker-compose.yml`, `.env.example`, `.gitignore`, `api/`, `db/` |
| TC2 | `.env.example` contains all six variable names | `grep -c "=" .env.example` returns 6 |
| TC3 | `.env` is listed in `.gitignore` | `grep "^\.env$" .gitignore` returns a match |
| TC4 | `docker-compose.yml` defines both `postgres` and `api` services | `grep -c "^\s\{2\}[a-z]" docker-compose.yml` returns at least 2 |

**Verification command:**
```bash
ls customer-risk-api/ && \
grep -c "=" customer-risk-api/.env.example && \
grep "^\.env$" customer-risk-api/.gitignore && \
cat customer-risk-api/docker-compose.yml
```

**Invariant flag:** None

---

### S1.T2 — Docker Compose: Postgres service with health check

**Description:**  
Complete the `postgres` service definition in `docker-compose.yml`. Add a named volume, environment variable wiring from `.env`, and a `pg_isready` health check. The API service stub remains. Output: Postgres starts cleanly and reaches `healthy` status.

**Inputs:** `docker-compose.yml` stub, `.env` (created from `.env.example`)  
**Outputs:** Updated `docker-compose.yml` with complete `postgres` service definition

**CC Prompt:**
```
Update docker-compose.yml to complete the postgres service definition.

Requirements:
- Use image: postgres:15
- Wire environment variables from .env: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- Mount a named volume `pgdata` to /var/lib/postgresql/data
- Add a healthcheck:
    test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s
- Define the named volume `pgdata` in the top-level volumes section

The api service remains as a stub (image placeholder only). Do not add depends_on yet — that comes in a later task.

Do not create any other files.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | `docker compose up -d postgres` starts without error | Exit code 0 |
| TC2 | Postgres container reaches `healthy` within 60s | `docker compose ps` shows `(healthy)` |
| TC3 | Can connect and run a query | `docker exec <container> psql -U riskuser -d riskdb -c "SELECT 1;"` returns `1` |
| TC4 | Named volume `pgdata` is created | `docker volume ls` shows `customer-risk-api_pgdata` |

**Verification command:**
```bash
cd customer-risk-api && \
cp .env.example .env && \
docker compose up -d postgres && \
sleep 15 && \
docker compose ps postgres && \
docker compose exec postgres psql -U riskuser -d riskdb -c "SELECT 1;"
```

**Invariant flag:** Touches **INV-09** (database must be reachable before API serves requests — health check is the enforcement mechanism).  
**Code review:** Confirm `interval`, `retries`, and `start_period` values are sufficient for Postgres to fully initialise before reporting healthy. Confirm `pg_isready` checks the correct user and database (not just the server process).

---

### S1.T3 — Database schema and seed data init script

**Description:**  
Create `db/init.sql` — the SQL init script that Postgres runs automatically on first container start. Creates the `customers` table and inserts 15 seed records (5 LOW, 5 MEDIUM, 5 HIGH). No application code changes.

**Inputs:** Schema decisions from this plan (customer_id VARCHAR(20), risk_tier TEXT, risk_factors TEXT[])  
**Outputs:** `db/init.sql`

**CC Prompt:**
```
Create db/init.sql — a Postgres initialisation script that will be mounted into
/docker-entrypoint-initdb.d/ and run automatically on first container start.

Schema:
  CREATE TABLE IF NOT EXISTS customers (
    customer_id  VARCHAR(20) PRIMARY KEY,
    risk_tier    TEXT        NOT NULL CHECK (risk_tier IN ('LOW', 'MEDIUM', 'HIGH')),
    risk_factors TEXT[]      NOT NULL
  );

Seed data — insert exactly 15 records:
  - 5 with risk_tier = 'LOW'. Use customer_ids: CUST-001 through CUST-005.
    Risk factors: plausible low-risk labels (e.g. 'stable_income', 'long_account_tenure',
    'no_missed_payments'). Vary the number of factors (1–3 per customer).

  - 5 with risk_tier = 'MEDIUM'. Use customer_ids: CUST-006 through CUST-010.
    Risk factors: plausible medium-risk labels (e.g. 'recent_address_change',
    'moderate_credit_utilisation', 'occasional_late_payment'). Vary the number of factors (2–3).

  - 5 with risk_tier = 'HIGH'. Use customer_ids: CUST-011 through CUST-015.
    Risk factors: plausible high-risk labels (e.g. 'multiple_missed_payments',
    'high_transaction_volume', 'sanctions_watchlist_match', 'identity_verification_failed').
    Vary the number of factors (2–4).

Use INSERT INTO ... VALUES (...) syntax. Use Postgres array literal syntax for risk_factors:
  ARRAY['factor_a', 'factor_b']

Do not create any other files.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | Script runs without SQL errors | `psql` exit code 0 |
| TC2 | Table exists with correct columns | `\d customers` shows customer_id, risk_tier, risk_factors |
| TC3 | Exactly 15 rows inserted | `SELECT COUNT(*) FROM customers;` returns 15 |
| TC4 | All three tiers present with count 5 each | `SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier;` returns LOW=5, MEDIUM=5, HIGH=5 |
| TC5 | risk_factors is a non-empty array for every row | `SELECT COUNT(*) FROM customers WHERE risk_factors = '{}';` returns 0 |
| TC6 | CHECK constraint rejects invalid tier | `INSERT INTO customers VALUES ('X', 'INVALID', '{}');` raises constraint violation |

**Verification command:**
```bash
docker compose down -v && docker compose up -d postgres && sleep 15 && \
docker compose exec postgres psql -U riskuser -d riskdb -c \
  "SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier ORDER BY risk_tier;" && \
docker compose exec postgres psql -U riskuser -d riskdb -c \
  "SELECT customer_id, risk_tier, risk_factors FROM customers ORDER BY customer_id LIMIT 5;"
```

**Invariant flag:** Touches **INV-08** (all three tiers must exist after initialisation) and **INV-01** (schema defines read-only data; no write paths from application — confirmed here that init.sql is the only write path).  
**Code review:** Confirm `CHECK (risk_tier IN ('LOW', 'MEDIUM', 'HIGH'))` is present. Confirm `NOT NULL` on both `risk_tier` and `risk_factors`. Confirm all 15 rows cover all three tiers. Confirm `risk_factors` uses `TEXT[]` not `JSONB` (TEXT[] is what the plan specifies).

---

### S1.T4 — Mount init script into Docker Compose

**Description:**  
Update `docker-compose.yml` to mount `db/init.sql` into the Postgres container's `/docker-entrypoint-initdb.d/` directory. Tear down, remove volumes, and restart to confirm auto-seeding works end to end.

**Inputs:** `docker-compose.yml`, `db/init.sql`  
**Outputs:** Updated `docker-compose.yml` with volume mount for init script

**CC Prompt:**
```
Update the postgres service in docker-compose.yml to mount the init script.

Add a bind mount to the postgres service volumes section:
  - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro

The `:ro` flag is required — the container should not write to the init script.

The named volume pgdata mount remains unchanged.

Do not change any other service definitions or any other files.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | Fresh stack start seeds the database | After `docker compose down -v && docker compose up -d postgres`, all 15 rows are present |
| TC2 | Init script is mounted read-only | Running `docker compose exec postgres touch /docker-entrypoint-initdb.d/init.sql` fails with permission error |
| TC3 | Second start with existing volume skips init script (expected behaviour) | After `docker compose restart postgres` (without `-v`), data is still present and count is still 15 |

**Verification command:**
```bash
docker compose down -v && \
docker compose up -d postgres && \
sleep 20 && \
docker compose exec postgres psql -U riskuser -d riskdb -c \
  "SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier ORDER BY risk_tier;"
# Expect: HIGH 5 | LOW 5 | MEDIUM 5
```

**Invariant flag:** Touches **INV-08** (seed data present after initialisation).  
**Code review:** Confirm `:ro` flag is present on the bind mount. Confirm `pgdata` named volume mount is still present and unchanged.

---

## Session 2 — FastAPI Application: Core App, DB Layer, Customer Endpoint

**Session goal:** A running FastAPI container that connects to Postgres and returns correct JSON for a valid customer_id. Authentication is not enforced yet (added in Session 3). The `/customer/{customer_id}` endpoint returns correct data and a correct 404 for unknown IDs.

**Estimated duration:** ~2h 20m  
(T1: 28m · T2: 33m · T3: 40m · T4: 40m)

**Integration check (run after all tasks verified):**
```bash
docker compose up -d
sleep 20
curl -s http://localhost:8000/health | python3 -m json.tool
# Expect: {"status": "ok"}
curl -s http://localhost:8000/customer/CUST-001 | python3 -m json.tool
# Expect: customer_id, risk_tier=LOW, risk_factors array
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/NOTEXIST
# Expect: 404
docker compose down -v
```

---

### S2.T1 — FastAPI project structure and dependencies

**Description:**  
Create the FastAPI application file structure and `requirements.txt`. No application logic — skeleton only. Output is a valid Python package structure that can be installed and imported.

**Inputs:** None  
**Outputs:** `api/main.py` (skeleton), `api/requirements.txt`, `api/Dockerfile`

**CC Prompt:**
```
Create the FastAPI application skeleton inside the api/ directory.

Files to create:

1. api/requirements.txt — exact versions required:
   fastapi==0.111.0
   uvicorn[standard]==0.29.0
   psycopg2-binary==2.9.9

2. api/Dockerfile:
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

3. api/main.py — skeleton only:
   - Import FastAPI, create app instance
   - Add a single placeholder route: GET /health returns {"status": "ok"}
   - No database connection, no other routes

Do not add authentication, database logic, or the customer endpoint yet.
Do not modify docker-compose.yml in this task.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | `requirements.txt` contains all three dependencies | `grep -c "==" api/requirements.txt` returns 3 |
| TC2 | `Dockerfile` uses `python:3.11-slim` | `grep "FROM python:3.11-slim" api/Dockerfile` matches |
| TC3 | `main.py` is syntactically valid Python | `python3 -c "import ast; ast.parse(open('api/main.py').read())"` exits 0 |
| TC4 | FastAPI app instance is created | `grep "FastAPI()" api/main.py` matches |

**Verification command:**
```bash
python3 -c "import ast; ast.parse(open('customer-risk-api/api/main.py').read()); print('syntax OK')" && \
grep -c "==" customer-risk-api/api/requirements.txt && \
grep "FROM python:3.11-slim" customer-risk-api/api/Dockerfile
```

**Invariant flag:** None

---

### S2.T2 — Docker Compose: wire API service with build and depends_on

**Description:**  
Update `docker-compose.yml` to replace the API stub with a real build definition. Add `depends_on` with `condition: service_healthy` pointing to the Postgres service. Wire all environment variables. Expose port 8000.

**Inputs:** `docker-compose.yml`, `api/Dockerfile`  
**Outputs:** Updated `docker-compose.yml` with complete `api` service definition

**CC Prompt:**
```
Update docker-compose.yml to complete the api service definition.

The api service must:
- Build from ./api using build: context: ./api
- Expose port 8000:8000
- Wire these environment variables from .env:
    API_KEY, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
- Declare depends_on:
    postgres:
      condition: service_healthy
- Restart policy: restart: on-failure

The postgres service definition must not change.

Do not modify any files other than docker-compose.yml.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | `docker compose up -d` starts both containers | Both `postgres` and `api` containers running |
| TC2 | API container waits for Postgres healthy before starting | `docker compose logs api` shows no connection refused errors on startup |
| TC3 | `/health` returns 200 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` returns 200 |
| TC4 | Port 8000 is accessible from host | `curl http://localhost:8000/health` responds |

**Verification command:**
```bash
cd customer-risk-api && docker compose up -d && sleep 25 && \
docker compose ps && \
curl -s http://localhost:8000/health
# Expect: {"status":"ok"}
```

**Invariant flag:** Touches **INV-09** (API must not accept requests until DB is ready — enforced by `depends_on: condition: service_healthy`).  
**Code review:** Confirm `condition: service_healthy` (not just `depends_on: postgres`). Confirm it references the postgres service name exactly. Confirm restart policy is `on-failure` not `always` (always can mask startup failures).

---

### S2.T3 — Database connection module

**Description:**  
Create `api/db.py` — a module that provides a single function `get_connection()` returning a psycopg2 connection using environment variables. No query logic here. Include connection error handling that raises a clean exception (not a raw psycopg2 error).

**Inputs:** Environment variables: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`  
**Outputs:** `api/db.py`

**CC Prompt:**
```
Create api/db.py — a database connection module for the Customer Risk API.

Requirements:
- Provide a single function: get_connection()
- get_connection() reads connection parameters from environment variables:
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
- Uses psycopg2.connect() with those parameters. No connection pooling.
- If the connection fails, raise a RuntimeError with the message "Database connection failed"
  — do not propagate the raw psycopg2 exception to the caller.
- Import os for environment variable access. Import psycopg2.
- Do not log the connection string, password, or any credential in any log output.

Do not add any query functions. Do not modify main.py or any other file.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | Module is syntactically valid | `python3 -c "import ast; ast.parse(open('api/db.py').read())"` exits 0 |
| TC2 | `get_connection()` function is defined | `grep "def get_connection" api/db.py` matches |
| TC3 | No credential values are in log statements | `grep -i "password\|api_key\|secret" api/db.py` returns no matches on log/print lines |
| TC4 | RuntimeError is raised on failure (not psycopg2 error) | Code review confirms `except` block raises `RuntimeError("Database connection failed")` |
| TC5 | psycopg2 is imported | `grep "import psycopg2" api/db.py` matches |

**Verification command:**
```bash
python3 -c "import ast; ast.parse(open('customer-risk-api/api/db.py').read()); print('syntax OK')" && \
grep "def get_connection" customer-risk-api/api/db.py && \
grep "RuntimeError" customer-risk-api/api/db.py
```

**Invariant flag:** Touches **INV-05** (API key must not appear in logs — confirms no credentials are logged) and **INV-07** (error responses must not expose internal detail — RuntimeError wrapping prevents raw psycopg2 errors from propagating).  
**Code review:** Confirm the `except` block catches `psycopg2.OperationalError` (or broad `Exception`) and raises `RuntimeError("Database connection failed")` — no re-raise of the original. Confirm no `print()` or `logging` calls include the connection string or any variable that could contain a password.

---

### S2.T4 — Customer lookup endpoint

**Description:**  
Add `GET /customer/{customer_id}` to `main.py`. Uses `db.py` to query the customers table. Returns structured JSON on success, HTTP 404 with a clean message when the customer is not found. Uses parameterised psycopg2 query. customer_id is validated: alphanumeric + dash + underscore, max 20 chars. No authentication yet.

**Inputs:** `api/main.py` (skeleton), `api/db.py`  
**Outputs:** Updated `api/main.py` with customer endpoint

**CC Prompt:**
```
Add the customer lookup endpoint to api/main.py.

Endpoint: GET /customer/{customer_id}

Input validation on customer_id path parameter:
- Must match pattern ^[A-Za-z0-9_-]{1,20}$
- If it does not match, return HTTP 422 with message "Invalid customer_id format"

Database query (using db.get_connection()):
- SELECT customer_id, risk_tier, risk_factors FROM customers WHERE customer_id = %s
- customer_id value is passed as a parameterised argument — NEVER via string formatting or f-strings
- If no row is returned, raise HTTPException(status_code=404, detail="Customer not found")
- Close the connection after use (use try/finally)

Success response — HTTP 200, JSON:
{
  "customer_id": "<value from db>",
  "risk_tier": "<value from db>",
  "risk_factors": ["<factor1>", "<factor2>"]
}

Error handling:
- Database errors: catch Exception, log internally (do not log the query or customer_id value),
  raise HTTPException(status_code=500, detail="Internal server error")
- The raw exception message must never appear in the response body

Do not add authentication in this task. Do not modify db.py or any other files.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | Valid customer_id that exists (e.g. CUST-001) | HTTP 200, JSON with correct customer_id, risk_tier, non-empty risk_factors array |
| TC2 | Valid customer_id for a HIGH tier customer (e.g. CUST-011) | HTTP 200, risk_tier = "HIGH" |
| TC3 | Valid customer_id that does not exist | HTTP 404, `{"detail": "Customer not found"}` |
| TC4 | customer_id with SQL injection attempt (e.g. `CUST-001'--`) | HTTP 422 (rejected by validation pattern before reaching DB) |
| TC5 | customer_id exceeding 20 characters | HTTP 422 |
| TC6 | customer_id containing spaces or special chars | HTTP 422 |
| TC7 | Risk factors array is returned as a JSON array (not a string) | `risk_factors` in response is `[]` type, not a string |
| TC8 | Response contains exactly three keys: customer_id, risk_tier, risk_factors | No extra fields |

**Verification command:**
```bash
# Rebuild and restart
docker compose up -d --build && sleep 25 && \
curl -s http://localhost:8000/customer/CUST-001 | python3 -m json.tool && \
curl -s http://localhost:8000/customer/CUST-011 | python3 -m json.tool && \
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/NOTEXIST && \
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/customer/CUST-001'--"
```

**Invariant flag:** Touches **INV-02** (data returned matches DB exactly), **INV-03** (parameterised query — only correct row returned), **INV-06** (no string interpolation into SQL), **INV-07** (no internal errors in response).  
**Code review:**  
- Confirm the query uses `%s` placeholder and tuple argument, not f-string or concatenation.  
- Confirm `try/finally` closes the connection on every code path.  
- Confirm the 500 handler's `detail` is the literal string `"Internal server error"` — not `str(e)` or any variable.  
- Confirm `risk_factors` is returned as a Python list (psycopg2 deserialises `TEXT[]` to a Python list automatically — confirm no manual serialisation).  
- Confirm no default values are substituted: if the DB returns NULL for any field, it should surface as an error, not a silent default.

---

## Session 3 — Authentication, Error Handling, Security

**Session goal:** The API enforces API key authentication on all API routes. Unauthenticated requests receive 401. The `/health` endpoint and the UI route remain exempt. Error responses are clean — no stack traces, no DB detail.

**Estimated duration:** ~1h 50m  
(T1: 40m · T2: 33m · T3: 33m)

**Integration check (run after all tasks verified):**
```bash
docker compose up -d --build && sleep 25
# No key — expect 401
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/CUST-001
# Wrong key — expect 401
curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: wrong-key" http://localhost:8000/customer/CUST-001
# Correct key — expect 200
curl -s -H "X-API-Key: $API_KEY" http://localhost:8000/customer/CUST-001 | python3 -m json.tool
# Health — no key needed — expect 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
docker compose down -v
```

---

### S3.T1 — API key authentication middleware

**Description:**  
Add API key authentication to FastAPI using a dependency. The key is read from the `API_KEY` environment variable at startup. All API routes require the `X-API-Key` header. `/health` is exempt. Returns HTTP 401 on missing or incorrect key. The key must never appear in any response or log.

**Inputs:** `api/main.py`  
**Outputs:** Updated `api/main.py` with authentication dependency

**CC Prompt:**
```
Add API key authentication to api/main.py.

Implementation requirements:
- On startup, read API_KEY from environment using os.environ. If the variable is not set,
  raise a RuntimeError at startup (fail fast — do not start without a key).
- Implement a FastAPI dependency function `verify_api_key(x_api_key: str = Header(None))`:
  - If x_api_key is None or does not match the API_KEY value, raise HTTPException(status_code=401,
    detail="Unauthorized")
  - Use a constant-time comparison (use hmac.compare_digest) to prevent timing attacks
  - Do not log the supplied key value under any circumstances
- Apply the dependency to the /customer/{customer_id} route using `dependencies=[Depends(verify_api_key)]`
- The /health route must NOT have this dependency — it must remain publicly accessible
- The 401 response body must be exactly: {"detail": "Unauthorized"}
  — do not include the expected key, the supplied key, or any other detail

Do not modify db.py. Do not modify the customer endpoint logic (only add the dependency).
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | Request to `/customer/{id}` with no `X-API-Key` header | HTTP 401, `{"detail": "Unauthorized"}` |
| TC2 | Request with wrong key value | HTTP 401, `{"detail": "Unauthorized"}` |
| TC3 | Request with correct key | HTTP 200 with customer data |
| TC4 | Request to `/health` with no key | HTTP 200, `{"status": "ok"}` |
| TC5 | Request to `/health` with wrong key | HTTP 200 (health is exempt from auth) |
| TC6 | 401 response body does not contain the API key value | Response body parsed: no key value present |
| TC7 | Empty string as key value | HTTP 401 |
| TC8 | API_KEY not set in environment | Application fails at startup (not silently) |

**Verification command:**
```bash
docker compose up -d --build && sleep 25 && \
echo "--- No key (expect 401):" && \
curl -s -w "\nHTTP %{http_code}\n" http://localhost:8000/customer/CUST-001 && \
echo "--- Wrong key (expect 401):" && \
curl -s -w "\nHTTP %{http_code}\n" -H "X-API-Key: badkey" http://localhost:8000/customer/CUST-001 && \
echo "--- Correct key (expect 200):" && \
curl -s -H "X-API-Key: $(grep API_KEY .env | cut -d= -f2)" http://localhost:8000/customer/CUST-001 | python3 -m json.tool && \
echo "--- Health no key (expect 200):" && \
curl -s -w "\nHTTP %{http_code}\n" http://localhost:8000/health
```

**Invariant flag:** Touches **INV-04** (all API routes require valid key), **INV-05** (key must not appear in response or logs).  
**Code review:**  
- Confirm `hmac.compare_digest` is used (not `==`).  
- Confirm dependency is applied to the customer route via `dependencies=[Depends(verify_api_key)]`.  
- Confirm `/health` route definition has no `dependencies` parameter.  
- Confirm startup reads `os.environ["API_KEY"]` (raises `KeyError` if missing) or explicit guard with `RuntimeError`.  
- Confirm no log statement includes `x_api_key` or the `API_KEY` env var value.  
- Confirm 401 detail is the literal `"Unauthorized"` — not `f"Expected {API_KEY}"` or similar.

---

### S3.T2 — Global error handler: suppress internal detail

**Description:**  
Add a global exception handler to FastAPI that catches unhandled exceptions and returns a clean `{"detail": "Internal server error"}` with HTTP 500. Ensures that no stack trace, psycopg2 error text, or Python exception message can leak through an unhandled path.

**Inputs:** `api/main.py`  
**Outputs:** Updated `api/main.py` with global exception handler

**CC Prompt:**
```
Add a global exception handler to api/main.py.

Requirements:
- Register an exception handler for the base Exception class using @app.exception_handler(Exception)
- The handler must return a JSONResponse with status_code=500 and body {"detail": "Internal server error"}
- The handler must NOT include the exception message, traceback, or any system information in the response
- The handler SHOULD log the exception internally using Python's logging module at ERROR level,
  but must not log the request headers (which may contain the API key)
- HTTPException instances are handled by FastAPI's default handler — do not intercept those

Import logging at the top of main.py. Use logging.getLogger(__name__).

Do not modify db.py or any other files.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | Unhandled exception in a route | HTTP 500, body exactly `{"detail": "Internal server error"}` |
| TC2 | HTTPException (e.g. 404) still returns its own detail | 404 with `{"detail": "Customer not found"}` — not overridden |
| TC3 | 401 still returns `{"detail": "Unauthorized"}` | Not overridden by global handler |
| TC4 | Response body for 500 contains no Python traceback text | Manual inspection of response body |

**Verification command:**
```bash
# Add a temporary route to trigger a deliberate unhandled exception, test, then remove
# Verify via code review that the handler is registered and does not re-raise
grep "exception_handler" customer-risk-api/api/main.py && \
grep "Internal server error" customer-risk-api/api/main.py && \
python3 -c "import ast; ast.parse(open('customer-risk-api/api/main.py').read()); print('syntax OK')"
```

**Invariant flag:** Touches **INV-07** (error responses never include DB error detail, stack traces, or internal system information).  
**Code review:**  
- Confirm handler catches `Exception` (not just `psycopg2.Error`).  
- Confirm response body is `JSONResponse(status_code=500, content={"detail": "Internal server error"})`.  
- Confirm the `logging.error(...)` call does not log `request.headers` (which contains the API key).  
- Confirm `HTTPException` is not caught by this handler (FastAPI handles it separately — the global handler should not override it, or should explicitly re-raise `HTTPException`).

---

### S3.T3 — Verify no write paths exist in application code

**Description:**  
This is a verification-only task. No new code is produced. Read every file in `api/` and confirm that no SQL contains INSERT, UPDATE, DELETE, or DDL. Produce a brief written record of what was reviewed. This task is required before Session 4 begins.

**Inputs:** All files in `api/`  
**Outputs:** Written verification entry in VERIFICATION_RECORD.md (no code changes)

**CC Prompt:**
```
This is a code review task — do not write any code.

Read every Python file in the api/ directory. For each file, search for:
  - Any SQL string containing INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE
  - Any use of psycopg2 cursor.execute() with a statement other than SELECT
  - Any import of a library that could perform writes (e.g. SQLAlchemy, an ORM)

Produce a brief report in this format:

File: api/main.py
  SQL statements found: [list any, or "none"]
  Write operations found: [list any, or "none"]

File: api/db.py
  SQL statements found: [list any, or "none"]
  Write operations found: [list any, or "none"]

Conclusion: [PASS if no write paths found | FAIL with specifics if any found]

Do not modify any files.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | No INSERT/UPDATE/DELETE/DDL in any Python file | All files report "none" for write operations |
| TC2 | No ORM library imported | No SQLAlchemy or equivalent import found |
| TC3 | psycopg2 execute() calls use only SELECT | Confirmed by code review |

**Verification command:**
```bash
grep -rni "INSERT\|UPDATE\|DELETE\|DROP\|CREATE\|ALTER\|TRUNCATE" customer-risk-api/api/ --include="*.py"
# Expect: no output (no matches)
grep -rni "sqlalchemy\|orm\|alembic" customer-risk-api/api/ --include="*.py"
# Expect: no output
```

**Invariant flag:** Directly verifies **INV-01** (system never writes to the database).  
**Code review:** This task IS the code review. Confirm grep output is empty for all write-related patterns.

---

## Session 4 — UI and Integration Wiring

**Session goal:** A browser-accessible UI at `http://localhost:8000/` that allows an operations user to enter a customer ID and see the result or a clear error message. The UI reads the API key from a JavaScript constant (populated from an environment variable at build time or served as a config). The full stack works end-to-end from browser to database.

**Estimated duration:** ~1h 40m  
(T1: 33m · T2: 33m · T3: 28m)

**Integration check (run after all tasks verified):**
```bash
docker compose up -d --build && sleep 25
# Open http://localhost:8000/ in a browser
# Enter CUST-001 — expect LOW tier result with risk factors displayed
# Enter CUST-011 — expect HIGH tier result
# Enter NOTEXIST — expect "Customer not found" error message
# Submit empty input — expect client-side validation message
docker compose down -v
```

---

### S4.T1 — Static UI HTML file

**Description:**  
Create `api/static/index.html` — the operations UI. Plain HTML and vanilla JavaScript only. No frameworks. The UI sends a GET request to `/customer/{customer_id}` with the API key in the `X-API-Key` header. Displays the result in a readable format. Handles errors (404, 401, 500) with user-friendly messages. The API key is sourced from a JavaScript constant `API_KEY` defined at the top of the script block.

**Inputs:** API endpoint specification from this plan  
**Outputs:** `api/static/index.html`

**CC Prompt:**
```
Create api/static/index.html — the operations UI for the Customer Risk API.

Requirements:
- Plain HTML5. No frameworks. No external CSS or JS libraries. All CSS inline in a <style> block.
- Layout: A centered card with a title "Customer Risk Lookup", a text input for customer_id,
  a "Look Up" button, and a result area below.
- JavaScript (in a <script> block at the bottom of the body):
  - Define a constant: const API_KEY = "REPLACE_ME";
    (This placeholder will be replaced in a later task — do not attempt to read from .env here)
  - On button click (or Enter key in the input):
    1. Validate: if input is empty, show "Please enter a customer ID" in the result area
    2. Trim whitespace from the input value
    3. Fetch GET /customer/{customer_id} with header X-API-Key: API_KEY
    4. On 200: display customer_id, risk_tier (styled by tier — green for LOW, amber for MEDIUM,
       red for HIGH), and risk_factors as a bulleted list
    5. On 404: display "Customer not found"
    6. On 401: display "Authentication error — check API key configuration"
    7. On any other error: display "An error occurred — please try again"
  - Clear the result area on each new search
- The input field must have id="customer-id-input"
- The result area must have id="result-area"
- The Look Up button must have id="lookup-btn"

Do not modify any Python files. Do not create any other files.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | File is valid HTML | `python3 -c "from html.parser import HTMLParser; p=HTMLParser(); p.feed(open('api/static/index.html').read())"` exits 0 |
| TC2 | Required IDs present | `grep -c 'id="customer-id-input"\|id="result-area"\|id="lookup-btn"' index.html` returns 3 |
| TC3 | API_KEY constant is defined | `grep "const API_KEY" api/static/index.html` matches |
| TC4 | X-API-Key header is set in fetch call | `grep "X-API-Key" api/static/index.html` matches |
| TC5 | No external script/style imports | `grep -i "cdn\|bootstrap\|jquery\|react" api/static/index.html` returns no matches |
| TC6 | Risk tier colour coding is present | `grep -i "LOW\|MEDIUM\|HIGH" api/static/index.html` shows colour references |

**Verification command:**
```bash
python3 -c "
from html.parser import HTMLParser
p = HTMLParser()
p.feed(open('customer-risk-api/api/static/index.html').read())
print('HTML parse OK')
" && \
grep "const API_KEY" customer-risk-api/api/static/index.html && \
grep "X-API-Key" customer-risk-api/api/static/index.html
```

**Invariant flag:** None (UI is client-side only; no server logic in this task).

---

### S4.T2 — Serve static files from FastAPI and inject API key

**Description:**  
Mount the `api/static/` directory in FastAPI using `StaticFiles`. Add a startup event that reads `API_KEY` from the environment and writes a replacement `index.html` with the actual key substituted for `REPLACE_ME`. The UI is served at `GET /` (redirect or direct serve of `index.html`). No separate route needed beyond the static mount.

**Inputs:** `api/main.py`, `api/static/index.html`  
**Outputs:** Updated `api/main.py` with static file serving and key injection

**CC Prompt:**
```
Update api/main.py to serve the static UI and inject the API key into the HTML at startup.

Requirements:

1. Static file serving:
   - Mount api/static/ using FastAPI's StaticFiles at path "/static"
   - Add a route GET / that returns a FileResponse for /app/static/index.html
   - The FileResponse route must NOT require API key authentication

2. API key injection at startup:
   - On application startup (use @app.on_event("startup") or lifespan context):
     - Read the content of /app/static/index.html
     - Replace the literal string "REPLACE_ME" with the value of the API_KEY environment variable
     - Write the modified content back to /app/static/index.html
   - This means the running container serves an index.html with the real API key embedded
   - Log a startup message: "Static UI ready" (do not log the key value)

3. Do not add authentication to the GET / route or the /static mount
4. Do not change any existing routes or the authentication dependency

Import FileResponse from fastapi.responses and StaticFiles from fastapi.staticfiles.
Do not modify db.py or index.html source file directly.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | GET / returns HTML content | `curl -s http://localhost:8000/` contains `Customer Risk Lookup` |
| TC2 | Served HTML contains real API key (not "REPLACE_ME") | `curl -s http://localhost:8000/ | grep "REPLACE_ME"` returns no match |
| TC3 | GET / does not require X-API-Key header | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/` returns 200 |
| TC4 | Static file mount is accessible | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/static/index.html` returns 200 |

**Verification command:**
```bash
docker compose up -d --build && sleep 25 && \
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ && \
curl -s http://localhost:8000/ | grep -c "Customer Risk Lookup" && \
curl -s http://localhost:8000/ | grep -c "REPLACE_ME"
# Last grep should return 0 (key was substituted)
```

**Invariant flag:** Touches **INV-04** (GET / must be exempt from auth — confirms UI route has no key requirement) and **INV-05** (API key injection must not log the key value).  
**Code review:**  
- Confirm the GET / route has no `dependencies` parameter (not authenticated).  
- Confirm the startup handler replaces `REPLACE_ME` and does not log the key value.  
- Confirm the `StaticFiles` mount path does not overlap with API routes.

---

### S4.T3 — End-to-end browser smoke test (manual)

**Description:**  
Manual verification task. No new code. Confirm that the full stack works from a browser: UI loads, customer lookup returns correct data, errors are displayed correctly. Record results in VERIFICATION_RECORD.md.

**Inputs:** Running stack (`docker compose up -d --build`)  
**Outputs:** Written verification record (no code changes)

**CC Prompt:**
```
This is a manual verification task — do not write any code.

Provide a step-by-step browser test script I can follow to verify the UI end-to-end.
The script should cover:
1. Page load verification
2. Successful lookup for one LOW, one MEDIUM, one HIGH tier customer
3. 404 case (unknown customer ID)
4. Empty input validation
5. Visual verification of tier colour coding

Format as a numbered checklist I can tick off manually.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | Page loads at `http://localhost:8000/` | Title "Customer Risk Lookup" visible, input and button rendered |
| TC2 | Enter CUST-001, click Look Up | risk_tier "LOW" displayed in green, risk_factors listed |
| TC3 | Enter CUST-007, click Look Up | risk_tier "MEDIUM" displayed in amber |
| TC4 | Enter CUST-013, click Look Up | risk_tier "HIGH" displayed in red |
| TC5 | Enter NOTEXIST, click Look Up | "Customer not found" message displayed |
| TC6 | Submit empty input | "Please enter a customer ID" shown, no network request made |

**Verification command:**
```
Manual — open http://localhost:8000/ in a browser and follow the test script produced by CC.
```

**Invariant flag:** None (manual UI verification — no code changes).

---

## Session 5 — System Verification and README

**Session goal:** The fully assembled system is verified against every invariant end to end. A README is produced that enables any engineer to start the system from scratch with no prior knowledge of the codebase.

**Estimated duration:** ~1h 00m  
(T1: 33m · T2: 28m)

**Integration check:** This session IS the system integration check. Completion of T1 with all invariants PASS constitutes the integration check for the full system.

---

### S5.T1 — System invariant verification (Phase 8 preparation)

**Description:**  
Execute a structured verification run against each invariant from INVARIANTS.md using the fully assembled, running stack. Record PASS or FAIL for each. This produces the evidence required for the Phase 8 sign-off. No new code — only test execution and recording.

**Inputs:** Running stack, INVARIANTS.md  
**Outputs:** Completed VERIFICATION_CHECKLIST.md entries for INV-01 through INV-09

**CC Prompt:**
```
This is a verification task — do not write any code.

Produce a set of exact shell commands (one block per invariant) that I can run against a
live docker compose stack to verify each invariant from INVARIANTS.md.

For each invariant, provide:
- The invariant text (abbreviated)
- The exact command(s) to run
- What a PASS result looks like
- What a FAIL result looks like

Cover all nine invariants: INV-01 through INV-09.
```

**Test Cases (one per invariant):**

| Invariant | Test | Pass Condition |
|---|---|---|
| INV-01 | `grep -rni "INSERT\|UPDATE\|DELETE\|DDL" api/*.py` | No matches |
| INV-02 | Query CUST-001 via API, query same row direct from DB, compare fields | Values identical |
| INV-03 | Query CUST-001 — confirm returned customer_id == "CUST-001" | customer_id field matches exactly |
| INV-04 | Request without key → 401; with wrong key → 401; with correct key → 200 | All three pass |
| INV-05 | `docker compose logs api` after several requests; grep for API_KEY value | No match in logs |
| INV-06 | Code review: no f-string or concatenation into SQL in any `.py` file | No matches |
| INV-07 | Trigger a 500 (bad DB creds temporarily), inspect response body | No stack trace in response |
| INV-08 | `SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier` | LOW≥1, MEDIUM≥1, HIGH≥1 |
| INV-09 | `docker compose up -d` from cold; API only serves after postgres healthy | No 500s in first 30s window |

**Verification command:**
```bash
# Run all invariant checks in sequence
echo "=== INV-01: No write paths ===" && \
grep -rni "INSERT\|UPDATE\|DELETE\|DROP\|CREATE\|ALTER\|TRUNCATE" customer-risk-api/api/ --include="*.py" || echo "PASS: no write SQL found"

echo "=== INV-03: Correct row returned ===" && \
curl -s -H "X-API-Key: $(grep API_KEY customer-risk-api/.env | cut -d= -f2)" \
  http://localhost:8000/customer/CUST-001 | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['customer_id']=='CUST-001', 'FAIL'; print('PASS')"

echo "=== INV-04: Auth enforcement ===" && \
R1=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/CUST-001) && \
R2=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: badkey" http://localhost:8000/customer/CUST-001) && \
R3=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $(grep API_KEY customer-risk-api/.env | cut -d= -f2)" http://localhost:8000/customer/CUST-001) && \
echo "No key: $R1 (expect 401) | Wrong key: $R2 (expect 401) | Good key: $R3 (expect 200)"

echo "=== INV-08: All tiers seeded ===" && \
docker compose -f customer-risk-api/docker-compose.yml exec postgres \
  psql -U riskuser -d riskdb -c "SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier ORDER BY risk_tier;"
```

**Invariant flag:** Directly verifies all nine invariants. Full code review pass required before recording sign-off.

---

### S5.T2 — README

**Description:**  
Create `README.md` at the project root. Covers prerequisites, setup, startup, how to use the UI, how to use the API directly, how to reset state (volumes), known limitations, and environment variable reference.

**Inputs:** All project files (complete system)  
**Outputs:** `README.md`

**CC Prompt:**
```
Create README.md at the project root (customer-risk-api/README.md).

Required sections:
1. **Overview** — one paragraph: what this system is and what it does
2. **Prerequisites** — Docker Desktop (or Docker Engine + Compose plugin), a terminal
3. **Setup** — step-by-step:
   a. Clone the repository
   b. Copy .env.example to .env
   c. Set API_KEY in .env to a value of your choice
   d. Run: docker compose up -d
   e. Wait ~20 seconds for Postgres to initialise
   f. Open http://localhost:8000/ in a browser
4. **Using the UI** — brief description of the customer ID lookup flow
5. **Using the API directly** — example curl commands:
   - GET /health (no auth)
   - GET /customer/{customer_id} (with X-API-Key header)
   - 404 example
   - 401 example
6. **Resetting the database** — `docker compose down -v` clears volumes; next `up` re-seeds
7. **Known limitations** — API key is visible in browser network traffic; no per-user auth;
   not production-hardened
8. **Environment variables** — table of all six variables with descriptions and example values
9. **Seed data** — table listing the 15 customer IDs, their tiers, and their risk factors

Use GitHub-flavoured Markdown. Keep each section concise — this is an operational reference,
not a design document.
```

**Test Cases:**

| # | Scenario | Expected Outcome |
|---|---|---|
| TC1 | README contains all 9 required sections | Manual review — all section headings present |
| TC2 | `docker compose down -v` command is explicitly documented | `grep "down -v" README.md` matches |
| TC3 | All 6 environment variables are documented | Manual review of variables table |
| TC4 | Known limitations section mentions browser key visibility | `grep -i "browser\|network" README.md` matches |

**Verification command:**
```bash
grep -c "^##" customer-risk-api/README.md
# Expect: 9 or more section headings
grep "down -v" customer-risk-api/README.md
grep -i "browser\|network traffic" customer-risk-api/README.md
```

**Invariant flag:** None.

---

## Appendix A — Environment Variable Reference

| Variable | Used By | Description | Example |
|---|---|---|---|
| `API_KEY` | FastAPI, UI (injected) | Shared secret for API authentication | `supersecret-demo-key-2024` |
| `POSTGRES_USER` | Postgres, FastAPI | DB username | `riskuser` |
| `POSTGRES_PASSWORD` | Postgres, FastAPI | DB password | `changeme` |
| `POSTGRES_DB` | Postgres, FastAPI | Database name | `riskdb` |
| `POSTGRES_HOST` | FastAPI | Hostname of Postgres service (Docker service name) | `postgres` |
| `POSTGRES_PORT` | FastAPI | Port Postgres listens on | `5432` |

---

## Appendix B — File Manifest (End State)

```
customer-risk-api/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── db/
│   └── init.sql
└── api/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py
    ├── db.py
    └── static/
        └── index.html
```

---

## Appendix C — Invariant Coverage Matrix

| Invariant | S1 | S2 | S3 | S4 | S5 |
|---|---|---|---|---|---|
| INV-01: No writes to database | T3 (schema review) | T4 (code review) | T3 (grep audit) | — | T1 (final audit) |
| INV-02: Data matches DB exactly | — | T4 (code review) | — | — | T1 |
| INV-03: Parameterised queries only | — | T4 (code review) | — | — | T1 |
| INV-04: All API routes require auth | — | — | T1 (enforcement) | T2 (UI route exempt) | T1 |
| INV-05: Key never in response/logs | — | T3 (db.py review) | T1 (auth review) | T2 (startup handler) | T1 |
| INV-06: No string interpolation into SQL | — | T4 (code review) | — | — | T1 |
| INV-07: No internal detail in errors | — | T4 (500 handler) | T2 (global handler) | — | T1 |
| INV-08: All tiers seeded | T3 (seed verify) | — | — | — | T1 |
| INV-09: API waits for DB healthy | T2 (health check) | T2 (depends_on) | — | — | T1 |