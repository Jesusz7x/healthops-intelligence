# Security and privacy

## Implemented controls

- Fictional-only records; emails are restricted to reserved `.invalid` for patient entry/import.
- Passwords stored as PBKDF2-HMAC-SHA256 digests with random salts; sessions use random 256-bit URL-safe values while only SHA-256 digests are persisted.
- HttpOnly, SameSite=Strict cookie; 8-hour expiry. Set `HEALTHOPS_SECURE_COOKIES=1` behind HTTPS.
- Role checks in the API, administrator-only account-role changes, and protection against removing/demoting the last active administrator.
- Login throttling per source address, bounded request bodies and CSV row counts, strict content types, cross-origin write rejection, no permissive CORS.
- SQLite parameter binding, foreign keys, CHECK constraints and transactionally recorded audit events.
- Spreadsheet formula escaping in CSV export; CSV import is all-or-nothing and never changes its source upload.
- Content Security Policy, `nosniff`, no-store API responses, generic errors, and request logs without payloads/cookies/patient data.
- Remote bind refused unless `HEALTHOPS_READ_ONLY=1`; in that mode every logged-in account receives viewer permissions.
- `.gitignore` excludes SQLite database files, `.env`, bytecode, and test artifacts.

## Limits and safe use

This is a portfolio demo, not a production security review or healthcare compliance assessment. The seeded demo password is intentionally public and must not protect real data. There is no password reset, MFA, account invitation lifecycle, external identity provider, database backup/restore workflow, retention policy, TLS termination, reverse-proxy hardening, distributed rate limiting, dependency scanner, or independent penetration test. Do not enter protected health information or expose the mutable local instance to the Internet. A public deployment must use synthetic seed data, read-only mode, HTTPS, and an isolated database.
