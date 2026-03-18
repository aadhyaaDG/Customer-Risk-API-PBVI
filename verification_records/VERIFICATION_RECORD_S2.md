# Verification Record — S2: FastAPI Application Core

---

## S2.T1 — FastAPI project structure and dependencies

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | `requirements.txt` contains all three dependencies | `grep -c "==" api/requirements.txt` returns 3 | Returns 3 |
| TC2 | `Dockerfile` uses `python:3.11-slim` | `grep "FROM python:3.11-slim" api/Dockerfile` matches | Matches |
| TC3 | `main.py` is syntactically valid Python | `python3 -c "import ast; ast.parse(open('api/main.py').read())"` exits 0 | Exits 0 |
| TC4 | FastAPI app instance is created | `grep "FastAPI()" api/main.py` matches | Matches |

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S2.T2 — Docker Compose: wire API service with build and depends_on

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | `docker compose up -d` starts both containers | Both `postgres` and `api` containers running | Both running |
| TC2 | API container waits for Postgres healthy before starting | `docker compose logs api` shows no connection refused errors on startup | No errors |
| TC3 | `/health` returns 200 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` returns 200 | Returns 200 |
| TC4 | Port 8000 is accessible from host | `curl http://localhost:8000/health` responds | Responds |

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S2.T3 — Database connection module

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Module is syntactically valid | `python3 -c "import ast; ast.parse(open('api/db.py').read())"` exits 0 | Exits 0 |
| TC2 | `get_connection()` function is defined | `grep "def get_connection" api/db.py` matches | Matches |
| TC3 | No credential values in log statements | `grep -i "password\|api_key\|secret" api/db.py` returns no matches on log/print lines | No matches |
| TC4 | RuntimeError raised on failure (not psycopg2 error) | Code review confirms `except` block raises `RuntimeError("Database connection failed")` | Confirmed |
| TC5 | psycopg2 is imported | `grep "import psycopg2" api/db.py` matches | Matches |

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S2.T4 — Customer lookup endpoint

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Valid customer_id that exists (e.g. CUST-001) | HTTP 200, JSON with correct customer_id, risk_tier=LOW, non-empty risk_factors array | HTTP 200, correct data |
| TC2 | Valid customer_id for a HIGH tier customer (e.g. CUST-011) | HTTP 200, risk_tier = "HIGH" | HTTP 200, risk_tier=HIGH |
| TC3 | Valid customer_id that does not exist | HTTP 404, `{"detail": "Customer not found"}` | HTTP 404, correct body |
| TC4 | customer_id with SQL injection attempt (e.g. `CUST-001'--`) | HTTP 422 (rejected by validation pattern before reaching DB) | HTTP 422 |
| TC5 | customer_id exceeding 20 characters | HTTP 422 | HTTP 422 |
| TC6 | customer_id containing spaces or special chars | HTTP 422 | HTTP 422 |
| TC7 | risk_factors is returned as a JSON array (not a string) | `risk_factors` in response is `[]` type, not a string | Array type confirmed |
| TC8 | Response contains exactly three keys | No extra fields: only customer_id, risk_tier, risk_factors | Exactly three keys |

**Verdict:**
- [x] Pass
- [ ] Fail

---

## Integration Check

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

| # | Check | Expected | Result |
|---|---|---|---|
| IC1 | Both containers running | `docker compose ps` shows postgres and api | Both healthy |
| IC2 | `/health` returns `{"status": "ok"}` | HTTP 200 with correct body | HTTP 200, `{"status":"ok"}` |
| IC3 | `/customer/CUST-001` returns LOW tier data | HTTP 200, risk_tier=LOW, risk_factors array | HTTP 200, correct data |
| IC4 | `/customer/NOTEXIST` returns 404 | HTTP 404 | HTTP 404 |

**Integration Verdict:**
- [x] Pass
- [ ] Fail
