# Verification Record — S4: UI and Integration Wiring

---

## S4.T1 — Static UI HTML file

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | File is valid HTML | `HTMLParser().feed(...)` exits 0 | Confirmed — HTML parses without error |
| TC2 | Required IDs present: `customer-id-input`, `result-area`, `lookup-btn` | All three IDs in file | Confirmed — all three `id=` attributes present |
| TC3 | `const API_KEY = "REPLACE_ME"` constant defined | `grep "const API_KEY"` matches | Confirmed |
| TC4 | `X-API-Key` header set in fetch call | `grep "X-API-Key"` matches | Confirmed — set in fetch headers object |
| TC5 | No external script/style imports (no CDN, Bootstrap, jQuery, React) | No matches | Confirmed — no external dependencies |
| TC6 | Risk tier colour coding present for LOW, MEDIUM, HIGH | Colour classes or styles reference all three tiers | Confirmed — `.tier-LOW` (green), `.tier-MEDIUM` (amber), `.tier-HIGH` (red) CSS classes present |

**Code review checklist:**
- [x] `const API_KEY = "REPLACE_ME"` is the first statement in the `<script>` block
- [x] Fetch uses `encodeURIComponent(customerId)` — no raw user input interpolated into URL
- [x] All server-returned values passed through `escapeHtml()` before DOM insertion — XSS safe
- [x] Empty/whitespace-only input caught client-side before any network request
- [x] Result area cleared (`innerHTML = ""`) at the start of every lookup
- [x] Status codes 200, 401, 404 handled explicitly; all others fall through to generic error message
- [x] Enter key in the input field triggers lookup (same handler as button click)
- [x] `risk_factors` renders as a bulleted `<ul>` list on 200; shows "None recorded" when empty array

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S4.T2 — Serve static files from FastAPI and inject API key

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | `GET /` returns HTML content | Response body contains `Customer Risk Lookup` | Confirmed — page loads with correct heading |
| TC2 | Served HTML contains real API key, not `REPLACE_ME` | Page source contains no `REPLACE_ME` string | Confirmed — key was substituted at startup |
| TC3 | `GET /` does not require `X-API-Key` header | HTTP 200 with no auth header | Confirmed — UI accessible unauthenticated |
| TC4 | `/static/index.html` is accessible via static mount | HTTP 200 | Confirmed |

**Code review checklist:**
- [x] `StaticFiles` mounted at `/static` directly on `app` — no auth dependency
- [x] `GET /` route has no `dependencies` parameter — unauthenticated
- [x] Startup handler replaces `REPLACE_ME` with `API_KEY` value — key value not logged
- [x] Startup logs `"Static UI ready"` only — no key in log message
- [x] `FileResponse` returns `/app/static/index.html` — correct container path
- [x] No existing routes, auth dependency, or `db.py` modified

**Verdict:**
- [x] Pass
- [ ] Fail

---

## S4.T3 — End-to-end browser smoke test (manual)

| # | Scenario | Expected | Result |
|---|---|---|---|
| TC1 | Page loads at `http://localhost:8000/` | Title and card visible, input and button rendered | Pass |
| TC2 | Page source contains no `REPLACE_ME` | String absent | Pass |
| TC3 | Enter `CUST-001`, click Look Up | `LOW` tier result, green badge, risk factors listed | Pass |
| TC4 | Enter `CUST-007`, click Look Up | `MEDIUM` tier result, amber badge | Pass |
| TC5 | Enter `CUST-013`, click Look Up | `HIGH` tier result, red badge, multiple risk factors | Pass |
| TC6 | Enter `NOTEXIST`, click Look Up | "Customer not found" message | Pass |
| TC7 | Submit empty input | "Please enter a customer ID" — no network request | Pass |
| TC8 | Submit whitespace-only input | "Please enter a customer ID" — no network request | Pass |
| TC9 | Press Enter in input field (CUST-003) | Lookup fires, LOW result returned | Pass |
| TC10 | All three tier badge colours visually distinct | GREEN (LOW), AMBER (MEDIUM), RED (HIGH) legible | Pass |

**Verdict:**
- [x] Pass
- [ ] Fail

---

## Integration Check

```bash
docker compose up -d --build && sleep 25
# Open http://localhost:8000/ in a browser
# Enter CUST-001 — expect LOW tier result with risk factors displayed
# Enter CUST-011 — expect HIGH tier result
# Enter NOTEXIST — expect "Customer not found" error message
# Submit empty input — expect client-side validation message
docker compose down -v
```

| # | Check | Expected | Result |
|---|---|---|---|
| IC1 | UI loads at `http://localhost:8000/` | Page renders with no errors | Pass |
| IC2 | LOW customer (CUST-001) displays correctly | Green LOW badge, risk factors listed | Pass |
| IC3 | HIGH customer (CUST-011) displays correctly | Red HIGH badge, risk factors listed | Pass |
| IC4 | Unknown customer returns error message | "Customer not found" | Pass |
| IC5 | Empty input caught client-side | "Please enter a customer ID", no network request | Pass |

**Integration Verdict:**
- [x] Pass
- [ ] Fail
