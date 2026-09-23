# Elseview — Lightweight backend blueprint — Tunisian research platform

**Brand:** Elseview — See what you’re missing.

**Revised September 23, 2026. Proposed design, not implemented software.**

Step-by-step development plan: [BACKEND_IMPLEMENTATION_PLAN.md](/Users/user/Workspace/startup-act/BACKEND_IMPLEMENTATION_PLAN.md). It defines phase order, canonical implementation names, tests and completion gates without changing the four-container architecture.

## 1. Final architecture

**Exactly four containers: frontend, backend, database and cache. AI uses an external cloud LLM with an OpenAI-compatible API.** This decision replaces the previous local-model and dedicated-worker architecture.

```text
Browser -> frontend (web assets + reverse proxy)
                    -> backend (FastAPI + embedded job runner)
                         -> database (PostgreSQL)
                         -> cache (Valkey)
                         -> cloud LLM (HTTPS, external provider)
                         -> private persistent files
```

No local model, GPU, Celery, separate worker/scheduler container, object-storage server, vector database or microservices. The cloud provider is not a fifth container. Self-hosting the application does not make cloud inference free or keep all research data inside Tunisia.

## 2. Technologies

| Part | Proposed choice | Purpose |
|---|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn | One API application |
| Validation | Pydantic 2, pydantic-settings | Typed payloads and settings |
| Database | PostgreSQL 16, supported patch release | Durable relational data and JSONB |
| Database access | SQLAlchemy 2, psycopg 3 | Synchronous, explicit service transactions |
| Migrations | Alembic | Controlled schema changes |
| Cache | Valkey 8.1 supported patch line | Cached reads and rate counters, not a broker |
| Cloud client | OpenAI Python SDK with custom base URL | Verified compatible Chat Completions provider |
| Authentication | PyJWT, pwdlib with Argon2 | No external identity service required |
| Files | Backend-mounted private volume | Uploads and exports without another container |
| Frontend serving | Built assets and Caddy in frontend container | Serve UI, proxy `/api`, TLS for public deployment |
| Frontend library | React | User-confirmed choice; planned client-rendered application, not yet implemented |
| Tests | pytest and HTTPX | Local mock-provider tests; real PostgreSQL integration |
| Deployment | Docker Compose | Four services only |

These are planned dependencies, not installed or locked packages. Resolve supported patches, check compatibility and pin versions during implementation. A provider being OpenAI-compatible does not mean it supports every OpenAI endpoint or feature.

## 3. Container responsibilities

### Frontend

React provides the researcher dashboard, participant tests and report views, with Arabic RTL, French and accessible interaction. Plan a client-rendered application; no separate server-rendering service is required. React calls FastAPI through `/api` and never calls the cloud LLM directly. The same frontend container serves the built UI and proxies API requests. Only this service publishes public ports. No API keys or researcher-only answer rules enter browser bundles. Development can run the frontend development server in this same service instead. Build tooling and additional React libraries will be selected during implementation rather than assumed installed.

### Backend

Authentication, study building, recruitment, collection, quality review, reporting, cloud requests and private files. Start with one Uvicorn process. Its FastAPI lifespan manages a small supervised background-job loop. No model weights or heavy media engine is installed by default.

### Database

Permanent studies, answers, consent, jobs, usage and compensation records. Restricted application role; private network; persistent volume. The database, not cache, decides whether a job or payment event happened.

### Cache

Short-lived dashboard results and rate-limit counters. Tenant-specific keys include relevant source/permission versions. Cache loss cannot lose submissions, earned rewards or jobs. Sensitive operations fail closed or use a bounded DB rate-limit fallback when cache is unavailable.

## 4. Lightweight code structure

Proposed project root: `/Users/user/Workspace/startup-act/`. This layout is not an implemented app.

```text
frontend/                    React application and web-server configuration
backend/
  app/
    main.py                  FastAPI construction and lifespan
    config.py                environment validation
    db.py                    engine and per-operation sessions
    auth/                    users, memberships, permissions
    studies/                 versions, templates, block validation
    participants/            profiles, private contacts, recruitment
    responses/               sessions, answers, quality reviews
    reports/                 snapshots, metrics, exports
    ai/                      cloud client, prompts, evidence, budgets
    jobs/                    database job claiming and handlers
    common/                  assets, audit, shared helpers
  migrations/
  tests/
  pyproject.toml
compose.yaml
.env.example
```

