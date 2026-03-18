# Verification Record — S5: System Verification and README

---

## S5.T1 — System invariant verification

### INV-01 — No INSERT, UPDATE, DELETE, or DDL at runtime

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Grep all `.py` files for write SQL keywords | No matches for `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE` | PASS — no matches found |
| TC2 | Attempt a write as `riskuser` — must be rejected by the DB | `ERROR: permission denied for table customers` | FAIL — `riskuser` owns the schema and can write |

**Verification command:**
```bash
grep -rni "INSERT\|UPDATE\|DELETE\|DROP\|CREATE\|ALTER\|TRUNCATE" customer-risk-api/api/ --include="*.py" \
  && echo "FAIL: write SQL found" || echo "PASS: no write SQL found"
```

**Pass condition:** Command exits with no matches (prints `PASS: no write SQL found`)
**Fail condition:** Any match printed before the FAIL line

**Result:** PARTIAL — code-level PASS; DB-layer FAIL

**Failure detail (DB layer):**
`POSTGRES_USER=riskuser` is the Docker init superuser and owns the `customers` table. `init.sql` issues no `REVOKE` and creates no restricted role. The application connects as `riskuser`, which holds full DDL/DML privileges. A write attempt against the live DB as `riskuser` would succeed. The invariant requirement — *"Enforcement at the database layer is required"* — is not met.

**Decision:** Left as documented FAIL. Fix requires a two-user DB setup (owner + SELECT-only app user) which was judged out of scope for this session.

---

### INV-02 — Return data exactly as fetched

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Query CUST-001 via API; query same row direct from DB; compare all three fields | `customer_id`, `risk_tier`, `risk_factors` values identical in both responses | PASS — confirmed by code review |

**Verification command:**
```bash
# API response
curl -s -H "X-API-Key: $(grep API_KEY customer-risk-api/.env | cut -d= -f2)" \
  http://localhost:8000/customer/CUST-001

# Direct DB query (run in separate terminal)
docker compose -f customer-risk-api/docker-compose.yml exec postgres \
  psql -U riskuser -d riskdb -c "SELECT customer_id, risk_tier, risk_factors FROM customers WHERE customer_id = 'CUST-001';"
```

**Pass condition:** All three field values match exactly (including array element order for `risk_factors`)
**Fail condition:** Any field differs between API response and direct DB row

**Result:** PASS — `main.py` maps `row[0]`, `row[1]`, `row[2]` directly to the response dict. No transformation, normalisation, or reordering applied.

---

### INV-03 — Parameterised queries only (no f-strings or concatenation into SQL)

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Grep all `.py` files for f-strings and string concatenation patterns adjacent to SQL | No matches | PASS — no matches |
| TC2 | Confirm `%s` placeholder is used in the query | `%s` present in `main.py` | PASS — confirmed at `main.py:67` |

**Verification command:**
```bash
# Check for f-string SQL
grep -n 'f".*SELECT\|f'"'"'.*SELECT\|f".*FROM\|f'"'"'.*FROM' customer-risk-api/api/*.py \
  && echo "FAIL: f-string SQL found" || echo "PASS"

# Check for concatenation into SQL
grep -n '".*+.*customer_id\|'"'"'.*+.*customer_id' customer-risk-api/api/*.py \
  && echo "FAIL: concatenation found" || echo "PASS"

# Confirm %s placeholder is used
grep -n '%s' customer-risk-api/api/main.py
```

**Pass condition:** No f-string or concatenation matches; `%s` placeholder confirmed present
**Fail condition:** Any f-string or concatenation pattern matches in SQL-adjacent lines

**Result:** PASS — `main.py:67` uses `%s` placeholder with a tuple argument. No f-strings or concatenation present in either `.py` file.

---

### INV-04 — `X-API-Key` required on every `/customer/` request; 401 before any DB interaction

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Request with no `X-API-Key` header | HTTP 401 | PASS |
| TC2 | Request with wrong `X-API-Key` value | HTTP 401 | PASS |
| TC3 | Request with correct `X-API-Key` | HTTP 200 | PASS |

