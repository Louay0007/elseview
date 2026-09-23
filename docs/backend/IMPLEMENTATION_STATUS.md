# Elseview — Implementation status

**Brand:** Elseview — See what you’re missing.

## Elseview brand cutover — September 23, 2026

- Applied the name and exact tagline to all product/planning Markdown files, React heading and browser metadata, FastAPI metadata, package identities and the backend logger.
- Renamed the Compose project to `elseview`; four active containers now use that prefix. Active PostgreSQL/private-file volumes use `elseview_*` names.
- Copied volumes only after stopping the original services, preserving original volumes as rollback copies. Renamed databases in the copied volume to `elseview_app` and `elseview_test`; updated bootstrap SQL, test guards, DSNs and instructions consistently.
- Compared application metadata rows, including creation timestamps, before/after cutover: exact match. No application schema change was needed; migration remains `001_foundation`.
- Post-cutover full test run: **96 passed, zero skipped; 90% coverage**. Added branding and Compose naming assertions. Frontend production bundle built; live frontend title/tagline and proxied readiness checked.
- Internal service names, health response contracts, application roles, fixture identifiers and workspace directory remain stable. No new containers, features or cloud calls were introduced.

Original P01 validation below is historical evidence; the 96-test cutover result above is the newer result.

## P01 — Development foundation

**Implemented and validated September 23, 2026.** No git commit reference exists: this workspace is not a Git repository. P02–P19 remain unimplemented.

### Delivered

- Python 3.12 FastAPI app factory/lifespan, safe errors, bounded request middleware, request IDs, safe structured logs, explicit configuration policy.
- Four Compose services with loopback-only frontend, nonroot backend, private PostgreSQL/cache, persistent database/private-file volumes and health checks.
- Minimal React/Vite status page and production static/Caddy frontend target; no research UI claimed.
- Hash-pinned Python lockfile resolved across platforms, npm lockfile, pinned base-image manifest digests.
- Separate runtime/migration/test PostgreSQL roles and databases.
- Explicit Alembic revision `001_foundation`; synthetic-only metadata table and idempotent `p01_demo` fixture.
- Guarded real-PostgreSQL test runner, mocked-provider and deterministic fixtures, network-denying unit harness, Compose/config/schema/API tests.
- Safe one-time secret generator and consistent `scripts/dev` wrapper.

### Observed validation

- Full container suite: **95 passed, zero skipped**, including real PostgreSQL migration downgrade/upgrade/repeat, constraints, JSON round-trip, rollback, readiness revision checks, explicit seed idempotency, and two app boots with no startup SQL/seed.
- Coverage: **90% overall**, `app/db.py` 100%, `app/main.py` 98%, `app/config.py` 95%. Lower CLI coverage is disclosed; seed/test-runner CLIs were also executed as actual container commands.
- Ruff lint and formatting passed.
- Backend `pip check`: no broken requirements.
- Development frontend and backend images built successfully; production frontend target also built successfully.
- Live frontend `/api/v1/health/ready` returned `{"status":"ready"}`.
- PostgreSQL runtime role probe: user `app`, database `elseview_app`, schema CREATE privilege **false**.
- Authenticated cache ping returned PONG.
- Backend UID/GID verified as 10001.
- Backend restarted: readiness recovered and synthetic fixture count remained exactly 1.
- Compose resolved exactly `frontend`, `backend`, `database`, `cache`; DB/cache have no published host ports.

Commands and safe replay instructions are in `/Users/user/Workspace/startup-act/README.md`. Raw local build/test logs are ignored under `/Users/user/Workspace/startup-act/.tools/`; no secrets are copied into this report.

### Issues caught and corrected during validation

- First platform-specific Python lock omitted Linux-only greenlet dependency; regenerated universal hash lock and rebuilt Linux ARM64 successfully.
- Valkey CLI health check needed REDISCLI_AUTH for this pinned version; corrected and verified authenticated health.
- Tests needing root infrastructure fixtures initially lacked container mounts; added read-only development mounts, not extra services.
- Test fixture environment expectation aligned with development-mode defaults; full suite rerun.

### Remaining scope/limits

No auth system, study data models, jobs, live cloud LLM or payments are enabled. Documentation health tests do not prove production safety, browser accessibility or future research workflows. No external LLM spend occurred. PostgreSQL/cache connection failures are tested/sanitized, but this P01 work is not a production chaos or load certification. Frontend production was build-validated; public TLS deployment is not configured in local P01.

The test suite cannot exhaust all possible inputs. Its passing result applies to the committed-in-files P01 contracts and explicitly listed checks, not the full future platform.
