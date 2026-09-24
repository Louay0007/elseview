# Elseview — Development platform and acceptance evidence

**Brand:** Elseview — See what you’re missing.

P18 adds checked OpenAPI/error contracts, React/browser contract fixtures, guarded
load measurements and restart checks. P19 adds integrated backend acceptance and
a ten-story coverage map; remaining combined browser/live-provider/production
gates are explicit, not silently marked passed. Start with
`/Users/user/Workspace/startup-act/docs/backend/P18_P19_ACCEPTANCE.md`.

## Elseview naming

- Compose project and image prefix: `elseview`.
- Containers: `elseview-frontend-1`, `elseview-backend-1`, `elseview-database-1`, `elseview-cache-1`.
- Active volumes: `elseview_postgres_data` and `elseview_private_data`.
- Databases: `elseview_app` and the guarded `elseview_test`.
- Packages: `elseview-backend` and `elseview-frontend`; backend logger: `elseview`.
- Workspace path stays `/Users/user/Workspace/startup-act/`; internal service DNS names and `/api/v1` routes stay unchanged.

The existing P01 installation was migrated by copying stopped volumes and renaming the copied databases. Original `research-platform_postgres_data` and `research-platform_private_data` volumes remain as rollback copies, not active storage. Private dumps and the before/after data comparison are in the ignored directory `/Users/user/Workspace/startup-act/.tools/elseview-backup/`. Do not publish backups or delete them before confirming recovery needs.

On this migrated installation, Compose may warn that the adopted Elseview volumes were not originally created by Compose. Their explicit names intentionally select the preserved data. Fresh installations create these volumes normally; no destructive reset is required.

Implemented: four-container development foundation, authentication/workspaces, durable jobs, privacy/consent APIs, private uploads, versioned study builder APIs, study grants, seven core method contracts and a React test-only preview renderer.

P06/P07 add purpose-separated panel/private recruitment, screeners, overlapping quotas,
development reward commitments, consent-bound participant sessions, append-only answer
revisions, event batches, one-shot exposure and atomic final submission. Participant
accounts need verification but not membership in the researcher's workspace.

P08/P09 add independent human review, adjudication and appeals; idempotent reward
obligations and manual payment/reversal records backed by a balanced immutable
journal; accepted-source analysis snapshots, deterministic metrics, approved report
versions, privacy-filtered JSON/CSV exports and revocable shares.

P10/P11 add a consent-gated, budgeted async AI adapter (mock by default), conservative
uncertain-charge handling, and seven advanced research methods with React renderers
and a minimal existing-session participant runner.

**Not enabled or certified:** live provider compatibility/dialect quality, automated
financial transfers, cloud transcription, external sandbox connectors, XLSX/PDF export or P16–P19; no public-production release or full
browser accessibility certification is claimed. The embedded runner
executes `system.check` and internally authorized `privacy.erase` and
`collection.quality`, `ai.generate` and `longitudinal.reminder`. Public job submission cannot invoke internal
jobs. Live AI requires explicit operator capability/privacy/host/pricing approvals;
development and ordinary tests remain mock. No authentication bypass is provided.

P06/P07 API usage, safe retry rules and development limitations are documented in
`/Users/user/Workspace/startup-act/docs/backend/P06_P07_API.md`. Apply the additive
`006_recruiting → 007_collection → 008_reviews → 009_analytics → 010_ai → 011_methods → 012_longitudinal → 013_evaluation → 014_templates → 015_billing` migrations explicitly with
`/Users/user/Workspace/startup-act/scripts/dev exec -T backend alembic upgrade head`.
Do not reset the application database to install these phases.

Review/payment and analytics/report API contracts, operational boundaries and safe
retry examples: `/Users/user/Workspace/startup-act/docs/backend/P08_P09_API.md`.
Payment entries record manually verified evidence; this backend does not move money.

AI configuration, optional consent, advanced method contracts and browser limitations:
`/Users/user/Workspace/startup-act/docs/backend/P10_P11_API.md`.

P12/P13 add consent-bound interview bookings, in-app reminders, immutable diary
occurrence sessions, private recording/transcript evidence, and a standalone human
evaluation workbench with blind pairwise assignments, versioned datasets, annotation,
adjudication and reviewed exports. Minimal React schedule/evaluation forms are available.
Contracts and limitations: `/Users/user/Workspace/startup-act/docs/backend/P12_P13_API.md`.

