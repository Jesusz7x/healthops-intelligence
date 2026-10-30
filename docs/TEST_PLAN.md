# QA plan and evidence

## Test layers

| Layer | Evidence | Scope |
|---|---|---|
| API route and data integration | `tests/test_healthops.py` (16 tests) | Calls `dispatch_request()` with in-memory request/response streams and temporary SQLite data. Covers auth/cookies, authorization, patient and appointment validation, inventory movements, CSV rollback/formula escaping, reports, quality flags, staff/settings/user roles, audit, read-only mode, content type, and safe handling when a response client disconnects. It does not validate HTTP socket transport. |
| Real HTTP integration | `tests/test_http_server.py` (4 tests) | Launches `python api/server.py` as a subprocess on a dynamically selected local port. Exercises page/CSS/JS, login/session reuse, authenticated/unauthenticated API routes, role and Origin checks, process survival, and stderr for server exceptions. Runs where the environment permits local sockets; this sandbox denies socket creation, so the class is skipped here. |
| Data processing unit | `tests/test_quality.py` (2 tests) | Required fields, reserved demo email, age range, normalized possible duplicate names and duplicate IDs. |
| Frontend contract | `tests/test_frontend_contract.py` (3 tests) | Unique/referenced IDs, equal English/Spanish translation keys, static translations, and same-origin asset links. |
| Deployment config | `tests/test_render_config.py` (2 tests) | Checks pinned Python, free Blueprint plan, assigned-port entry point, read-only/security flags, and health-check path. |
| Static syntax | `node --check web/app.js`; `python3 -m py_compile api/*.py processing/*.py` | JavaScript parse and Python byte-compilation. |
| Browser E2E | Not run | No browser automation is available. Visual, mobile, keyboard and assistive-technology review remain needed. |

## Negative cases exercised

Unauthenticated read, viewer write, viewer audit access, invalid age/email/date, naive timezone, duplicate scheduled staff/time, illegal appointment transition, negative stock, invalid CSV email and no-partial-import behavior, formula-like export cell, demotion of final admin, missing content type, static path traversal, public read-only mutation, foreign Origin rejection (in real HTTP suite), and a disconnected response writer that must not trigger a second response attempt.

## HTTP lifecycle defect

The old handler overrode `BaseHTTPRequestHandler.handle()` and called `self.path` before the base request parser had populated it. The in-process tests manually assigned `path`, `command`, and `requestline`, so they hid this lifecycle defect. The application code now keeps the base `handle()` and dispatches through `do_GET`, `do_POST`, `do_PUT`, `do_PATCH`, and `do_DELETE` to `dispatch_request()`.

The four real-HTTP tests now exist and launch the actual entry point. In this sandbox both the socket probe and `python3 api/server.py` fail before listening with `PermissionError: [Errno 1] Operation not permitted`; the suite skips the socket tests for that explicit environment restriction. As a result, the reported `AttributeError` fix is supported by the corrected lifecycle and passing route tests but still requires HTTP verification outside this sandbox. It must not be described as live-HTTP verified yet.

No real-user or clinical safety claims are tested. The demo is not certified for healthcare use.
