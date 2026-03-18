# Session Log — S5: System Verification and README

**Branch:** `add-md-files`
**Date:** 18-03-2026

---

| Task Id | Task Name | Status | Commit |
|---|---|---|---|
| S5.T1 | System invariant verification | Complete | — |
| S5.T2 | README | Complete | — |

---

## Notes

**I-07 fix applied during session:**
Code review revealed `main.py:60` raised `HTTPException(status_code=422, ...)` for malformed customer IDs. I-07 requires `400`. Fixed in-session by changing `422 → 400`. No other code changes were made.

**I-01 DB-layer FAIL — documented, not fixed:**
`POSTGRES_USER` (`riskuser`) is the Docker init superuser and owns the `customers` table. `init.sql` does not create a restricted SELECT-only role, so the application connects with full DDL/DML privileges. The code-level check passes (no write SQL in any `.py` file), but the database-layer enforcement requirement stated in I-01 is not met. Decision: record as documented FAIL; scope of fix judged too large for this session.
