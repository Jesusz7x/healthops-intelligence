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

## Public demonstration, if later authorized and hosted

A public URL is not deployed or verified. For a read-only demo behind a trusted HTTPS reverse proxy, set:

```sh
HEALTHOPS_HOST=0.0.0.0 HEALTHOPS_READ_ONLY=1 HEALTHOPS_SECURE_COOKIES=1 python3 api/server.py
```

Remote binding exits unless read-only mode is enabled. The reverse proxy must terminate HTTPS, forward only to the local app, restrict request sizes, and avoid recording cookie headers/request bodies. Use a fresh database containing only the bundled synthetic seed. Public accounts are downgraded to viewer. Do not publish an editable/admin demo or upload an owner database.

A hosted service must support persistent storage if records are expected to survive restarts. Free hosting tiers, storage retention, sleep behavior, and terms change frequently; no provider was selected or purchased. Do not add a credit card or deploy until reviewing the provider's current official terms and the security limits above. A production system should use managed PostgreSQL, HTTPS, secret management, backups, migrations, monitoring, account lifecycle, and a security/privacy review; those are outside this demo build.

## Blocked validation

The execution sandbox forbids opening sockets, and external package installation is unavailable. Therefore live browser access, actual port binding, reverse proxy, TLS, public deployment, and mobile visual checks were not performed. Tests invoke the handler in process and verify generated HTML/API responses against temporary SQLite.

## Prepared free demo target: Render (not deployed)

A safe, read-only Blueprint is in [`render.yaml`](../render.yaml). Render's official docs describe Python web services, require binding to `0.0.0.0` and the assigned `PORT`, and support a health-check path. The project already binds to `0.0.0.0` when configured, reads `PORT`, and exposes `/api/health`.

Render currently offers free web services, but they spin down after 15 minutes idle and may take about a minute to wake. Their free filesystem is ephemeral, so the SQLite database and sessions can reset on redeploy/restart/sleep. That's acceptable only for this read-only seeded demonstration, not for user-entered data. Render documents 750 free instance hours per workspace/month and says no payment method means services are suspended rather than billed for excess included usage. Account creation and linking a public GitHub repo are still needed; no service has been created here and no payment details were added. Review the current limits before connecting an account.

Official references consulted 2026-10-30: [Render free services and filesystem limits](https://render.com/docs/free), [web service port binding and TLS termination](https://render.com/docs/web-services), [Blueprint YAML reference](https://render.com/docs/blueprint-spec), and [first-deploy tutorial](https://render.com/docs/your-first-deploy). These plan details can change; verify them again before deployment.