Use ordinary router/schema/service/model files only where needed. These folders are not microservices. Avoid abstract repository frameworks, event buses or plugin systems before a real need exists.

## 5. Data model: implement only needed tables

The larger dictionary at `/Users/user/Workspace/startup-act/docs/backend/DATA_MODEL.md` is a future normalized reference, **not a requirement to create 70 tables at launch**. This smaller first-release model takes precedence.

| Table | Key data and rules |
|---|---|
| users / refresh_tokens | Credentials hashed, rotating login grants, expiry/revocation |
| workspaces / memberships | Company, country, locale, timezone; unique user membership |
| study_grants | Member, study and explicit capabilities; not every member can read every study |
| participant_profiles | Explicit shared-panel opt-in and consented attributes |
| private_contacts | Workspace-owned contacts; no automatic global merging |
| studies / study_versions | Lifecycle, immutable published version, validated blocks and private rules in separate JSONB fields |
| invitations / reservations | Hashed capability, audience source, compensation offer, expiry and atomic capacity hold |
| consent_receipts | Purpose, document version, language, decision and time |
| sessions / answers | Pinned version, assignment, answer status, typed value and revision |
| review_decisions | Assigned reviewer, decision, evidence and append-only history |
| assets | Workspace, opaque key, size, checksum, purpose, state and retention |
| analysis_snapshots / reports | Fixed source revisions, exclusions, metrics, approved findings |
| jobs | Kind, target, unique key, attempts, due time, status, lease token/expiry |
| ai_runs / usage_budgets | Provider/model, input hash, reservation, actual usage, evidence, limits |
| idempotency_records | Actor/operation/key, request hash, saved response |
| audit_events | Who changed what; no raw answers or secrets |

Strictly validate block JSON and freeze it on publish. Verify answer block keys belong to the pinned version in application code. Normalize blocks later if query requirements justify it. Keep original answers separate from translated or generated text.

Add event capture, diary occurrences, bookings, exports, API keys and billing tables when their features ship. **Real compensated studies require durable reward/payment records before launch.** Money uses integer smallest currency units, explicit currency, unique posting keys and append-only corrections; no escrow or automatic transfers. Private-panel data remains isolated.

## 6. Features retained

- UX: survey, prototype, timed exposure, preference, first click; later card/tree, interviews, diary and accessibility research.
- Product: concept, pricing, onboarding, journey and feature-priority templates.
- Marketing: ad clarity, brand, landing pages and audience comparisons.
- Business: instructions, forms, offers, support and market-entry templates.
- AI evaluation: humans review customer model answers, translations and authorized chatbot scenarios.
- AI assistant: cloud-generated test drafts, themes, summaries, translation and evidence-linked report drafts.

Reuse the same typed blocks for multiple business use cases. Detailed method behavior remains at `/Users/user/Workspace/startup-act/docs/backend/RESEARCH_METHODS.md`. Larger optional feature/API contracts are retained at `/Users/user/Workspace/startup-act/docs/backend/FEATURE_CONTRACTS.md`; they do not require more containers or immediate implementation.

## 7. Durable background work inside backend

FastAPI lifespan starts one supervised job loop. PostgreSQL holds durable work; do not rely only on fire-and-forget tasks or FastAPI BackgroundTasks.

1. Save business action and pending job in one transaction. Return `202` with job ID.
2. Claim a bounded due batch using `FOR UPDATE SKIP LOCKED`, set a lease, commit.
3. Execute outside database transactions. Use async cloud HTTP; run blocking database work in a bounded thread with its own session.
4. Persist result only if lease and consent epoch still match. Settle usage once.
5. Shutdown stops claiming work and drains for a bounded time. Expired leases allow recovery after restart.

Initial limits: one backend process, one cloud request at a time, one small export at a time, two-second polling. Reminders are jobs with `run_after`; no scheduler service. Lease ownership and permanent idempotency keys protect result/financial writes. Queue claims may run more than once; external provider execution is not guaranteed exactly once.

A cloud timeout can still incur a provider charge. Mark unknown outcomes and reconcile conservatively instead of blindly retrying. Blocking CPU/media tasks must not monopolize the API event loop. Accept transcripts first; defer heavy audio/video processing or explicitly approve a cloud media service. Do not quietly restore local inference or worker containers.

