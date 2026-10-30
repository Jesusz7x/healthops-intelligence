# QA plan and evidence

## Test layers

| Layer | Evidence | Scope |
|---|---|---|
| API integration | `tests/test_healthops.py` (13 tests) | In-process HTTP-handler dispatch with temporary SQLite database: auth/cookies, authorization, patients, appointment validation/conflict/state transition, inventory movement, CSV rollback/formula escaping, reports, quality flags, staff/settings/user roles, audit, read-only profile, content-type and path traversal. |
| Data processing unit | `tests/test_quality.py` (2 tests) | Required fields, reserved demo email, age range, normalized possible duplicate names and duplicate IDs. |
| Frontend contract | `tests/test_frontend_contract.py` (3 tests) | Unique and referenced IDs, equal English/Spanish translation keys, all static UI translations, and same-origin asset links. |
| Static syntax | `node --check web/app.js`; `python3 -m py_compile api/*.py processing/*.py` | JavaScript parse and Python byte-compilation. |
| HTTP/browser E2E | Not run | Sandbox denies socket creation; no browser automation package. Visual/mobile/keyboard/assistive-technology review remains needed. |

## Negative cases exercised

Unauthenticated read, viewer write, viewer audit access, invalid age/email/date, naive timezone, duplicate scheduled staff/time, illegal appointment transition, negative stock, invalid CSV email and no-partial-import behavior, formula-like export cell, demotion of final admin, missing content type, static path traversal, and public read-only mutation.

## Defect found and fixed during QA

The first attempted integration suite bound a local socket and failed with `PermissionError` due to sandbox policy, before executing tests. The tests were revised to call the same request handler with in-memory streams; no application code was changed to fake a successful network bind. The revised suite passed. This proves route/persistence behavior but cannot validate actual socket transport or browser rendering.

No real-user or clinical safety claims are tested. The demo is not certified for healthcare use.
