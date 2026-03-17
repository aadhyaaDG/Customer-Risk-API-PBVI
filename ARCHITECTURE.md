# ARCHITECTURE.md
## Customer Risk API
**Version:** 1.0  
**Classification:** Training Demo System  
**Architecture Decision:** A — Single FastAPI Container + Postgres  

---

## 1. Problem Framing

### What this system solves

Internal operations staff currently answer risk tier questions by running
ad-hoc SQL directly against a Postgres database. This creates three
concrete problems: there is no enforced access boundary (anyone with
database credentials can query anything), there is no audit surface (no
record of who looked up what), and there is no stable data contract
(downstream tools cannot integrate against raw SQL results).

This system solves those three problems by placing a controlled,
authenticated HTTP interface in front of the data. All reads flow through
one chokepoint. The database is no longer directly reachable from outside
the service network. Every query is mediated by an interface with a
defined contract.

### What this system explicitly does not solve

- It does not compute or reassess risk. All risk tiers and factors are
  pre-populated. The system is a read surface, not a scoring engine.
- It does not manage users, roles, or per-user access. There is one API
  key. Identity of the caller is not tracked beyond key validity.
- It does not produce an audit log. Requests are not persisted. This is
  a known gap acceptable for the demo scope (see Open Questions).
- It does not harden for production. TLS, rate limiting, secrets
  rotation, and observability are all out of scope.

---

## 2. Five Key Design Decisions

---

### Decision 1: Single FastAPI container serves both the UI and the API

**What was decided**  
One FastAPI process handles all responsibilities: serving the static HTML
page at `GET /`, answering API queries at `GET /customer/{id}`, and
exposing a health check at `GET /health`. Postgres runs as a second
container. Two containers total. FastAPI's port (8000) is published
directly to the host.

**Rationale**  
Minimum moving parts. For a demo system with a fixed scope, a single
application container is the simplest topology to reason about, debug,
and start. There is no proxy layer, no additional config file, and no
additional failure surface. FastAPI's `StaticFiles` mount handles static
file serving natively — no external tool is required.

**Alternatives rejected**

- *Nginx + FastAPI (Architecture B):* Adds a third-party process, a
  `nginx.conf` file, and a proxy hop for a demo system with no
  concurrent load or CDN requirements. The security benefit of Nginx as
  a network boundary is real but exceeds the scope of a training demo.
  Rejected in favour of simplicity.

- *Architecture C (Jinja2 key injection):* Introduces a template
  rendering dependency and bakes the API key into page source on every
  render. Rejected because key visibility in page source is a worse
  security posture than user-entered key, even in a demo context.

**Challenge**  
> FastAPI is now the sole published container. The API authentication
> logic is the only barrier between the network and the database. A
> route added without the `Depends(verify_api_key)` decorator is
> silently unauthenticated and immediately reachable from outside the
> stack.

**Assessment: Valid. Accepted with a mitigation obligation.**  
This is the primary security trade-off of Architecture A versus B. The
mitigation is to apply the authentication dependency at the router
level, not per-route, so all routes under `/api/` inherit it by default.
This must be enforced in code review. The risk is real and must be
documented explicitly.

---

### Decision 2: API key transmitted in `X-API-Key` request header, validated in a FastAPI dependency

**What was decided**  
All requests to `/customer/{id}` must carry a valid API key in the
`X-API-Key` HTTP header. Validation is implemented as a reusable FastAPI
`Depends()` function injected into every protected route. Requests
without a valid key receive a `401 Unauthorized` response. The key is
stored as an environment variable, loaded at startup, held in memory.
The UI user enters the key in a form field; it is never rendered into
the HTML page.

**Rationale**  
Headers are not logged by default in access logs, are not stored in
browser history, and are not echoed in referrer chains. URL query
parameters fail all three of these properties. The `Depends()` pattern
in FastAPI makes auth a declarative, per-route obligation rather than
something that must be remembered inside each handler — reducing the
surface for accidental omission.

**Alternatives rejected**