P14/P15 add 23 versioned template recipes and opt-in commercial plan/allowance/usage,
invoice, manual payment and credit workflows using the existing P08 ledger. Publication,
response and AI add-on hooks preserve frozen prices and duplicate-safe source IDs.
Unactivated development workspaces remain unbilled. Commercial activation requires
explicit reviewed rules; no bank/card automation or jurisdictional compliance claim.
See `/Users/user/Workspace/startup-act/docs/backend/P14_P15_API.md`.

## P02 — Authentication and workspaces

All routes use `/api/v1`. Auth writes require `Origin: http://localhost:8080` in development. Login returns a short-lived bearer access token plus a CSRF token, while the opaque refresh token is an HttpOnly, SameSite=Strict cookie scoped to `/api/v1/auth`. Production-mode cookies are Secure; local HTTP is development-only.

| Routes | Function |
|---|---|
| `POST /auth/register`, `/auth/verification/request`, `/auth/verify-email` | Register, resend verification, consume verification token |
| `POST /auth/login`, `/auth/refresh`, `/auth/logout` | Login, rotating refresh and logout |
| `POST /auth/password-reset/request`, `/auth/password-reset/confirm` | Generic recovery request and one-use reset |
| `GET /me`, `/me/login-sessions`; `DELETE /me/login-sessions/{id}` | Own identity and session revocation |
| `POST/GET /workspaces`; `GET /workspaces/{id}` | Create/list/read authorized workspaces |
| `GET /workspaces/{id}/members`; `PATCH/DELETE /workspaces/{id}/members/{member}` | Membership administration and last-owner protection |
| `POST /workspaces/{id}/invitations`, `/workspace-invitations/accept` | Recipient-bound, expiring invitations |
| `GET /workspaces/{id}/audit` | Redacted workspace audit for authorized administrators |

Refresh requires the cookie, allowed Origin and `X-CSRF-Token`. Logout requires the bearer and allowed Origin, plus the bound CSRF token when a refresh cookie is present. Other authenticated APIs use an explicit bearer token, not automatic cookie authentication. Keep browser access tokens in memory. Refresh replay revokes the family; reset invalidates all existing access sessions.

**Development email:** verification/reset/invitation messages are written to private `/app/private/dev-mail/*.json` inside the backend volume, with directory/file permissions 0700/0600. An operator can inspect that mailbox using `scripts/dev exec`; it is not exposed through an HTTP endpoint and tokens are not printed in logs. Files expire from the spool after 24 hours during subsequent delivery, with a 1,000-message cap. Token validity is separately enforced by the database. This is not production SMTP delivery. Failed delivery can be retried through verification/reset requests; do not publish the mailbox or backups.

Workspace roles are owner, admin, researcher, reviewer and viewer. Membership is always checked against active user/workspace status. Only owners can promote/demote owners or administrators; removing the final owner is rejected under a workspace lock. Study access additionally requires ownership or an explicit role-bounded study grant. Participant research capabilities remain P06/P07 work; they are not workspace staff roles.

## P03 — Durable jobs and cache

`POST /workspaces/{workspace_id}/jobs` accepts `{"command_key":"unique-operation-key","kind":"system.check","payload":{}}`. Owners/admins/researchers may submit this diagnostic. Duplicate command keys replay the same job; changed payloads conflict. `GET` the collection/detail for authorized status; `POST /{job_id}/cancel` cancels permitted work. Nonadministrators cannot read another requester's job.

The runner is enabled in development Compose and stays inside the backend process. PostgreSQL stores due times, leases, attempts and state; cache restart cannot lose work. Claiming uses `SKIP LOCKED`; completion rechecks lease, membership, user/workspace state and privacy epoch. Expired unsafe external attempts become uncertain rather than being blindly replayed. No real external job handler exists yet.

Handler timeouts and shutdown are bounded. A handler suppressing cancellation quarantines that runner instance; restarting the backend is required, and the lease remains available for controlled reconciliation. Python cannot forcibly kill arbitrary running code safely. Future handlers must cooperate with cancellation and must not perform CPU-heavy work on the event loop.

Valkey caches only scoped disposable data and rate counters. Security-sensitive rate limits fail closed with 503 when cache is unavailable; excess requests receive 429. Test cache keys use isolated DB15 namespaces, never shared DB0. Generic transactional idempotency stores only request/key hashes and safe response receipts; expired keys return 409. New keys still require domain uniqueness constraints for financial or other irreversible effects.

## P04 — Privacy and private files