## 8. Cloud LLM integration

Full specification: `/Users/user/Workspace/startup-act/docs/backend/AI_CLOUD.md`.

Required backend-only settings: approved `LLM_BASE_URL`, `LLM_API_KEY`, exact `LLM_MODEL`, capability profile, time/output limits and cost limits. The provider/model has not been supplied yet, so no specific price or strongest-model claim is made.

Use compatible Chat Completions initially; verify authentication, message roles, model IDs, output-token field, JSON support, errors and usage. Do not assume Responses, tool calling, file uploads, batch APIs or provider idempotency are available.

The model produces drafts. SQL/Python calculates counts. Application code checks cited source IDs and exact quotes; humans approve findings. No synthetic participants, emotion-as-fact inference, automatic payout rejection or invented results.

## 9. Cost controls

Reserve maximum estimated call cost transactionally before dispatch. Include input, capped output and provider-specific reasoning/cache charges. Record actual usage and request IDs per attempt. Use Decimal amounts with explicit billing currency; do not confuse USD provider spend with TND customer invoices.

Disable automatic SDK retries; one application layer owns bounded retries. Cache by workspace, snapshot, consent epoch, model/provider/config revision and prompt/schema. Changed evidence invalidates cache. Limit context and output; do not resend the full study for each question. Apply per-study and daily workspace caps including outstanding reservations.

## 10. Tunisian privacy and security

The company is Tunisian by proposed business design; this documentation does not incorporate it or obtain a label. Default currency can be TND, scheduling Africa/Tunis, languages Arabic and French.

Cloud prompts may leave Tunisia. Approve the provider's location, retention, training use, deletion support and contractual terms, and confirm applicable transfer formalities before real personal-data processing. Consent alone is not a blanket authorization. Sensitive studies can remain human-only.

Redact unnecessary identifiers, keep keys backend-only, restrict destination hosts and never log prompts/raw answers. Every job/export rechecks workspace scope and consent. Withdrawal invalidates accessible AI/report/cache derivatives and triggers applicable deletion. Provider-side deletion cannot be promised beyond actual provider capabilities.

Keep short-lived access tokens, hashed rotating refresh tokens, CSRF controls, scoped study grants and private files. Human-only mode must prevent backend AI dispatch, not only hide a button. Real user/financial data needs tested backup and access controls even in a small app.

## 11. Deployment and recovery

Full plan: `/Users/user/Workspace/startup-act/docs/backend/SELF_HOSTING.md`.

Frontend is the only public service; database/cache use private service DNS. Backend uploads/exports and PostgreSQL each have persistent volumes. TLS is required for internet access and can terminate inside the frontend serving container. No public directory listing or direct private-file mount.

Migrations are one-off commands through the existing backend service, not a permanent fifth container. Back up a matched database and asset set with encrypted off-device copies. Restore privacy tombstones before reopening access. Cache is disposable; jobs and compensation history are not.

## 12. API and testing

Use `/api/v1`, typed JSON, stable error codes, pagination and request IDs. Final submissions, AI requests and financial commands are idempotent. Preview data never counts as actual participants or revenue.

```json
{"job_id":"5a2179c0-2526-47a0-bc13-a2a85890896d","kind":"ai_summary","status":"pending"}
```

Test last-slot reservation races, duplicate submissions, tenant isolation, immutable versions, restart recovery, lost leases, invalid cloud JSON, 429/timeouts, uncertain charges, budget races, withdrawal mid-call and private downloads. Mock the provider in ordinary tests; live compatibility tests are opt-in with synthetic data and a small spending cap.

This is a single-process low-complexity deployment, not a high-availability promise. Measure latency and memory before increasing workload. No application, provider connection or containers were started by this documentation revision.

## 13. References and precedence

This document supersedes the previous local-model and multi-worker choices. Detailed dictionaries describe future options only where consistent with this architecture.

- https://github.com/openai/openai-python — custom base URL, async client, retry and timeout settings.
- https://fastapi.tiangolo.com/advanced/events/ — application lifespan.
- https://www.postgresql.org/docs/16/sql-select.html — queue-like row locking.
- https://docs.sqlalchemy.org/en/20/orm/session_basics.html — transaction and concurrency rules.
- https://valkey.io/ — cache project.