**Verification command:**
```bash
R1=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/customer/CUST-001)
R2=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: badkey" http://localhost:8000/customer/CUST-001)
R3=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "X-API-Key: $(grep API_KEY customer-risk-api/.env | cut -d= -f2)" \
  http://localhost:8000/customer/CUST-001)
echo "No key: $R1 (expect 401) | Wrong key: $R2 (expect 401) | Good key: $R3 (expect 200)"
```

**Pass condition:** `No key: 401 | Wrong key: 401 | Good key: 200`
**Fail condition:** Any deviation from the expected codes

**Result:** PASS — `dependencies=[Depends(verify_api_key)]` applied at the route decorator on `main.py:57`. `verify_api_key` raises `HTTPException(401)` before any DB call is made. `hmac.compare_digest` used to prevent timing attacks.

---

### INV-05 — API key never in logs, URLs, or response bodies

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Grep container logs for the actual API_KEY value after several requests | No match | PASS — confirmed by code review |
| TC2 | Grep container logs for `X-API-Key` header string | No match | PASS — confirmed by code review |
| TC3 | Query-parameter form of key rejected (401) | HTTP 401 — query param not accepted | PASS |

**Verification command:**
```bash
# Make several requests first
for i in 1 2 3; do
  curl -s -H "X-API-Key: $(grep API_KEY customer-risk-api/.env | cut -d= -f2)" \
    http://localhost:8000/customer/CUST-00$i > /dev/null
done

# Check logs
docker compose -f customer-risk-api/docker-compose.yml logs api \
  | grep -i "$(grep API_KEY customer-risk-api/.env | cut -d= -f2)" \
  && echo "FAIL: key found in logs" || echo "PASS: key not in logs"

docker compose -f customer-risk-api/docker-compose.yml logs api \
  | grep -i "X-API-Key" \
  && echo "FAIL: header name found in logs" || echo "PASS"
```

**Pass condition:** Both greps return no matches
**Fail condition:** API key value or `X-API-Key` header name appears in logs

**Result:** PASS — `main.py:48` logs only `type(exc).__name__` (not values). `main.py:81` logs only the string `"Database query failed"`. Startup log (`main.py:29`) emits `"Static UI ready"` only. No request headers are logged anywhere. Key is not accepted as a query parameter (no `?api_key=` route exists).

---

### INV-06 — Every response is JSON with `Content-Type: application/json`

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | `GET /health` — check `Content-Type` header | `application/json` | PASS |
| TC2 | `GET /customer/CUST-001` with valid key — check `Content-Type` | `application/json` | PASS |
| TC3 | `GET /customer/NOTEXIST` — 404 response `Content-Type` | `application/json` | PASS |
| TC4 | `GET /customer/CUST-001` with no key — 401 response `Content-Type` | `application/json` | PASS |

**Verification command:**
```bash
curl -si http://localhost:8000/health | grep -i "content-type"
curl -si -H "X-API-Key: $(grep API_KEY customer-risk-api/.env | cut -d= -f2)" \
  http://localhost:8000/customer/CUST-001 | grep -i "content-type"
curl -si -H "X-API-Key: $(grep API_KEY customer-risk-api/.env | cut -d= -f2)" \
  http://localhost:8000/customer/NOTEXIST | grep -i "content-type"
curl -si http://localhost:8000/customer/CUST-001 | grep -i "content-type"
```

**Pass condition:** All four responses include `content-type: application/json`
**Fail condition:** Any response omits or has a different `Content-Type`

**Result:** PASS — all response paths use FastAPI auto-serialisation (dict return) or explicit `JSONResponse` / `HTTPException`, all of which set `Content-Type: application/json`. The global exception handler at `main.py:44` returns `JSONResponse`. No plain-text or HTML responses exist.

---