All routes below are relative to `/api/v1/workspaces/{workspace_id}` and require a bearer token. Consent and policy administration is owner/admin-only. Upload creation and completion require owner/admin/researcher; a role revoked after intent creation is rechecked. Other asset readers need ownership, an administrative capability, or a revocable member link.

| Routes | Contract |
|---|---|
| `POST/GET /consent-documents` | Immutable localized document key/version, purpose, text and SHA-256 digest |
| `POST/GET /consent-receipts` | Own decision, displayed digest and retained receipt key; study-purpose decisions additionally bind the exact published `study_version_id` |
| `POST/GET /retention-policies` | Immutable raw/media/derived/export durations, version and stated legal basis |
| `POST /upload-intents` | Declared size, MIME type, extension, checksum, purpose and retention policy; retained upload-key replay |
| `PUT /upload-intents/{id}/content` | Stream raw bytes with the declared Content-Type; no multipart form or public path |
| `POST /upload-intents/{id}/complete` | Validate quarantined bytes; repeat completion returns the same ready asset |
| `GET /assets/{id}`, `/assets/{id}/content` | Authorized metadata/download with current restriction, retention and checksum checks |
| `POST /assets/{id}/links`; `DELETE /assets/{id}/links/{link_id}` | Same-workspace member sharing and immediate revocation |
| `POST /privacy-requests`; `GET /privacy-requests/{id}` | Own access, withdrawal or erasure request with a retained request key |
| `GET /privacy-requests/{id}/data` | Paginated own identity, asset metadata and receipt data for an access request |
| `POST /privacy-requests/{id}/retry` | Explicit retry after exhausted erasure attempts; does not duplicate active cleanup |
| `POST /assets/retention-sweep` | Owner/admin cleanup of up to 100 expired/abandoned objects per call |

Supported file subset: noninterlaced 8-bit RGB/RGBA PNG, at most 8 MiB, 4096 pixels per axis and four million pixels; UTF-8 CSV, at most 2 MiB, 10,000 rows and 100 columns; UTF-8 text, at most 1 MiB; PCM WAV, at most 16 MiB and ten minutes. Unsupported formats/encodings are rejected. This is bounded structural validation, **not antivirus scanning, arbitrary document parsing or transcription**. CSV downloads are attachments; imported/reported spreadsheet formula handling belongs to later phases.

Uploads expire after one hour; streaming requests have a 60-second deadline. Workspace reserved storage defaults to 256 MiB (`PRIVATE_WORKSPACE_BYTES`), including pending objects, and uploads require 32 MiB free disk headroom. Files use generated opaque keys, 0700 directories, 0600 files and descriptor-relative no-follow access. Failed uploads require a new intent, unless failure occurred before data transfer. Expiry denies access immediately; operators run retention sweeps until empty for physical cleanup. No additional storage service or scheduler is introduced.

Withdrawal creates a durable subject/workspace restriction and advances the workspace privacy epoch before returning. A declined optional AI consent does not prohibit human-only work. Recording use requires affirmative current recording consent. `privacy.erase` removes owned files, links/intents, receipts, owned study drafts/published content and replay payloads; its final database effects are lease-fenced. Cleanup continues even after membership revocation and cannot be cancelled via the diagnostic job API.

**Erasure boundary:** this is workspace-scoped foundational erasure, not global account deletion or completed P17 privacy compliance. Identity, membership, immutable organization consent/policy documents, redacted audit and minimal restriction/job/asset tombstones remain. There are no public-panel profiles or imported private contacts yet, and no identity/contact merging. Later producers must join the deletion workflow; backup tombstone replay, reviewed legal holds and provider-side deletion remain later gates.

## P05 — Versioned builder and preview

Use `GET /api/v1/research-methods` for the enabled registry. Core methods are `survey.single`, `survey.multi`, `survey.rating`, `survey.text`, `preference`, `five_second` and `prototype.task`. Configuration, answer values, event metadata, safe projections and deterministic reducer functions have synthetic French/Arabic fixtures. The preview shell is English; authored prompts/options/consent support French and Arabic/RTL.

