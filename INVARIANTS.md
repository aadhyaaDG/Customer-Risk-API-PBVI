# INVARIANTS.md
## Customer Risk API
**Version:** 1.0  
**Classification:** Training Demo System  

---

## About This Document

An invariant is a condition the system must never violate, regardless of
input, deployment state, or implementation path. These are not
requirements or acceptance criteria — they are constraints. If any
invariant is violated, the system is broken by definition, even if
everything else works correctly.

Every invariant here is derived from either the requirements brief or
ARCHITECTURE.md. Each is tagged with its source for traceability.
Phase 3 implementation must treat this list as a checklist: every
invariant must have a corresponding test or a documented structural
guarantee before the system is considered complete.

---

## Group 1 — Data Access

**I-01 — Only read operations are permitted against the database**  
The application must never issue INSERT, UPDATE, DELETE, or DDL
statements at runtime. The Postgres user the application connects with
must be granted SELECT privileges only. Enforcement at the database
layer is required — API-level intent is not sufficient. A future route
or code path that accidentally performs a write must be stopped at the
database connection, not relied upon to be absent from the code.  
*Source: Requirements brief (read-only constraint)*

**I-02 — Data returned to the user must be as fetched, without transformation**  
Field values returned in API responses must be the literal values
retrieved from the database. No re-labelling, re-ordering of array
elements, normalisation, or any other modification may be applied between
the database read and the response serialisation. If the database
contains a value, that value is what the caller receives.  
*Source: Requirements brief (structured output)*

---

## Group 2 — Authentication

**I-03 — A valid API key must be present on every request to a protected endpoint**  
All requests to `/customer/` routes must carry a valid API key in the
`X-API-Key` header. Requests with a missing, empty, or invalid key must
be rejected with `401 Unauthorized` before any other processing occurs.
No database interaction may take place before the key is confirmed valid.
The dependency must be applied at the router level so that every route
under `/customer/` inherits it by default — per-route application is
the failure mode this invariant guards against.  
*Source: Requirements brief (API key authentication), Architecture Decision 2, Risk R1*

**I-04 — No data may be returned to an unauthenticated caller under any circumstances**  
An unauthenticated request must never receive customer data in any form
— not in a response body, not in an error message, not as a partial
result. Authentication failure must produce a uniform rejection with no
information about whether the requested customer ID exists or not.  
*Source: Architecture Decision 2, Risk R1*

---

## Group 3 — Information Security

**I-05 — The API key must never appear in any log, URL, or output**  
The API key must travel only in the `X-API-Key` request header. It must
not be accepted as a URL query parameter, which would expose it in
FastAPI access logs and browser history. It must not appear in any
response body, error message, or log entry. FastAPI request logging
must be configured to exclude the `X-API-Key` header value.  
*Source: Architecture Decision 2, Decision 5*

---

## Group 4 — Response Contract

**I-06 — All responses return structured JSON with a correct Content-Type header**  
Every response from the API — success, error, or rejection — must be a
valid JSON object. The `Content-Type: application/json` header must
accompany every such response without exception. A response with a JSON
body but a missing or incorrect content type silently breaks downstream
tool integrations.  
*Source: Requirements brief (structured output)*

**I-07 — A non-existent customer ID returns 404; a malformed customer ID returns 400**  
A lookup for a customer ID not present in the database must return
`404 Not Found`. A request carrying a customer ID that does not conform
to the defined format must return `400 Bad Request` before any database
interaction occurs. These are distinct cases: 400 means the request was
not understood; 404 means the request was understood but the record was
not found. Note: this invariant is contingent on OQ1 (customer ID
format) being resolved before implementation begins.  
*Source: Requirements brief (functional requirements), Architecture OQ1*

---

## Group 5 — Network

**I-08 — Postgres is reachable only from within the Compose internal network**  
The Postgres container must publish no ports to the host. It must accept
connections only from within the Compose internal network. FastAPI is
the only service that holds database credentials and the only service
that may connect to Postgres. Direct access from the host or any
external network must be structurally impossible, not merely
discouraged.  
*Source: Architecture Decision 1*

---

## Group 6 — Data Integrity

**I-09 — The seeded database must always contain at least one record for each risk tier**  
At all times after a successful boot, the database must contain at least
one `LOW`, one `MEDIUM`, and one `HIGH` tier record. A seed that omits
any tier makes end-to-end verification of the system's contract
impossible and means the API cannot demonstrate its full response range.  
*Source: Requirements brief (functional requirements)*

---

## Invariant Index

| ID | Group | Summary | Conditional |
|---|---|---|---|
| I-01 | Data Access | Only read operations permitted; DB user holds SELECT only | No |
| I-02 | Data Access | Data returned as fetched, no transformation | No |
| I-03 | Authentication | Valid API key required on every protected request; enforced at router level | No |
| I-04 | Authentication | No data returned to unauthenticated callers under any circumstances | No |
| I-05 | Information Security | API key never in logs, URLs, or any output | No |
| I-06 | Response Contract | All responses are JSON with correct Content-Type | No |
| I-07 | Response Contract | Non-existent customer returns 404; malformed ID returns 400 | Yes — awaits OQ1 |
| I-08 | Network | Postgres not reachable outside Compose network | No |
| I-09 | Data Integrity | Seeded database always contains all three risk tiers | No |