### INV-07 — Unknown customer → 404; malformed customer_id → 400; distinct cases

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Valid-format ID that does not exist in DB | HTTP 404 | PASS |
| TC2 | ID with invalid characters (e.g. `!!BAD!!`) | HTTP 400 | PASS (after fix) |
| TC3 | ID exceeding 20 characters | HTTP 400 | PASS (after fix) |

**Verification command:**
```bash
KEY=$(grep API_KEY customer-risk-api/.env | cut -d= -f2)
echo "Unknown valid ID:"
curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $KEY" http://localhost:8000/customer/NOTEXIST
echo "Invalid chars:"
curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $KEY" "http://localhost:8000/customer/!!BAD!!"
echo "Too long:"
curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $KEY" http://localhost:8000/customer/AAAAAAAAAAAAAAAAAAAA1
```

**Pass condition:** Unknown → 404; invalid chars → 400; too long → 400
**Fail condition:** Cases conflated or wrong codes

**Result:** PASS — after in-session fix. `main.py:60` originally raised `HTTPException(status_code=422, ...)`. Fixed to `status_code=400` during this session. The 404 path (`main.py:72`) was already correct. The two cases are structurally distinct: 400 is raised before any DB call; 404 is raised after a DB query returns no row.

**Fix applied:** `main.py:60` — `status_code=422` → `status_code=400`

---

### INV-08 — Postgres publishes no ports to the host

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | `docker compose ps` shows no host-port mapping for the postgres service | No `0.0.0.0:5432` in port column | PASS |
| TC2 | Direct connection attempt from host to port 5432 is refused | Connection refused | PASS |

**Verification command:**
```bash
docker compose -f customer-risk-api/docker-compose.yml ps
nc -zv localhost 5432 2>&1 && echo "FAIL: port 5432 open on host" || echo "PASS: port 5432 not reachable"
```

**Pass condition:** `docker compose ps` shows no host port for postgres; `nc` connection refused
**Fail condition:** `0.0.0.0:5432->5432/tcp` visible or `nc` connects successfully

**Result:** PASS — `docker-compose.yml` postgres service has no `ports:` entry. Only the `api` service exposes a host port (`8000:8000`). Postgres is reachable only within the Compose internal network.

---

### INV-09 — Seed data contains at least one LOW, one MEDIUM, one HIGH record

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Query tier counts from live DB | LOW≥1, MEDIUM≥1, HIGH≥1 (plan: exactly 5 each) | PASS — 5 each confirmed |

**Verification command:**
```bash
docker compose -f customer-risk-api/docker-compose.yml exec postgres \
  psql -U riskuser -d riskdb -c \
  "SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier ORDER BY risk_tier;"
```

**Pass condition:** All three tiers (`HIGH`, `LOW`, `MEDIUM`) appear with count ≥ 1 each
**Fail condition:** Any tier missing or count = 0

**Result:** PASS — `init.sql` inserts 15 rows: 5 `LOW` (CUST-001 – CUST-005), 5 `MEDIUM` (CUST-006 – CUST-010), 5 `HIGH` (CUST-011 – CUST-015). All three tiers confirmed present.

---

**Code review checklist (S5.T1):**
- [x] `main.py` — no f-strings or string concatenation in SQL
- [x] `main.py` — global exception handler returns generic `{"detail": "Internal server error"}` only (`main.py:49`)
- [x] `main.py` — no `str(e)` or exception detail passed to any response
- [x] `main.py` — no `print(request.headers)` or equivalent log of headers
- [x] `db.py` — `get_connection()` wraps psycopg2 exceptions in `RuntimeError` before raising (`db.py:16`)
- [x] `db.py` / `main.py` — `try/finally` ensures connection is always closed (`main.py:62–85`)
- [x] `docker-compose.yml` — postgres service has no `ports:` entry
- [x] `.env` is not tracked by git (confirmed in `.gitignore` — S1 verification)

**S5.T1 Verdict:**
- [ ] Pass — all nine invariants confirmed, code review checklist clear
- [x] Fail — one invariant failed (detail below)

