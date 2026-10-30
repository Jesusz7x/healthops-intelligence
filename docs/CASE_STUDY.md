# Case study: HEALTHOPS INTELLIGENCE

## Problem

Small care facilities can have fragmented operational information across appointment lists, staff rosters, and stock sheets. This project explores a compact way to bring fictional operational records together and show basic trends while keeping data-quality findings and auditability visible.

## Scope and safety boundary

This is a learning/demo product using only generated data. It does not contain diagnoses, medications, treatment plans, or real patient information; it is not clinically validated or certified. The goal is to demonstrate software design, not to make care decisions.

## Design and implementation

A same-origin browser client talks to a Python REST-style handler. SQLite enforces relational links and stock/age/state constraints. The backend handles role checks, validation, audit events, and imports; a Python processing module identifies missing/invalid/duplicate-looking CSV fields. The browser interface includes dashboard, patients, appointments, staff/account roles, inventory, reports, audit, settings, language and theme controls.

Security choices include salted PBKDF2 password hashes, hashed random session tokens, HttpOnly/SameSite cookies, role checks on every protected action, parameterized SQL, request-size limits, upload row caps, all-or-nothing import, safe CSV export, audit rows, loopback-only default binding, and a read-only gate for remote binding.

## Data methods

- Trend: total appointment rows for the last 7 calendar days compared with the preceding 7 days; percentage change is omitted if the comparison period is zero.
- Experimental anomalies: daily count median absolute deviation (MAD), scaled by 1.4826; flag modified z-scores above 3.5 when MAD is nonzero. Flags are prompts for review, not errors or clinical risks.
- Demand baseline: trailing 28 calendar-day mean repeated across the following 7 days. It is deliberately a naive comparison baseline, not a trained forecasting model.
- Stock alert: quantity at or below the item's explicit reorder level.

## Verification and measured results

The implementation passed 23 non-socket checks: 16 API/request-handler checks, 2 deployment-config checks, 2 data-quality unit tests, and 3 frontend-contract tests; 4 real-HTTP subprocess integration checks are present but were skipped in this sandbox on Python 3.13.5/Node 20. JavaScript syntax and Python byte-compilation passed. The tests cover authentication, roles, state transitions, constraints, CSV rollback/formula escaping, audit/configuration, quality flags, and read-only mode. No performance benchmark or predictive-accuracy metric is claimed. The sandbox denied socket creation (`PermissionError: Operation not permitted`), so the new live HTTP checks could not execute here; real HTTP, visual/mobile/accessibility, and public deployment remain unverified.

## Decisions and next work

The requested Angular/TypeScript, Express/Node, and PostgreSQL stack could not be verified because the local package registry is inaccessible, Angular tooling is absent, and PostgreSQL server is not running. The working implementation instead favors Python standard library and SQLite, reducing install load and keeping the project runnable offline. Next steps are to validate the UI in a real browser; then decide whether to migrate the frontend to Angular and the REST host to Express, add a PostgreSQL repository/migrations, run transport-level tests, and deploy a read-only synthetic demo over HTTPS. Those tasks are not represented as complete.
