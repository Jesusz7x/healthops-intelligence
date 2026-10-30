# HEALTHOPS INTELLIGENCE

**A fictional operations-intelligence demo for small healthcare facilities.** The system demonstrates an authenticated web application, role-aware REST endpoints, relational data, CSV workflows, transparent operational analytics, and audit records. Every included person, appointment, quantity, account, and metric is synthetic. This is not a clinical product, medical record system, or certified healthcare software.

## Current implementation

- Python 3.13 standard-library HTTP API and static web server.
- SQLite through Python's built-in `sqlite3`, with foreign keys, checks, indexes, and transaction handling.
- Bilingual English/Spanish responsive HTML, CSS, and JavaScript interface with light/dark themes.
- Password hashing with PBKDF2-HMAC-SHA256, random session tokens stored as hashes, HttpOnly/SameSite cookies, role checks, login throttling, and audit events.
- Dashboard, fictional patient registry, appointments, staff directory and demo account roles, stock movements, CSV import/export, data-quality checks, audit log, settings, daily trends, robust anomaly flags, and a simple demand baseline.
- Python quality-review CLI and 18 automated integration/unit and frontend-contract tests.

The first runnable version uses the standard library because Angular/Express packages are not installed and package-registry access is unavailable in the build environment. PostgreSQL is installed as a client, but no server is running. **Angular, Express, PostgreSQL, and browser-level end-to-end tests are not part of this verified version.** The REST contract is documented so those components can replace/extend the local adapter in a future stage. This limitation is not hidden or presented as completed work.

## Run locally

Requirements: Python 3.11 or newer. No pip install, Node build, PostgreSQL server, Docker, or paid service is required.

```sh
cd projects/07-healthops-intelligence
python3 api/server.py
```

Open `http://127.0.0.1:8787`. The service binds only to loopback by default. On first start it creates `data/healthops.sqlite3` and seeds fictional records. The database is ignored by Git.

### Demo accounts

All accounts use the local demo password `DemoHealthOps!2026`. Never reuse it outside this fictional local demo.

| Email | Role |
|---|---|
| `admin@healthops.local` | Administrator |
| `ops@healthops.local` | Operations |
| `clinical@healthops.local` | Clinical administration |
| `stock@healthops.local` | Inventory |
| `viewer@healthops.local` | Read only |

## Test

```sh
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m py_compile api/*.py processing/*.py
```

The 13 API integration tests dispatch requests in-process because this agent sandbox denies socket creation. The two data-quality tests exercise the Python analysis module, and three frontend-contract tests verify IDs, translations, and static asset links. These are real handler/database tests, but they do not replace a live HTTP/browser test.

## Main documents

- [Instalación y opciones de despliegue](docs/INSTALLATION.md)
- [Architecture](docs/ARCHITECTURE.md) and [data model](docs/DATA_MODEL.md)
- [OpenAPI contract](docs/openapi.yaml) and [API guide](docs/API.md)
- [User manual](docs/USER_GUIDE.md)
- [Security and privacy](docs/SECURITY.md)
- [Test plan](docs/TEST_PLAN.md)
- [Case study](docs/CASE_STUDY.md)
- [Technical decisions](docs/DECISIONS.md)

## Public demo safety

A remote bind is refused unless `HEALTHOPS_READ_ONLY=1`. In read-only mode every authenticated demo account is treated as viewer. For a public HTTPS reverse proxy, set `HEALTHOPS_HOST=0.0.0.0`, `HEALTHOPS_READ_ONLY=1`, and `HEALTHOPS_SECURE_COOKIES=1`. Do not expose the mutable local demo, put it behind plain HTTP, or upload a database with user-entered data. No public service has been deployed from this repository.

## License

MIT. The demo account names, records, and sample file are fictional and may be reused as sample data.
