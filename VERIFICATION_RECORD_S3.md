# Verification Record — S3: Authentication, Error Handling, Security

---

## S3.T1 — API key authentication middleware

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Request to `/customer/{id}` with no `X-API-Key` header | HTTP 401, `{"detail": "Unauthorized"}` | HTTP 401, `{"detail":"Unauthorized"}` |
| TC2 | Request with wrong key value | HTTP 401, `{"detail": "Unauthorized"}` | HTTP 401, `{"detail":"Unauthorized"}` |
| TC3 | Request with correct key | HTTP 200 with customer data | HTTP 200, correct customer data |
| TC4 | Request to `/health` with no key | HTTP 200, `{"status": "ok"}` | HTTP 200, `{"status":"ok"}` |
| TC5 | Request to `/health` with wrong key | HTTP 200 (health is exempt from auth) | HTTP 200, confirmed exempt |
| TC6 | 401 response body does not contain the API key value | Response body parsed: no key value present | Confirmed — body is `{"detail":"Unauthorized"}` only |
| TC7 | Empty string as key value | HTTP 401 | HTTP 401 — `hmac.compare_digest("", API_KEY)` returns False |
| TC8 | `API_KEY` not set in environment | Application fails at startup (not silently) | Confirmed — `os.environ["API_KEY"]` raises `KeyError` at import time |

**Code review checklist:**
- [x] `hmac.compare_digest` used (not `==`)
- [x] Dependency applied via `dependencies=[Depends(verify_api_key)]` on customer route
- [x] `/health` route has no `dependencies` parameter
- [x] Startup reads `os.environ["API_KEY"]` — raises on missing (not silent default)
- [x] No log statement includes `x_api_key` or the `API_KEY` env var value
- [x] 401 detail is the literal `"Unauthorized"` — not an f-string or variable

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S3.T2 — Global error handler: suppress internal detail

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Unhandled exception in a route | HTTP 500, body exactly `{"detail": "Internal server error"}` | Confirmed via code review — handler returns `JSONResponse(status_code=500, content={"detail": "Internal server error"})` |
| TC2 | HTTPException (e.g. 404) still returns its own detail | 404 with `{"detail": "Customer not found"}` — not overridden | Confirmed — `isinstance(exc, HTTPException)` re-raises before handler returns |
| TC3 | 401 still returns `{"detail": "Unauthorized"}` | Not overridden by global handler | Confirmed — 401 tested and passed after T2 applied |
| TC4 | Response body for 500 contains no Python traceback text | Manual inspection of response body | Confirmed — response body is literal string only; traceback goes to server log via `logger.error(..., exc_info=True)` |

**Code review checklist:**
- [x] Handler catches `Exception` (not just `psycopg2.Error`)
- [x] Response is `JSONResponse(status_code=500, content={"detail": "Internal server error"})`
- [x] `logging.error(...)` call does not log `request.headers`
- [x] `HTTPException` is explicitly re-raised — FastAPI's own handler takes over

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S3.T3 — Verify no write paths exist in application code

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | No INSERT/UPDATE/DELETE/DDL in any Python file | All files report "none" for write operations | Confirmed — no matches |
| TC2 | No ORM library imported | No SQLAlchemy or equivalent import found | Confirmed — no matches |
| TC3 | psycopg2 `execute()` calls use only SELECT | Confirmed by code review | Confirmed — one `execute()` call in `main.py`, SELECT only |

**Write-path audit report:**

```
File: api/main.py
  SQL statements found: one — SELECT customer_id, risk_tier, risk_factors FROM customers WHERE customer_id = %s (read-only)
  Write operations found: none

File: api/db.py
  SQL statements found: none — get_connection() opens a connection only, no queries
  Write operations found: none

Conclusion: PASS — no INSERT, UPDATE, DELETE, or DDL found in any Python file.
            No ORM or write-capable library imported. INV-01 satisfied.
```

**Verdict:**
- [x] Pass
- [ ] Fail

---

## Integration Check

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

| # | Check | Expected | Result |
|---|---|---|---|
| IC1 | No key → 401 | HTTP 401 | HTTP 401 |
| IC2 | Wrong key → 401 | HTTP 401 | HTTP 401 |
| IC3 | Correct key → 200 with data | HTTP 200, JSON customer record | HTTP 200, `{"customer_id":"CUST-001","risk_tier":"LOW","risk_factors":["stable_income"]}` |
| IC4 | `/health` no key → 200 | HTTP 200, `{"status":"ok"}` | HTTP 200, `{"status":"ok"}` |

**Integration Verdict:**
- [x] Pass
- [ ] Fail