1. Create consent translations and a retention policy; upload and complete any image stimuli.
2. `POST /studies` with `Idempotency-Key`, title, retention-policy UUID and `ai_policy` (`human_only` by default). The receipt returns study UUID, initial version UUID and revision 1.
3. `PUT /studies/{study_id}/versions/{version_id}` with `expected_revision`, typed `blocks_json`, private `rules_json`, locales and locale-to-document UUIDs. Successful edits increment the revision. See `backend/tests/study_fixtures.py` for complete executable examples.
4. `POST .../validate`, then `POST .../publish` with the current `expected_revision`. Publication validates translations, branches, consent, stimuli, rules and renderer availability, freezes the canonical hash and creates one launch-ready record. A launch-ready record does not recruit participants.
5. `POST .../new-draft` or `POST .../clone` with `Idempotency-Key` to revise/duplicate without mutating a published version. Only one draft per study is permitted. `PATCH /studies/{study_id}/state` supports pause/resume, close and archive transitions.
6. `POST /studies/{study_id}/grants` assigns explicit role-bounded capabilities to an active same-workspace membership; `DELETE /studies/{study_id}/grants/{id}` revokes them. Read-only grants do not expose private author configuration or scoring rules.
7. `POST .../preview` with a locale returns a 15-minute, session-bound preview capability and a `/#preview=...` path. Open that path on the local frontend. The fragment is immediately removed from the address bar; keep the capability private. Backend endpoints `/api/v1/study-preview` and `/api/v1/study-preview/assets/{id}` accept it through `X-Preview-Token` and recheck session, grants, version, sources and privacy epoch.

Preview answers are sent transiently to the backend for path/value validation, not stored as research records. They never create collection sessions, rewards, recruitment, charges or report evidence. Preference order is stable for the preview capability. The five-second renderer preloads the image, uses a one-shot display, detects hidden-tab interruption and records a sessionStorage attempt marker to prevent a clean replay of that same preview attempt. Timing remains client-observed, not certified instrumentation. Production session persistence and exposure event adjudication are P07 work.

Prototype tasks use owned image flows or a reviewed public HTTPS link with a private authorization reference/build revision. The backend never fetches arbitrary prototype URLs or claims to observe cross-origin success; outcomes are self-reported. No remote connector is enabled.

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

The wrapper always uses the same environment file and base/development Compose pair, independently of your working directory. Run `scripts/dev up -d --build frontend` after changing frontend source; backend changes reload from a bind mount. The default React page is a connectivity diagnostic; authorized preview links open the P05 renderer. A complete researcher dashboard and production participant workflow are not implemented.

## Tests

The full guarded suite uses the separate `elseview_test` database. It migrates/reset that test schema; never point the runner at valuable data.

```sh
/Users/user/Workspace/startup-act/scripts/dev exec -T -e TEST_ALLOW_RESET=elseview_test backend python -m app.test_runner -q --cov=app --cov-report=term-missing
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m ruff check app migrations tests
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m ruff format --check app migrations tests
/Users/user/Workspace/startup-act/scripts/dev exec -T backend python -m pip check
python3 /Users/user/Workspace/startup-act/scripts/validate_blueprint.py
```

Plain pytest without the explicit DB guard runs unit/API tests and clearly skips real-DB cases. It is not equivalent to the full suite. Test fixtures deny external Python socket connections; guarded DB tests allow the selected test PostgreSQL address and explicitly cache-marked tests allow Valkey with isolated DB15 keys. No cloud call is implemented. This is a test safeguard, not a production egress firewall. Tests explicitly disable the app runner except isolated runner/lifespan tests.

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

The base Compose file is a local development foundation too, not a production deployment. Database owner/test credentials are available in the backend development container so explicit migration/test commands work. Before production, remove those credentials from the runtime, configure real email delivery and secret management, TLS/public-domain settings, reviewed retention and recovery controls. Audit APIs have no modification endpoints; database administrators still control their database, and this is not tamper-proof audit storage.

Migration chain: `001_foundation → 002_identity → 003_jobs → 004_privacy → 005_studies → 005_study_guards`. The final two revisions belong to logical phase P05; the second adds immutable document/validated-dimension guards without changing existing records. Foundation and identity/job rows were preserved. P04 adds eight tables (including immediate restrictions); P05 adds four tables. Migrations use frozen DDL, not mutable runtime model creation. Destructive test downgrade is permitted only on the dedicated guarded test database; application startup never migrates.

The container development target includes test dependencies intentionally. A smaller production-only backend image can be introduced when production deployment is in scope. No fifth worker/storage/model service is required.

## Evidence

See `/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md` for actual test/build results and limits. The implementation roadmap remains `/Users/user/Workspace/startup-act/BACKEND_IMPLEMENTATION_PLAN.md`.
