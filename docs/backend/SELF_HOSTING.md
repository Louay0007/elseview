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

React/Vite are installed. The client uses FastAPI through `/api/`; cloud LLM credentials stay in the backend. Development Vite and production Caddy occupy the same frontend service slot, so the architecture remains four containers.

## Runtime

The development host is an Apple Silicon Mac. The executed P18 probe recorded Linux aarch64, eight logical CPUs and about 8.32 GB of physical memory visible inside its container; see `P18_RELIABILITY.md` for measurement scope. The backend image supplies Python 3.12; do not replace system Python. Images and installed dependency versions are pinned.

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

Migrations and backups are one-off commands through existing services, not additional permanent containers. Use `/Users/user/Workspace/startup-act/scripts/dev` for the canonical Compose file set. P18 exercised actual database/cache/backend restarts after a local backup; readiness recovered and durable development counts matched.

## Backups and costs

Back up matched PostgreSQL and private files using a coordinated recovery point. Encrypt backups, keep an off-device copy, protect keys and test restore. Reapply consent-deletion restrictions before reopening access. Cache is not needed to recover jobs or earned compensation.

The software is self-hostable; cloud fees, hardware, electricity, backups and participant compensation are not automatically free. Measure concurrency and export impact before growing. This simple setup is not a high-availability claim.

## References

- https://fastapi.tiangolo.com/advanced/events/
- https://www.postgresql.org/docs/16/backup-dump.html
- https://github.com/abiosoft/colima
- https://valkey.io/

Status: four-container development installation verified through P18/P19 acceptance work. AI remains mocked and integrations disabled. This is not production high availability, encrypted backup certification or a live-provider approval. See `P18_P19_ACCEPTANCE.md` and `P16_P17_API.md` for evidence and restore prerequisites.
