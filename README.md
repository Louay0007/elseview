# Elseview — Tunisian research platform — P01

**Brand:** Elseview — See what you’re missing.

## Elseview naming

- Compose project and image prefix: `elseview`.
- Containers: `elseview-frontend-1`, `elseview-backend-1`, `elseview-database-1`, `elseview-cache-1`.
- Active volumes: `elseview_postgres_data` and `elseview_private_data`.
- Databases: `elseview_app` and the guarded `elseview_test`.
- Packages: `elseview-backend` and `elseview-frontend`; backend logger: `elseview`.
- Workspace path stays `/Users/user/Workspace/startup-act/`; internal service DNS names and `/api/v1` routes stay unchanged.

The existing P01 installation was migrated by copying stopped volumes and renaming the copied databases. Original `research-platform_postgres_data` and `research-platform_private_data` volumes remain as rollback copies, not active storage. Private dumps and the before/after data comparison are in the ignored directory `/Users/user/Workspace/startup-act/.tools/elseview-backup/`. Do not publish backups or delete them before confirming recovery needs.

On this migrated installation, Compose may warn that the adopted Elseview volumes were not originally created by Compose. Their explicit names intentionally select the preserved data. Fresh installations create these volumes normally; no destructive reset is required.

Implemented: four-container development foundation, React status page, FastAPI health API, PostgreSQL migration, synthetic fixture, authenticated Valkey, and automated tests.

**Not implemented:** authentication/research APIs (P02 onward), job processing (P03), cloud calls (P10), participant data or payments. No auth bypass or dummy research endpoints exist. Live AI and job-runner configuration fail closed in P01.

## Prerequisites

A working Docker engine and Docker Compose, plus Python 3 to generate development secrets. Python 3.12 is provided inside the backend image. Containers support ARM64; base images are pinned to verified manifest digests. Python dependencies are hash-locked for cross-platform installation. Frontend React/Vite dependencies have an npm lockfile.

## Start development

Run once; the setup command refuses to overwrite existing credentials:

```sh
python3 /Users/user/Workspace/startup-act/scripts/setup_dev.py
/Users/user/Workspace/startup-act/scripts/dev build
/Users/user/Workspace/startup-act/scripts/dev up -d database cache backend
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m alembic upgrade head
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m app.seed
/Users/user/Workspace/startup-act/scripts/dev up -d frontend
```

Visit `http://localhost:8080`. Only this loopback frontend port is published. The frontend proxies `/api` to FastAPI. Database and cache do not publish host ports.

Backend readiness stays 503 until the explicit migration is applied. Startup performs no DDL and does not seed. Repeating the seed command preserves the same single synthetic fixture. On an existing setup, skip secret generation. Do not use `down -v` unless intentionally deleting all development data.

The wrapper always uses the same environment file and base/development Compose pair, independently of your working directory. Run `scripts/dev up -d --build frontend` after changing frontend source; backend changes reload from a bind mount. The React page is only a P01 connectivity diagnostic, not the research product interface.

## Tests

The full guarded suite uses the separate `elseview_test` database. It migrates/reset that test schema; never point the runner at valuable data.

```sh
/Users/user/Workspace/startup-act/scripts/dev exec -T -e TEST_ALLOW_RESET=elseview_test backend python -m app.test_runner -q --cov=app --cov-report=term-missing
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m ruff check app migrations tests
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m ruff format --check app migrations tests
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m pip check
python3 /Users/user/Workspace/startup-act/scripts/validate_blueprint.py
```

Plain pytest without the explicit DB guard runs unit/API tests and clearly skips real-DB cases. It is not equivalent to the full suite. Test fixtures deny external Python socket connections; the only explicitly allowed network is the selected test PostgreSQL address. No cloud client or provider call is implemented, and tests use an in-memory HTTP mock. This is a test safeguard, not a production egress firewall.

## Foundation contracts

- `GET /api/v1/health/live`: 200 `{"status":"ok"}` without a database dependency.
- `GET /api/v1/health/ready`: 200 `{"status":"ready"}` only for the expected migration/table; otherwise sanitized 503.
- Every response has a validated/generated UUID request ID. Errors never include raw input or exception details.
- Body limits enforce actual received bytes, not just Content-Length.
- Logs contain allowlisted event metadata, not arbitrary messages, headers, query strings, bodies or secrets. Uvicorn access logs are disabled.
- The runtime DB role has DML grants, no schema CREATE permission; migration owner and test owner are separate.
- Backend runs as UID/GID 10001. Private volume belongs to that user.
- Settings reject unknown owned environment names, invalid modes/origins, missing/weak secrets and unsafe test database configuration. Unrelated operating-system variables are ignored.
- `.env` is generated with mode 0600 and ignored. Never paste it, publish rendered Compose with resolved secrets, or commit it.

## Scope and operational cautions

The base Compose file is a local development foundation too, not a production deployment. Database owner/test credentials are available in the backend development container so explicit migration/test commands work. Before production, remove those credentials from the runtime, add P02 authentication, real secret management, TLS/public-domain configuration, reviewed retention and recovery controls.

Migration `001_foundation` contains only `app_metadata` for synthetic P01 fixture verification plus Alembic tracking. It is not a research schema. Destructive test downgrade is permitted only on the dedicated guarded test database.

The container development target includes test dependencies intentionally. A smaller production-only backend image can be introduced when production deployment is in scope. No fifth worker/storage/model service is required.

## Evidence

See `/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md` for actual test/build results and limits. The implementation roadmap remains `/Users/user/Workspace/startup-act/BACKEND_IMPLEMENTATION_PLAN.md`.
