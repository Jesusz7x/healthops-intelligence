# Installation and deployment / Instalación y despliegue

## Local setup

Prerequisite: Python 3.11+ with the standard `sqlite3` module. The provided Debian environment has Python 3.13 and SQLite 3.46 through Python. No dependencies need to be downloaded.

```sh
cd projects/07-healthops-intelligence
python3 api/server.py
```

Visit `http://127.0.0.1:8787`. Stop with Ctrl+C. The app binds to loopback, creates `data/healthops.sqlite3`, and seeds fictional records and local demo accounts on first run. Set `PORT=8790` to select another local port. Set `HEALTHOPS_DB=/path/to/a/new-demo.sqlite3` to use a separate database; do not point it at real data.

Run tests from the project folder:

```sh
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m py_compile api/*.py processing/*.py
```

Use a new `HEALTHOPS_DB` path when you need a fresh demo database. The app does not automatically erase databases. It never commits its runtime SQLite database to Git.

## Configuration

See `.env.example` for documented variable names; this project does not load `.env` automatically. Export variables in the shell before starting. No secret key is required because session keys are generated with the OS cryptographic random source and persisted only as digests.

## Public Render demonstration

The repo contains a free Render Blueprint in [`render.yaml`](../render.yaml). It selects the Python native runtime, pins Python `3.13.5`, runs `python3 api/server.py` without installing dependencies, binds the app to `0.0.0.0`, reads Render's assigned `PORT`, enables `HEALTHOPS_READ_ONLY=1` and `HEALTHOPS_SECURE_COOKIES=1`, and checks `GET /health`. The API health alias `/api/health` remains available.

A clean public database seeds only the fictitious read-only visitor account and synthetic operations records. In public mode, the backend accepts only that visitor's login, downgrades all sessions to `viewer`, rejects every data-write permission, and permits read-only access to the audit log. The login page explains the synthetic-data and non-clinical limits. The public demo credential is intentionally visible in README and the login screen; it is not a private secret. Do not reuse it. Do not upload a local SQLite database.

### Deploy after publishing this configuration

The GitHub repository must contain the updated Blueprint and code before Render can deploy it. Then open [Render Dashboard](https://dashboard.render.com/), choose **New → Blueprint**, connect/authorize the `Jesusz7x` GitHub account if prompted, select `Jesusz7x/healthops-intelligence`, review the Blueprint values, and create the service. Render assigns the public `onrender.com` URL after the service is created; no URL is claimed here before that happens. Render's official [first deploy guide](https://render.com/docs/your-first-deploy) describes this connection flow. The Blueprint uses no paid database or paid compute plan. Do not upgrade the plan, add paid services, or provide payment details for this showcase without explicit owner approval.

### Render Free limitations

Render Free web services currently spin down after 15 minutes without inbound traffic and may need about a minute to wake on the next request. Their local filesystem is ephemeral; the SQLite database, synthetic data, and sessions may be lost on spin-down, restart, or redeploy. The app reinitializes/seeds data on startup. Free web services cannot use persistent disks. Render provides 750 included Free instance hours per workspace per calendar month; service availability may be suspended after the included hours are consumed. This is a showcase/demo configuration, not production healthcare hosting. Review [current Free limitations](https://render.com/docs/free) before creating the service.

## Validation limits

This build sandbox denies local socket creation (`PermissionError: Operation not permitted`). The four subprocess tests for actual HTTP, HTTPS cookie flags, visitor login, protected paths, and assets are present but skip in this environment. The application has not yet been deployed, so no TLS/HTTPS response or public URL has been verified. Do not add a LIVE DEMO button to the portfolio until the real Render URL is active and its health/login/read-only checks pass. Browser visual, mobile, keyboard, and assistive-technology checks also remain outstanding.

Official references consulted 2026-10-30: [Render free services and filesystem limits](https://render.com/docs/free), [web service port binding and TLS termination](https://render.com/docs/web-services), [Blueprint YAML reference](https://render.com/docs/blueprint-spec), and [first-deploy tutorial](https://render.com/docs/your-first-deploy). These plan details can change; verify them again before deployment.
