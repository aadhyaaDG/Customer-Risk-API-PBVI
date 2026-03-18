# Verification Record — S1: Infrastructure: Docker Compose, Postgres, Schema, Seed Data

---

## S1.T1 — Project scaffold and `.env.example`

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | All required files and directories exist | `ls` shows `docker-compose.yml`, `.env.example`, `.gitignore`, `api/`, `db/` | Shows 5 paths |
| TC2 | `.env.example` contains all six variable names | `grep -c "=" .env.example` returns 6 | Returns 6 variables |
| TC3 | `.env` is listed in `.gitignore` | `grep "^\.env$" .gitignore` returns a match | returns 1 match |
| TC4 | `docker-compose.yml` defines both `postgres` and `api` services | `grep -c "^\s\{2\}[a-z]" docker-compose.yml` returns at least 2 | returns 2 |

**Prediction Statement:** <!-- do not pre-populate -->

**Verdict:**
- [ 4 ] Pass
- [ 0 ] Fail

---

## S1.T2 — Docker Compose: Postgres service with health check

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | `docker compose up -d postgres` starts without error | Exit code 0 | Exit code 0 |
| TC2 | Postgres container reaches `healthy` within 60s | `docker compose ps` shows `(healthy)` | Shows `(healthy)` |
| TC3 | Can connect and run a query | `docker exec <container> psql -U riskuser -d riskdb -c "SELECT 1;"` returns `1` | Returns `1` |
| TC4 | Named volume `pgdata` is created | `docker volume ls` shows `customer-risk-api_pgdata` | Shows `customer-risk-api_pgdata` |

**Prediction Statement:** <!-- do not pre-populate -->

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S1.T3 — Database schema and seed data init script

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Script runs without SQL errors | `psql` exit code 0 | Exit code 0 |
| TC2 | Table exists with correct columns | `\d customers` shows customer_id, risk_tier, risk_factors | Shows customer_id, risk_tier, risk_factors |
| TC3 | Exactly 15 rows inserted | `SELECT COUNT(*) FROM customers;` returns 15 | Returns 15 |
| TC4 | All three tiers present with count 5 each | `SELECT risk_tier, COUNT(*) FROM customers GROUP BY risk_tier;` returns LOW=5, MEDIUM=5, HIGH=5 | Returns LOW=5, MEDIUM=5, HIGH=5 |
| TC5 | `risk_factors` is a non-empty array for every row | `SELECT COUNT(*) FROM customers WHERE risk_factors = '{}';` returns 0 | Returns 0 |
| TC6 | CHECK constraint rejects invalid tier | `INSERT INTO customers VALUES ('X', 'INVALID', '{}');` raises constraint violation | Raises check constraint violation |

**Prediction Statement:** <!-- do not pre-populate -->

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S1.T4 — Mount init script into Docker Compose

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Fresh stack start seeds the database | After `docker compose down -v && docker compose up -d postgres`, all 15 rows are present | 15 rows present |
| TC2 | Init script is mounted read-only | `docker compose exec postgres touch /docker-entrypoint-initdb.d/init.sql` fails with permission error | Permission error |
| TC3 | Second start with existing volume skips init script | After `docker compose restart postgres` (without `-v`), data is still present and count is still 15 | Count still 15 |

**Prediction Statement:** <!-- do not pre-populate -->

**Verdict:**
- [x] Pass
- [ ] Fail