- *API key as a query parameter (`?api_key=...`):* Exposes the key in
  access logs and browser history. Rejected on the implied constraint
  that secrets must not travel in URLs.

- *Basic Auth:* Functionally equivalent in security properties for this
  scope, but introduces browser-native credential prompts that interact
  poorly with the vanilla JS UI. Rejected for UX consistency.

- *Key injected into page source at startup (Architecture C pattern):*
  Makes the key visible in browser page source and developer tools to
  anyone who can load the UI. Rejected — user-entered key is a strictly
  better posture even at demo scope.

- *No authentication:* Violates an explicit functional requirement.
  Rejected.

**Challenge**  
> A single static key in an `.env` file is not meaningfully different
> from no authentication in a demo context. Anyone who has the key has
> full access; there is no rotation, no expiry, no per-user key. The
> security value is largely theatrical.

**Assessment: Valid observation, rejected as a blocker.**  
The challenge correctly identifies that a single shared key is a weak
auth model. It is, however, the model the brief specifies. The system
implements the contract correctly and structurally. Noting this
limitation explicitly in Open Questions is the appropriate response, not
adding key management scope that the brief excludes.

---

### Decision 3: Postgres initialised via `init.sql` mounted into `/docker-entrypoint-initdb.d/`; seed data uses `ON CONFLICT DO NOTHING`

**What was decided**  
Database schema creation and seed data insertion are handled by a single
`init.sql` file. The official Postgres Docker image executes all `.sql`
files in `/docker-entrypoint-initdb.d/` on first container start. Seed
inserts use `ON CONFLICT DO NOTHING` to ensure the script is safe to
re-run against an already-seeded database.

**Rationale**  
The `/docker-entrypoint-initdb.d/` convention requires zero custom
tooling — no migration runner, no separate init container, no Makefile
target. It is executed by the image itself. `ON CONFLICT DO NOTHING`
makes the operation idempotent: `docker compose up` against an existing
volume does not duplicate records or fail with a key violation.

**Alternatives rejected**

- *Alembic or another migration tool:* Correct for production, where
  schema evolution matters. For a read-only demo with a fixed schema,
  this adds a dependency and an entrypoint step with no benefit.
  Rejected.

- *Seed data in a separate Python script run as an init container:*
  Adds a third container, an execution ordering dependency, and Python
  startup time for something SQL handles natively. Rejected.

- *No idempotency guard (plain `INSERT`):* Fails on second `docker
  compose up` against a live volume with a primary key violation.
  Rejected.

**Challenge**  
> `init.sql` only runs on first volume creation. If the schema needs to
> change during development, the developer must destroy the volume
> manually (`docker compose down -v`). This is a sharp edge that isn't
> documented anywhere.

**Assessment: Valid. Accepted as a known limitation.**  
This is a genuine operational footgun for anyone iterating on the
schema. It must be documented explicitly in `README.md` under a
"Resetting the database" section. This does not change the architectural
decision but generates a documentation obligation.

---

### Decision 4: FastAPI entrypoint polls Postgres with `pg_isready` before starting Uvicorn

**What was decided**  
The FastAPI container uses a shell script as its `CMD` entrypoint. Before
launching `uvicorn`, the script loops on `pg_isready -h db -U $POSTGRES_USER`
with a short sleep interval and a maximum retry count. Uvicorn starts
only after Postgres confirms it is accepting connections.

**Rationale**  
Docker Compose `depends_on` with `condition: service_started` only
confirms the container process has started — not that Postgres is ready
to accept connections. Postgres initialises asynchronously after the
process starts. Without a readiness check, the FastAPI container
attempts its first connection during startup and fails non-deterministically
depending on host machine speed. The `pg_isready` loop is the minimal
correct solution: it uses a tool already present in standard Postgres
client packages, requires no additional dependencies, and resolves the
race definitively.

**Alternatives rejected**

- *`depends_on: condition: service_healthy` with a Postgres healthcheck:*
  Correct and clean, but requires adding a `healthcheck` block to the
  Postgres service in `docker-compose.yml`. Both approaches work; the
  entrypoint script was chosen because it makes the boot behaviour
  explicit in one place rather than split between the compose file and
  the container definition.

