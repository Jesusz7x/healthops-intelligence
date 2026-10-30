# REST API guide

Base path: `/api`. The same-origin Python server serves the UI and API. Public health probes are available at both `/health` (Render check) and `/api/health`. JSON is UTF-8. Mutating routes require `Content-Type: application/json`; patient CSV import requires `text/csv`. Browser requests use an HttpOnly, SameSite=Strict session cookie. Error shape: `{"error":{"message":"..."}}`. See [openapi.yaml](openapi.yaml) for the OpenAPI 3.1 contract.

## Authentication and roles

`POST /auth/login`, `POST /auth/logout`, `GET /auth/me`. Session lifetime is 8 hours. Seeded local demo accounts and roles are in the README. Roles: `admin`, `operations`, `clinical`, `inventory`, and `viewer`. Public read-only mode seeds a visitor on a clean database, rejects other logins, maps every session to viewer, blocks backend write actions, and permits read-only access to `/audit`.

## Modules

| Route | Method | Purpose / permission |
|---|---|---|
| `/health` | GET | Health/status probe; public |
| `/dashboard`, `/reports`, `/data-quality` | GET | Aggregates, operational trend, anomaly flags, baseline, quality findings; authenticated |
| `/patients` | GET, POST | Search/list and create; create roles: admin, operations, clinical |
| `/patients/{id}` | PATCH | Update name, demo email, age, status; admin, operations, clinical |
| `/appointments` | GET, POST | List/create; create roles: admin, operations, clinical |
| `/appointments/{id}` | PATCH | Transition a scheduled appointment to completed, cancelled, or no-show |
| `/staff` | GET, POST | Staff directory; create admin only |
| `/users` | GET | Demo account roles; admin only |
| `/users/{id}` | PATCH | Change role/active flag; admin only; keeps an active admin |
| `/inventory` | GET, POST | List/create stock item; create roles: admin, inventory |
| `/inventory/{id}/movements` | GET, POST | Read stock ledger / add receipt or issue; write roles: admin, inventory |
| `/import/patients` | POST | Atomic CSV import, at most 1,000 rows; admin, operations |
| `/export/patients.csv` | GET | CSV export with spreadsheet-formula escaping; authenticated |
| `/audit` | GET | Last 200 audit rows; admin locally, read-only visitor in public mode |
| `/settings` | GET, PATCH | Demo facility name and threshold; write admin only |

The API does not expose patient deletion. Deactivation and appointment status transitions retain history. Paging is currently capped at 500 records per list, and audit at 200. Rate limits, request-size limits, input checks, same-origin restrictions and generic server errors are applied in the local handler.
