# Customer Risk API

## Overview

A read-only HTTP API that serves customer risk profiles from a Postgres database. A single FastAPI container handles all requests: it serves a static HTML lookup UI at `/`, a health endpoint at `/health`, and an authenticated customer endpoint at `/customer/{id}`. A Postgres container holds the data and is never reachable outside the internal Docker network. All customer lookups require a shared API key sent in the `X-API-Key` request header.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine + Compose plugin (Linux)
- A terminal (bash, zsh, PowerShell, or equivalent)

---

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd customer-risk-api
   ```

2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

3. Open `.env` and set `API_KEY` to a value of your choice:
   ```
   API_KEY=your-secret-key-here
   ```

4. Start the stack:
   ```bash
   docker compose up -d
   ```

5. Wait approximately 20 seconds for Postgres to initialise and the API to become ready.

6. Open [http://localhost:8000/](http://localhost:8000/) in a browser.

---

## Using the UI

1. Enter a customer ID (e.g. `CUST-001`) in the input field.
2. Click **Look Up** or press Enter.
3. The result panel displays the customer's risk tier (colour-coded: green for LOW, amber for MEDIUM, red for HIGH) and their risk factors as a bulleted list.
4. An unknown ID returns a "Customer not found" message. An empty input is caught before any network request is made.

---

## Using the API directly

**Health check (no authentication required):**
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

**Customer lookup (API key required):**
```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/customer/CUST-001
# {"customer_id":"CUST-001","risk_tier":"LOW","risk_factors":["stable_income"]}
```

**404 — customer not found:**
```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/customer/NOTEXIST
# HTTP 404  {"detail":"Customer not found"}
```

**401 — missing or invalid API key:**
```bash
curl http://localhost:8000/customer/CUST-001
# HTTP 401  {"detail":"Unauthorized"}
```

---

## Resetting the database

To wipe the database volume and re-seed from scratch:

```bash
docker compose down -v
docker compose up -d
```

The `-v` flag removes the named volume. The next `up` runs the init script and reloads all 15 seed records.

---

## Known limitations

- The API key is injected into the browser UI at startup and is visible in browser network traffic and developer tools. Do not use a sensitive key in this setup.
- There is no per-user authentication — any caller with the key has full read access.
- This system is a training demo and is not production-hardened: no TLS, no rate limiting, no audit logging, and no secrets management beyond a local `.env` file.

---

## Environment variables

| Variable | Used by | Description | Example |
|---|---|---|---|
| `API_KEY` | FastAPI | Shared secret required in the `X-API-Key` header on every customer request | `change-me-before-use` |
| `POSTGRES_USER` | Postgres, FastAPI | Database username | `riskuser` |
| `POSTGRES_PASSWORD` | Postgres, FastAPI | Database password | `changeme` |
| `POSTGRES_DB` | Postgres, FastAPI | Database name | `riskdb` |
| `POSTGRES_HOST` | FastAPI | Hostname of the Postgres service (Docker Compose service name) | `postgres` |
| `POSTGRES_PORT` | FastAPI | Port Postgres listens on | `5432` |

All six variables must be present in `.env` before running `docker compose up`.

---

## Seed data

The database is pre-loaded with 15 records — 5 per risk tier.

| Customer ID | Risk tier | Risk factors |
|---|---|---|
| CUST-001 | LOW | stable_income |
| CUST-002 | LOW | long_account_tenure, no_missed_payments |
| CUST-003 | LOW | stable_income, low_credit_utilisation, no_missed_payments |
| CUST-004 | LOW | long_account_tenure, consistent_repayment_history |
| CUST-005 | LOW | stable_income, no_missed_payments |
| CUST-006 | MEDIUM | recent_address_change, moderate_credit_utilisation |
| CUST-007 | MEDIUM | occasional_late_payment, short_account_tenure |
| CUST-008 | MEDIUM | moderate_credit_utilisation, recent_address_change, new_credit_account |
| CUST-009 | MEDIUM | occasional_late_payment, moderate_credit_utilisation |
| CUST-010 | MEDIUM | recent_employer_change, short_account_tenure, moderate_credit_utilisation |
| CUST-011 | HIGH | multiple_missed_payments, high_credit_utilisation |
| CUST-012 | HIGH | sanctions_watchlist_match, identity_verification_failed, multiple_missed_payments |
| CUST-013 | HIGH | high_transaction_volume, multiple_missed_payments, recent_default, account_under_review |
| CUST-014 | HIGH | identity_verification_failed, high_transaction_volume, sanctions_watchlist_match |
| CUST-015 | HIGH | multiple_missed_payments, high_credit_utilisation, recent_default |