- *Relying on application-level retry logic in psycopg2:* Pushes
  infrastructure concerns into application code. FastAPI's startup
  event would need to catch connection errors and retry — this is
  the wrong layer for what is fundamentally a boot-ordering problem.
  Rejected.

- *`restart: on-failure` on the FastAPI service:* Masks the root cause.
  The container crashes, Docker restarts it, eventually it connects.
  This works in practice but produces noisy logs and is indistinguishable
  from a genuine repeated crash. Rejected.

**Challenge**  
> The `pg_isready` polling loop is shell script logic that needs a
> timeout and error handling. If Postgres never becomes ready (e.g. a
> volume permission error), the FastAPI container hangs indefinitely
> with no clear signal to the operator.

**Assessment: Valid. Mitigated by design.**  
The loop must include a maximum retry count and exit with a non-zero
code on exhaustion. This causes the FastAPI container to exit, which
Compose surfaces as a stopped service — visible and actionable. The
script must not loop infinitely. This is an implementation obligation
that must be enforced in code review.

---

### Decision 5: Single `.env` file supplies all secrets and configuration; no secrets are present in any image layer

**What was decided**  
All secrets (`POSTGRES_PASSWORD`, `API_KEY`) and environment-specific
configuration (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_HOST`) are
defined in a single `.env` file at the project root. Docker Compose
loads it automatically. The `.env` file is listed in `.gitignore` and
is never `COPY`-ed in any `Dockerfile`. A `.env.example` file with
placeholder values is committed to the repository.

**Rationale**  
Baking secrets into image layers — even via `ARG`/`ENV` in a Dockerfile
— persists them in the image's layer history and makes them extractable
with `docker image history`. Runtime injection via `.env` means the
image contains no credentials at any point in its lifecycle. The
`.env.example` pattern gives new developers the correct file shape
without committing real values.

**Alternatives rejected**

- *Hardcoding credentials in `docker-compose.yml`:* Commits secrets to
  version control. Rejected immediately.

- *Docker secrets (Swarm feature):* Correct for production orchestration.
  Not available in plain Compose without Swarm mode. Rejected as out of
  scope.

- *Separate `.env` files per service:* Adds no security benefit here and
  fragments configuration management. Rejected for simplicity.

**Challenge**  
> The `.env` file sits on the developer's filesystem in plaintext. If
> the project directory is ever compressed, synced, or accidentally
> committed, the credentials travel with it. `.gitignore` is not a
> security control.

**Assessment: Valid. Accepted as a scope boundary.**  
This is a real risk, and the brief explicitly lists secrets management
at scale as out of scope. The `.gitignore` entry, the `.env.example`
pattern, and a README warning are the appropriate mitigations within the
brief's constraints. A production system would use a secrets manager.
This system documents the gap rather than pretending it doesn't exist.

---

## 3. Key Risks

**R1 — Auth bypass via missing `Depends()` on a new route**  
FastAPI does not enforce authentication globally by default. In
Architecture A, FastAPI is the published container — a route added
without the auth dependency is immediately reachable from the host.
Mitigation: apply the dependency at the router level, not per-route,
so all routes under `/customer/` inherit it by default. This is the
highest-priority implementation obligation in this architecture.

**R2 — Internal error detail leaking through the API response**  
psycopg2 exceptions carry database internals — table names, column
names, constraint names — in their string representations. If exceptions
are not caught and sanitised before the response is constructed, these
details surface to the caller. Mitigation: a FastAPI exception handler
must catch all unhandled exceptions and return a generic 500 with no
internal detail. This must be implemented explicitly and tested.

**R3 — FastAPI serves both UI and API from the same process**  
A crash, memory pressure, or slow startup in the API layer also takes
down the UI. There is no separation of failure domains. For a demo
system this is acceptable, but it means a single unhandled exception
in a route handler can render the entire stack unresponsive until the
container restarts.

**R4 — Volume state masking schema changes during development**  
As noted under Decision 3, `init.sql` only runs on first volume
creation. A developer who modifies the schema and restarts the stack
without `docker compose down -v` will be running against the old schema.
Mitigation: document the reset procedure in `README.md` and add a
visible warning comment to `init.sql`.

---

## 4. Key Assumptions

**A1** — The API key is pre-shared with operations staff through an
out-of-band channel (e.g. told to them by a system administrator). The
system has no mechanism to distribute or display the key to users. Users
enter it manually into the UI on each session.

**A2** — The network on which the stack runs is trusted. The UI does not
enforce HTTPS. Credentials and responses travel in plaintext. This is
acceptable only because the system is assumed to run on a local or
internal network, not on the public internet.

**A3** — `customer_id` values in the seed data are sufficient to
demonstrate all three risk tiers. No real customer data is present at
any point.

**A4** — A single Postgres instance with no replication, no backup, and
no connection pooling is sufficient for the demo workload. There is no
concurrency requirement.

**A5** — The developer running the system has Docker Desktop or Docker
Engine with Compose V2 installed. No other toolchain is required.

---

## 5. Data Model

### Entity: `customer_risk_profile`

The single first-class entity in the system. Each row represents one
customer's assessed risk state. The system does not model customers
independently from their risk profile — there is no separate `customer`
table because the system has no need for customer attributes beyond what
drives the risk assessment.

| Column | Type | Description |
|---|---|---|
| `customer_id` | `VARCHAR(50) PRIMARY KEY` | Externally assigned identifier. The format is not generated by this system. |
| `risk_tier` | `VARCHAR(10) NOT NULL` | One of `LOW`, `MEDIUM`, or `HIGH`. Constrained by a `CHECK` constraint. |
| `risk_factors` | `TEXT[] NOT NULL` | Ordered array of human-readable strings describing what drove the tier assessment. May be empty for LOW tier records but must not be null. |
| `assessed_at` | `TIMESTAMPTZ NOT NULL` | Timestamp of when the risk tier was last assessed. Set at seed time; not updated by this system. |

### Entity: `api_key` (runtime, not persisted)

Not a database table. The API key is a single string value held in the
FastAPI application's memory, loaded from the `API_KEY` environment
variable at startup. It is included here as a first-class entity because
it is the authentication boundary of the system. There is no key
rotation, no key identifier, and no key metadata. The value is either
valid or it is not.

---

## 6. Open Questions

**OQ1 — `customer_id` format is unspecified**  
The brief does not define whether customer IDs are integers, UUIDs,
prefixed strings, or something else. This matters for: input validation
(a malformed ID should return `400`, not `404`), URL path design, and
column type selection. *Phase 3 must define a `customer_id` format
before implementation begins.*

**OQ2 — How does the UI operator obtain the API key?**  
The system has no key distribution mechanism. The UI requires the user
to enter the key manually on each session. There must be a channel
through which the key is communicated to staff. This is an operational
process gap, not a code gap — but it must be acknowledged in `README.md`.

**OQ3 — Should request activity be logged?**  
The current design produces no audit trail. The original problem
statement calls out "bypasses access controls" as a concern — but the
related concern of "no record of who looked up what" is also present
and not addressed. FastAPI access logs provide IP and timestamp but not
customer ID or key identity. Whether this is acceptable for the demo
scope should be confirmed before Phase 3.

**OQ4 — How many seed records, and what is the ID space?**  
"Representative records covering all three tiers" is ambiguous. Three
records is technically compliant. A realistic test set probably requires
10–20. The ID format decision (OQ1) determines what the IDs look like.
This must be resolved before `init.sql` is written.

**OQ5 — Is the startup window during FastAPI boot acceptable?**  
Between `docker compose up` and FastAPI passing its `pg_isready` checks,
any API request will fail with a connection error. For a demo started
and immediately used, this window may produce confusing errors. Whether
a friendlier holding response or a startup health endpoint is needed
should be confirmed before Phase 3.