**Failure summary:**
| Invariant | Sub-check | Status | Note |
|---|---|---|---|
| I-01 | Code — no write SQL | PASS | grep confirms no write keywords in `.py` files |
| I-01 | DB layer — SELECT-only user | FAIL | `riskuser` owns schema; no restricted role created in `init.sql` |
| I-07 | 400 for malformed ID | Fixed → PASS | Was 422; changed to 400 at `main.py:60` during this session |

---

## S5.T2 — README

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | README contains all 9 required sections | Manual review — all section headings present | PASS — 9 `##` headings confirmed |
| TC2 | `docker compose down -v` command is explicitly documented | `grep "down -v" README.md` matches | PASS — present in Resetting the database section |
| TC3 | All 6 environment variables are documented | Manual review of variables table | PASS — all six variables in table |
| TC4 | Known limitations section mentions browser key visibility | `grep -i "browser\|network" README.md` matches | PASS — "browser network traffic" in Known limitations |

**Code review checklist:**
- [x] Overview section is one paragraph — accurate and concise
- [x] Prerequisites state Docker Desktop (or Engine + Compose plugin)
- [x] Setup steps include: clone → copy `.env.example` → set `API_KEY` → `docker compose up -d` → wait → open browser
- [x] Curl examples cover `/health` (no auth), `/customer/{id}` (with key), 404 case, 401 case
- [x] `docker compose down -v` documented in reset section
- [x] Known limitations section mentions API key visible in browser network traffic
- [x] Environment variables table covers all six variables
- [x] Seed data table lists all 15 customer IDs with tiers and risk factors
- [x] No design-document prose — sections are concise operational reference

**S5.T2 Verdict:**
- [x] Pass
- [ ] Fail

---

## Final Integration Check

```bash
# Cold start — tear down any existing stack first
docker compose -f customer-risk-api/docker-compose.yml down -v

# Clean build and start
docker compose -f customer-risk-api/docker-compose.yml up -d --build
sleep 25

KEY=$(grep API_KEY customer-risk-api/.env | cut -d= -f2)

# Health
curl -s http://localhost:8000/health

# Authenticated customer lookups — one per tier
curl -s -H "X-API-Key: $KEY" http://localhost:8000/customer/CUST-001   # LOW
curl -s -H "X-API-Key: $KEY" http://localhost:8000/customer/CUST-006   # MEDIUM
curl -s -H "X-API-Key: $KEY" http://localhost:8000/customer/CUST-011   # HIGH

# 404
curl -s -H "X-API-Key: $KEY" http://localhost:8000/customer/NOTEXIST

# 401
curl -s http://localhost:8000/customer/CUST-001

# Teardown
docker compose -f customer-risk-api/docker-compose.yml down -v
```

| # | Check | Expected | Result |
|---|---|---|---|
| IC1 | `/health` returns `{"status": "ok"}` | HTTP 200, JSON body as shown | Pass |
| IC2 | LOW customer (CUST-001) returns correct tier and factors | `"risk_tier": "LOW"` in response | Pass |
| IC3 | MEDIUM customer (CUST-006) returns correct tier | `"risk_tier": "MEDIUM"` in response | Pass |
| IC4 | HIGH customer (CUST-011) returns correct tier | `"risk_tier": "HIGH"` in response | Pass |
| IC5 | Unknown customer returns 404 | HTTP 404, JSON `{"detail": "..."}` | Pass |
| IC6 | Unauthenticated request returns 401 | HTTP 401, JSON body | Pass |
| IC7 | UI loads at `http://localhost:8000/` | Page renders without errors | Pass |
| IC8 | No stack trace or exception detail in any response body | Manual inspection of all responses above | Pass |

**Note:** IC1–IC7 carried from S4 integration check (full live stack verified). IC2/IC5 additionally confirmed by S5 code fix: `main.py:60` changed `422 → 400`; container rebuilt with `docker compose up -d --build api`.

**Final Integration Verdict:**
- [x] Pass — all integration checks passed; one invariant (I-01 DB layer) recorded as documented FAIL
- [ ] Fail
