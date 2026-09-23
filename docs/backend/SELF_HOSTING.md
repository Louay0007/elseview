# Elseview — Simple self-hosting: four containers

**Brand:** Elseview — See what you’re missing.

## Services

| Service | Contents | Persistent data |
|---|---|---|
| frontend | Built React UI and Caddy web server/reverse proxy | TLS configuration/certificates when public HTTPS is used |
| backend | FastAPI and embedded database-backed job runner | Private uploaded and exported files |
| database | PostgreSQL | Permanent database volume |
| cache | Valkey | Optional/disposable cache state |

The cloud LLM is an external HTTPS service, not a container. No separate worker, scheduler, inference, storage, monitoring or proxy service. The frontend container itself proxies `/api` and serves the UI.

React is the confirmed frontend choice. The planned client-rendered app uses FastAPI through `/api`; cloud LLM credentials stay in the backend. Build tooling is not yet selected or installed. Development and production use the same frontend service slot, so the architecture remains four containers.

## Runtime

The inspected Mac has Apple Silicon, 16 GiB RAM and a Docker CLI, but its daemon was not running when checked. The backend image supplies Python 3.12; do not replace system Python. Use ARM64-compatible images and tested pinned dependencies. Choose a suitable container runtime; Docker Desktop licensing is conditional, and Colima is an alternative.

One backend application process initially, with one lifespan-managed job runner. PostgreSQL stores leases and future due times. Cloud HTTP is async; blocking database/export operations use bounded execution. No GPU or model memory planning is required.

## Networks and settings

Only frontend publishes ports: loopback during local development, reviewed public HTTPS for deployment. Database and cache use internal service names, with no public ports. Backend sends requests only to its approved cloud API and explicitly configured services.

Settings include database credentials, cache authentication, signing secrets, exact origins, cloud base URL/key/model, capability profile, budgets, upload caps, retention and job concurrency. Keep secrets outside committed files and frontend build arguments.

Host root: `/Users/user/Workspace/startup-act/`. Backend volume paths: `/app/private/assets` and `/app/private/tmp`. Container paths are not host paths. No direct public static serving of private files.

## Resilience

- Cloud down: participant collection remains available; AI jobs show pending/failed.
- Cache down: uncached reads continue; sensitive throttling fails closed or uses DB fallback.
- Database down: no mutation is acknowledged unless persisted.
- Restart: unfinished jobs recover from leases; unknown external outcomes retain conservative cost status.
- Low disk: refuse new large uploads before corruption.

Migrations and backups are one-off commands through existing services, not additional permanent containers. No runnable Compose/application images are supplied by this design-only update.

## Backups and costs

Back up matched PostgreSQL and private files using a coordinated recovery point. Encrypt backups, keep an off-device copy, protect keys and test restore. Reapply consent-deletion restrictions before reopening access. Cache is not needed to recover jobs or earned compensation.

The software is self-hostable; cloud fees, hardware, electricity, backups and participant compensation are not automatically free. Measure concurrency and export impact before growing. This simple setup is not a high-availability claim.

## References

- https://fastapi.tiangolo.com/advanced/events/
- https://www.postgresql.org/docs/16/backup-dump.html
- https://github.com/abiosoft/colima
- https://valkey.io/

Status: planned deployment. No containers or cloud calls were started.
