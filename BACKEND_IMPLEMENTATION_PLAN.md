# Elseview — Backend implementation plan — development mode

**Brand:** Elseview — See what you’re missing.

**Date:** September 23, 2026.  
**Status:** P01–P18 have development implementations and executed evidence. P19 has integrated automated acceptance and a ten-story test map, but unresolved combined browser/live-provider/production gates prevent unconditional final sign-off. See `/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md` and `/Users/user/Workspace/startup-act/docs/backend/P18_P19_ACCEPTANCE.md`. Commercial activation requires reviewed invoice/payment rules; live-provider/dialect evaluation, external transcription/sandbox connectors, production backup encryption and full browser accessibility/interaction validation remain external or disabled gates. Backend tests do not certify them. Checklists below describe acceptance criteria, not automatic evidence that every gate passed.

## 1. Goal, source documents and precedence

Build the complete Tunisian user-research platform progressively, using **React, Python FastAPI, PostgreSQL and Valkey**, with a cloud OpenAI-compatible LLM. Keep exactly four service definitions: `frontend`, `backend`, `database`, `cache`. Features are folders and functions, not microservices.

Sources reviewed:

- `/Users/user/Workspace/startup-act/BACKEND_BLUEPRINT.md`
- `/Users/user/Workspace/startup-act/docs/backend/SELF_HOSTING.md`
- `/Users/user/Workspace/startup-act/docs/backend/AI_CLOUD.md`
- `/Users/user/Workspace/startup-act/docs/backend/RESEARCH_METHODS.md`
- `/Users/user/Workspace/startup-act/docs/backend/FEATURE_CONTRACTS.md`
- `/Users/user/Workspace/startup-act/docs/backend/DATA_MODEL.md`

The main blueprint controls architecture. This plan resolves implementation naming, phase order and development-test contracts. Method specifications control method behavior unless an explicit correction below applies. The extended 70-table dictionary is a source of constraints, **not a command to build every table or an incompatible second schema**.

Companion acceptance inventory: `/Users/user/Workspace/startup-act/docs/backend/MODEL_TEST_MATRIX.md`. It maps all 70 older model names to the implementation, including combined or deferred models, plus models missing from that dictionary.

“All cases” means an explicit, risk-based acceptance suite for every implemented feature, model and state transition. No finite test suite proves the absence of every possible defect. Never report an unimplemented or skipped test as passed.

## 2. Non-negotiable development rules

1. One Python application and one initial Uvicorn application process. No Celery, local LLM, separate scheduler/worker, vector database or object-storage server.
2. PostgreSQL is authoritative for jobs, submissions, consent, budgets and money; Valkey is disposable cache and throttling only.
3. FastAPI lifespan starts and supervises the embedded job loop; jobs survive process reload because their records live in PostgreSQL.
4. Cloud calls occur outside database transactions using an async client. Blocking SQL uses independent synchronous sessions in routes or a bounded thread executor.
5. Use mocked cloud responses by default in tests and demos. Never spend money merely by running the ordinary test suite.
6. Auth, consent, tenant boundaries, idempotency and safe retention are foundational work, not final polish.
7. No schema mutation at application startup. Run Alembic explicitly through the backend service.
8. Only synthetic seed data in development. No copied production contacts, national IDs or recordings.
9. Every feature ships with model constraints, service rules, API schemas, permission checks and tests in the same change.
10. Unsupported study methods cannot be published; a feature flag never bypasses safety prerequisites.
11. Exact dependency versions/image digests are resolved and tested at P01; do not assume version ranges are reproducible locks.
12. Treat public deployments as a separate release gate even if the application works locally.

## 3. Implementation decisions that remove conflicts

| Conflict or ambiguity | Canonical decision |
|---|---|
| Embedded block JSON versus normalized `blocks` | Start with typed `blocks_json` and private `rules_json` in `study_versions`. Stable `block_key` strings identify blocks within a version. No duplicate physical block tables. |
| Old symbolic IDs versus resource UUIDs | Actual SQL resource IDs are UUIDs. Block/option/card/node keys are bounded strings, not SQL row IDs. Old examples with `sv_demo_v1` are fixture aliases, not real API UUIDs. |
| Multiple answer endpoints | Use `PUT /api/v1/collection/sessions/{session_id}/answers/{block_key}` with revision and client event ID. The old `/v1/sessions/...` POST example is not an implementation contract. |
| `response` versus `value` | API uses `value`; SQL `answers.value` stores the method-specific object. `status` and `reason_code` are separate columns. |
| Queues and outbox | Persist `jobs` in the command transaction; claim in the backend loop. No broker or separate outbox is needed initially. |
| AI budgets denominated only in millimes | Provider costs use `numeric`/Python Decimal with a currency and price snapshot; TND participant/business money uses integer millimes. Never silently equate them. |
| Entire study snapshot after every answer | Save immutable snapshot membership when analysis is requested, not on every autosave. Cache invalidates using dataset/privacy versions. |
| In-process work and development reload | Reload allowed only in development. Claim leases, shutdown, retry and uncertain cloud costs are tested across restarts. |
| Single model versus complex routing | One configurable approved provider/model initially, with explicit capability settings. No automatic provider fallback. |
| User profile versus private panel | Global identity and opt-in public panel are separate from each workspace's private contacts. Matching email addresses do not merge clients' records. |
| Full feature scope versus lightweight launch | Deliver P01–P19 in order; later features are scheduled, not silently dropped. Each can reuse shared components without additional containers. |

### Canonical answer payload

```json
{
  "schema_version": 1,
  "expected_revision": 0,
  "status": "responded",
  "value": {"option_id": "monthly"},
  "client_event_id": "fa4bba62-7383-4874-b044-e41dc3b6641a"
}
```

`expected_revision=0` creates the first answer. Later writes name the current revision and append a new revision. A duplicate event with identical content returns its original receipt; a changed body under the same event ID returns `409`. Session and version come from the authorized resource, not a trusted body field. `skipped`/`unable` require null value; required blocks cannot be skipped. Inability includes `technical`, `accessibility`, `declined` or `other` without forcing sensitive explanations. Diary sessions bind one occurrence, so no contradictory occurrence ID is accepted.

## 4. Development setup and code ownership

Root is `/Users/user/Workspace/startup-act/`. All paths below are planned unless already documented. React remains the confirmed frontend library; its build tooling is a separate implementation decision, not an added backend service.

| Absolute path | Responsibility |
|---|---|
| `/Users/user/Workspace/startup-act/compose.yaml` | Exactly frontend/backend/database/cache |
| `/Users/user/Workspace/startup-act/compose.dev.yaml` | Development overrides only, no new service names |
| `/Users/user/Workspace/startup-act/backend/Dockerfile` | Python 3.12 environment, nonroot runtime |
| `/Users/user/Workspace/startup-act/backend/pyproject.toml` | Direct dependencies and test/lint settings |
| `/Users/user/Workspace/startup-act/backend/requirements.lock` | Resolved dependencies with reproducible installation policy |
| `/Users/user/Workspace/startup-act/backend/app/main.py` | App factory, exception handlers and lifespan |
| `/Users/user/Workspace/startup-act/backend/app/config.py` | Validated environment, explicit demo/mock/live modes |
| `/Users/user/Workspace/startup-act/backend/app/db.py` | Engine and service-owned session/transaction helpers |
| `/Users/user/Workspace/startup-act/backend/app/auth/` | Accounts, tokens, memberships, grants |
| `/Users/user/Workspace/startup-act/backend/app/studies/` | Draft/version/launch and method registry |
| `/Users/user/Workspace/startup-act/backend/app/participants/` | Profiles, private panels, recruitment and scheduling |
| `/Users/user/Workspace/startup-act/backend/app/responses/` | Sessions, answer revisions, events and review |
| `/Users/user/Workspace/startup-act/backend/app/reports/` | Snapshots, metrics, evidence, reports and exports |
| `/Users/user/Workspace/startup-act/backend/app/ai/` | Provider adapter, prompts, budgets and output validation |
| `/Users/user/Workspace/startup-act/backend/app/jobs/` | Durable embedded runner and handlers |
| `/Users/user/Workspace/startup-act/backend/app/common/` | Private assets, audit, privacy and billing submodules as needed |
| `/Users/user/Workspace/startup-act/backend/migrations/` | Reviewed Alembic revisions |
| `/Users/user/Workspace/startup-act/backend/tests/` | Unit, API, DB, integration, security and contract tests |
| `/Users/user/Workspace/startup-act/backend/tests/fixtures/` | Synthetic French/Arabic/Arabizi studies and expected metrics |

Use module router/schema/service/model files when needed. Avoid empty layers and generic repository frameworks. Repository helpers may flush but never independently commit; the outer command controls commit/rollback.

Development mode: backend code bind-mounted with reload, one app process, private database/cache network, frontend proxy to `/api`. Public local ports bind `127.0.0.1`. Do not expose DB/cache simply to inspect them; use `docker compose exec`. Development permits a diagnostic view with synthetic data but must not disable authentication on the research APIs.

## 5. Build workflow and evidence

For every phase:

1. Confirm dependencies and select the smallest complete vertical slice.
2. Write request/response and state contracts plus test fixtures.
3. Add migration and model constraints, then service logic and permissions.
4. Add endpoints and method-specific serializers; do not serialize ORM objects wholesale.
5. Implement positive, invalid-input, permission, idempotency and failure tests.
6. Run phase tests, full existing regression suite, migration checks and format/lint checks.
7. Record changed paths, exact commands, test totals, failures/skips and unresolved external dependencies.
8. Mark phase complete only when its exit gate passes. Do not advance past a failed safety dependency.

Expected phase log file: `/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md`, created during coding. Each entry includes commit or change reference, migration revision, schema coverage, test result, remaining blocker and enabled flags. This plan itself does not claim those results exist.

## 6. Ordered phases and migration dependency map

| Phase | Delivers | Depends on | Migration group |
|---|---|---|---|
| P01 | Development foundation, config, test harness | None | 001 |
| P02 | Auth, workspace isolation, grants and audit | P01 | 002 |
| P03 | Durable jobs, idempotency and cache policy | P02 | 003 |
| P04 | Consent, private files and privacy foundations | P02–P03 | 004 |
| P05 | Versioned builder and core methods | P04 | 005 |
| P06 | Public/private panel and recruitment | P05 | 006 |
| P07 | Resumable collection and event handling | P06 | 007 |
| P08 | Quality review, appeals and compensation | P07 | 008 |
| P09 | Deterministic analysis and reports | P08 | 009 |
| P10 | Cloud LLM adapter, budgets and evidence | P03–P04, P09 | 010 |
| P11 | Advanced UX methods | P07–P09 | 011 |
| P12 | Interviews, diary and media/transcripts | P08–P11 | 012 |
| P13 | AI evaluations and annotation datasets | P10–P12 | 013 |
| P14 | Product, marketing and business templates | P09–P13 | 014 only if needed |
| P15 | Plans, credits, invoices and reconciliation | P08–P10 | 015 |
| P16 | Team collaboration, API keys and integrations | P09–P15 | 016 |
| P17 | Complete erasure, retention and restore behavior | P04 + all enabled data producers | 017 |
| P18 | Failure, security, load and React contracts | All enabled phases | Index-only fixes if measured |
| P19 | Whole-product acceptance and handoff | P18 | No speculative schema |

Migration groups are logical names, not pre-existing Alembic revision IDs. Keep one Alembic head and generate real revisions as code is implemented. Features like views/templates may need no migration. Do not create unused tables just to match the list.

## 7. P01 — Development foundation

**Build**

- Establish Python package and exact dependency locks; FastAPI/Uvicorn, Pydantic/settings, SQLAlchemy/psycopg, Alembic, auth libraries, OpenAI SDK, pytest/HTTPX and a minimal formatter/linter.
- Create four-service Compose and development override; health checks, nonroot backend, persistent DB/private-files volumes and disposable cache.
- Configure `APP_ENV=development`, `AI_MODE=mock`, separate application and test database names, synthetic seeds, maximum payload/connection limits and explicit secret validation.
- Add app factory, liveness/readiness, safe errors, request IDs and redacted structured logs.
- Build test harness: dependency overrides, deterministic clock/random inputs, temporary asset root and mocked provider. Do not mock SQL for database invariants.
- Make root migrations executable before the runner/API starts accepting study commands.

**Tests:** missing configuration, unsupported mode, unsafe public dev binding, invalid origin, unknown environment variables policy, health with missing DB, no secret logging; Compose renders exactly four services. Boot twice without duplicating schema/seed records. Test process startup and shutdown using a lifespan-aware client.

**Gate:** deterministic health response, clean disposable-DB migration, passing harness and no external network call from tests.

## 8. P02 — Identity, workspaces and grants

**Models:** users, refresh_tokens, one_time_tokens, workspaces, memberships, workspace_invites, study_grants when studies exist, audit_events. Initially attach future grant FK in P05 rather than creating an invalid cycle.

**Code and API**

- Register, verify email, login, refresh rotation, logout, password recovery and session revocation.
- Password hash only; opaque refresh/reset/invite tokens stored hashed, bounded expiry and one-use semantics.
- JWT algorithm/issuer/audience/expiry enforcement; secure-cookie settings and CSRF on cookie-authenticated changes. Local HTTP exceptions must be explicitly development-only.
- Workspace creation/list, staff invitations, role changes and last-owner protection.
- One reusable authorization function checks membership, study grant and capability; participant identity is not a workspace staff role.
- Implement generic error behavior to avoid revealing accounts, private contacts or other workspaces.

**Tests:** expired/tampered/wrong-audience tokens; refresh reuse revokes family; repeated reset; password change invalidates old sessions; two-owner deletion race; user A guesses user B/workspace B IDs; invited/revoked membership cannot act; actor cannot grant more capability than allowed. Assert DB rows contain no raw reset/refresh secret.

**Gate:** role/capability matrix parameterized across owner/admin/researcher/reviewer/viewer/participant/anonymous and two workspaces. No auth bypass for development research APIs.

## 9. P03 — Jobs, cache and idempotency

**Models:** jobs, job_attempts, idempotency_records. No broker/outbox required for ordinary background work.

**Implementation sequence**

1. Persist `jobs(kind,target_id,state,run_after,lease_token,lease_expires_at,attempt_count,max_attempts,requester,workspace_id,command_key)` atomically with the requested domain change.
2. Claim due jobs with a short locking transaction. Increment attempt/fencing token before external work; do not hold a DB connection while waiting on HTTP.
3. Run bounded handlers through the lifespan task loop. Isolate exceptions so one bad job does not kill polling.
4. Save results only when lease/authorization/privacy checks still pass. Graceful shutdown stops claims and drains/cancels safely.
5. Recover expired leases. Distinguish repeatable local work from uncertain cloud actions; unknown external outcome is not automatically retried.
6. Cache scoped aggregates with TTL/version keys; rate-limit security-sensitive actions without treating cache as authoritative.
7. Persist idempotency request hash and receipt. Same actor/key/body replays; same key/different body conflicts.

**Tests:** two claimers, duplicate command, crash before/after commit, stale lease completion, lease renewal, runner exception, server reload, scheduling timezone, cancel pending/running, cache flush, DB down, hot-loop prevention, max attempts, FIFO fairness with bounded priority. Ensure ordinary response save remains fast while a mocked cloud call waits.

**Gate:** pending work survives backend restart and cache deletion; one logical result/charge despite duplicate execution. No unobserved failed asyncio task or second runner from reload.

## 10. P04 — Privacy foundation and assets

**Models:** consent_documents, consent_receipts, retention_policies, privacy_requests, assets, upload_intents, asset_links. Global panel consent and study consent have distinct subjects/purposes; do not attach private contacts to global accounts implicitly.

**Build**

- Immutable localized consent text; record actual displayed version, purpose, receipt and decision. Human-only policy denies AI dispatch.
- Upload intent, streaming body, length/hash/type verification, quarantine and authorized download. Opaque generated storage keys only.
- Define limits for images, CSV, recordings and temporary storage; private backend volume with no public route to arbitrary paths.
- Media processing is bounded; accept supported safe formats, reject unsupported types instead of pretending a scanner exists.
- Create immediate withdrawal restriction and privacy-epoch invalidation before building derivatives in later phases.
- Implement access request and minimal erasure job for currently available data; later phases register their owned derivative deletion actions.

**Tests:** path traversal, symlink escape, extension/MIME mismatch, oversized/malformed files, partial upload, duplicate completion, disk-full failure, unauthenticated/cross-tenant download, revoked share, consent mismatch, optional AI refusal, repeat withdrawal and deletion retry. No contact details in logs/events.

**Gate:** ready assets only are usable; revoked source access is denied immediately even while physical deletion runs.

## 11. P05 — Builder, publication and core methods

**Models:** studies, study_versions, study_grants, launches. Block configuration is typed JSON inside the version; `rules_json` is never returned to participants.

**Build**

- Draft create/edit/clone, optimistic version checks, preview, validate, publish, launch-ready lifecycle.
- Closed method registry with config/value schemas, safe projection, validation, event allowlist and deterministic reducer.
- Initially single/multi/rating/text, preference, five-second exposure and owned/external-link prototype tasks.
- Approved Arabic/French translations and stable option keys; randomized orders persist in the participant session, not regenerated by UI refresh.
- Publication checks all asset permissions, unique keys, reachable acyclic branches, no forward answer dependency, missing locales, private scoring rules and consent requirements.
- Snapshot canonical JSON/hash. Published changes require a new version; in-flight sessions retain the old one.
- Preview uses explicitly nonproduction sessions and never creates rewards, charges, real recruiting or report evidence.

**Tests:** unknown type/version/properties, cycles, dangling branch, hidden-field leakage, duplicate key, unavailable asset, unauthorized clone, concurrent edits, mutation of published config, inconsistent translation keys, unsupported method flag, preview accidentally included in counts.

**Gate:** one draft passes validation, publishes and remains unchanged despite later edits; participant-safe payload excludes all evaluation keys.

## 12. P06 — Panel, screeners, quotas and recruiting

**Models:** participant_profiles, panel_consents, qualifications, private_contacts, private_contact_consents, invitations, candidates, launches, reservations; optional quota_cells/reservation_cells when segment quotas are enabled.

**Build**

- Public panel opt-in/profile editing and separately qualified language skills; no self-asserted verified expertise.
- Workspace private contact import with mapping preview, consent/source provenance, duplicate policy and suppression.
- Eligibility estimates return aggregate counts, not the private panel directory or guarantees of available respondents.
- Freeze candidate attributes/minimum source context at recruitment; shared email in different clients remains separate.
- Issue expiring invitation capabilities and validate screeners server-side. Never expose desired qualifying answers.
- Lock launch plus quota cells in stable order when reserving; include reward commitment and expiry.
- New invitations cannot bypass one-participant-per-launch rule. An open link may require verified identity for compensated studies; a cookie alone cannot guarantee unique people.

**Tests:** incompatible skill/age/device filters, missing optional data, imported duplicate private emails, public/private crossing, shared-device false positives, invite replay, expired token, last-slot race, overlapping quota cells, global launch cap across campaigns, expiry vs submission race, pause/close while invited and insufficient budget.

**Gate:** no quota overbooking and no cross-client private-contact disclosure. Screening compensation policy is explicit.

## 13. P07 — Participant collection

**Models:** sessions, answers, response_events, interaction_attempts. Experiment assignment stays immutable in session JSON initially; use dedicated rows only if subsequent query volume demands it.

**Build**

- Start after consent/reservation, bind version and safe actor capability, resume/next-block, autosave typed answers and final submission.
- Append answer revisions; one logical answer per session/block/occurrence, optimistic write conflicts, explicit current/final pointers without counting revisions as people.
- Event batch dedupe and sequence checks; preserve client-observed versus server-created events and received time.
- Server computes reachable next block from accepted answers. Changing earlier answers invalidates obsolete downstream answers/paths before submission.
- Stable preference order, one exposure attempt and timing interruption status; first-click support follows P11.
- Final submission validates reachable required blocks, records submitted snapshot and queues quality work in the same transaction.
- Give participants accurate saved/unsaved/retry receipts. Network retry must not destroy prior answers or generate another reward.

**Tests:** duplicate PUT/submission, stale expected revision, extra hidden block, wrong version, forged assignment, submission after close, missing required response, skip vs unable, Unicode/surrogate boundary, disconnected retry, event reordering, branch edits, repeated exposure, withdrawn/expired capability and attempted final-answer overwrite.

**Gate:** seeded end-to-end survey finishes exactly once, resumes safely and cannot reveal another participant's result.

## 14. P08 — Review, appeals and participant compensation

**Models:** quality_flags, review_decisions, review_assignments, appeals, reward_records, payout_records, ledger_accounts, ledger_transactions, ledger_entries.

**Build**

- Deterministic rule flags from pinned study policy; short/fast answers are evidence for review, not automatic proof of dishonesty.
- Assigned reviewer views, independent rounds, adjudication and appeal reason/history. No self-review or hidden cross-client reputation score.
- On an accepted result or other earned policy condition, create one reward obligation with a unique source/policy key.
- Record manual payment evidence separately from earning. No money transfer, escrow or bank API is implied.
- Balanced append-only journal with one currency/unit per posting; reversal rather than historical edits. Credits never convert into participant cash automatically.
- Preserve earned obligations through withdrawal/erasure with minimum retained financial data and reviewed retention policy.

**Tests:** repeated acceptance, competing reviewer decisions, failed appeal reopening, disagreement counts, self-review, missing rationale, rejected work without evidence, double reward, negative/overflow amount, currency mismatch, unbalanced journal, duplicate external reference, reversal and payout status after failure. Test exactly one supported full settlement initially; reject unsupported partial settlement explicitly rather than misrecording it.

**Gate:** retrying acceptance/payment commands cannot change total money twice; one human-supported review and appeal lifecycle works.

## 15. P09 — Deterministic analytics and reports

**Models:** analysis_snapshots, snapshot_sources, reports, report_versions, exports, report_shares. Sources include immutable answer revision IDs, digest, consent epoch and exclusion reason.

**Build**

- Freeze source population using a consistent transaction/view and a bounded manifest; repeated queries must not drift midway through a snapshot.
- Implement typed reducers: selection/rating distribution, completion, time-on-task, preference/ties, missingness and later method-specific measures.
- Always provide numerator, denominator, source unit, exclusions and metric version; zero denominator returns null, not fabricated 0%.
- Compare compatible versions/groups, label descriptive differences and suppress small sensitive segments with complementary disclosure checks.
- Draft/approve/revise reports; authorized CSV/JSON first, then XLSX/PDF using confirmed dependencies only when needed.
- Escape spreadsheet formulas and render trusted templates/fonts with network fetching disabled; verify Arabic text visually in browser acceptance.
- Revocable shares return approved redacted summaries, not raw responses/contact identities.

**Tests:** known fixture counts, missing/withdrawn/pending data, multi-select totals over 100%, ties, median even/odd datasets, same person with several answers, before/after changes, source drift, CSV injection, invalidated report, unauthorized raw export, guessed/revoked token and tiny segments.

**Gate:** fixtures independently calculate expected metrics, exports agree with the snapshot, and AI is not required to obtain correct numbers.

## 16. P10 — Cloud AI adapter and bounded analysis

**Models:** ai_runs, ai_attempts, ai_evidence, usage_budgets; cache metadata references immutable runs/snapshots rather than storing a second authoritative result.

**Build**

- One operator-configured OpenAI-compatible provider/client, exact model ID and capability profile. Backend-only secret and approved HTTPS destination.
- Modes: mock for dev/tests, disabled for human-only work, live explicitly enabled with valid configuration and approved data policy.
- Set SDK retries to zero; runner owns bounded retry/cost decisions. Do not assume JSON schema, output parameter, Responses or batch API availability.
- Estimate prompt/output costs with model-specific tokenization where available and conservative bounds otherwise. Reserve study and daily workspace budgets together, in fixed lock order.
- Implement test drafting, themes, failure grouping, translation, report draft, evidence Q&A, sentiment/clarity suggestions and nonbinding quality flags.
- Chunk bounded sources with overlap/deduplication. Record exact coverage; partial retrieval is not an exhaustive study analysis.
- Validate structured output, source IDs and quote spans against permitted immutable originals. Code computes counts; human approval governs claims.
- Cost cache key includes provider/model revision if available, local config revision, prompt/schema, workspace, snapshot and privacy epoch. Do not pretend a cloud model exposes downloadable weight hashes.
- Maintain uncertain attempt state after dispatched timeout; no free-cost assumption, no blind repeated call. Retain conservative budget until reconciliation.

**Tests:** 401/403/404 model mismatch, 429/Retry-After, 5xx, connect-before-send failure vs read-timeout-after-send, malformed/non-JSON, missing usage, truncated output, unsupported argument, leaked source from another workspace, invented quote, malicious prompt in feedback, revoked consent mid-call, double reservation, retry explosion, cache invalidation and provider outage while collection continues.

**Gate:** mock fixtures pass all adapter cases, no keys/prompts leak, ordinary tests make zero paid calls. Live provider compatibility and human dialect quality are separately reported external gates, not needed to develop core collection.

## 17. P11 — Advanced UX methods

Add registry entries without creating separate services. Every method gets publish validation, answer schema, event contract, reducer and fixtures.

| Method | Code behavior | Required edge cases |
|---|---|---|
| Ranking | Unique allowed option keys; configured rank count | Duplicates, missing rank, unknown IDs, partial ranks not counted as last place |
| Constant sum | Every option once; integer nonnegative points; exact sum | Float, overflow, sum off by one, duplicate allocation |
| First click | Pinned asset dimensions, normalized coordinates, first valid event and private AOI evaluation | Letterboxing, resize, orientation, out-of-bounds, NaN, duplicate click, polygon edge/overlap, keyboard mode |
| Card sort | Open/closed/hybrid groups, unique card placement | Missing/unplaced card policy, duplicate groups/cards, unknown category, empty valid category |
| Tree test | Rooted acyclic graph, valid adjacent path, target and backtracking | Broken graph, impossible transition, gave-up vs selected target, detour, unreachable nodes |
| Accessibility issue | Task-linked barrier/impact, optional consented context | No diagnosis requirement; evidence permission; no certification claim |
| Language review | Pinned source, rubric and original/translation separation | Fake quote, wrong language, missing dimension, unsupported numeric score |

React must supply actual browser geometry/visibility/keyboard behavior. Backend-only tests cannot certify exposure timing, screen-reader behavior or cross-origin capture. Public prototype links are self-reported unless an authorized instrumentation adapter exists.

**Gate:** every registry entry passes shared contract tests plus method fixtures; publish denies any method lacking a supported participant renderer.

## 18. P12 — Interviews, diary, recordings and transcripts

**Models:** schedule_slots, bookings, diary_occurrences, notifications, transcript_segments when structured transcript import is enabled.

- Build slot publication, conflict-safe booking, rescheduling/cancellation, attendance and reminder jobs. Store UTC plus IANA zone; join link is private until booking authorization.
- Materialize diary occurrences with open/due/grace timestamps and stable identity. Each occurrence has its own session; no repeated final answer overwrite.
- Accept consented recordings as private evidence. Start with uploaded transcript JSON/text and timestamped segments; a chat model does not automatically transcribe audio.
- If cloud transcription is requested, add an explicitly approved capability and separate pricing/consent; remain inside the existing backend container and bounded cloud job runner.
- Attendance is human/provider evidence, not inferred from opening a meeting link. No conference server or automatic call hosting.

**Tests:** host overlap and capacity races, ambiguous/invalid local time, Africa/Tunis display, cancelled reminder, repeated notification, missing attendance, early/late/grace diary boundaries, skipped days, daylight-saving zones for foreign users, duplicate occurrence creation, wrong session/occurrence, private recording access, invalid transcript span, media budget and refusal of recording consent.

**Gate:** a multi-day synthetic diary and rescheduled interview complete without duplicate entries/reminders; media permissions and deletion propagate.

## 19. P13 — AI evaluation and data annotation

- Build pairwise comparisons with hidden model identities, stable randomized order and explicit tie/both-bad/cannot-judge values.
- Add rubric-based scoring, approved test cases, language review and dataset annotation for classification, text spans and image polygons.
- Use immutable dataset item/label-schema versions. Independent labels precede adjudication; train/evaluation partitions cannot share the same item identity.
- Customer chatbot tests start with authorized sandbox scenarios and fictional inputs. Optional connector accepts only operator-approved destination/credential scope, never arbitrary URLs/tools or production actions.
- Keep model under test, human reviewers and the platform's AI assistant separate. Infrastructure/network failure is not automatically a model task failure.

**Tests:** reveal of hidden identity, permutation/tie errors, invalid rubric, unknown label, Unicode span offset, intersecting forbidden polygon, altered item after labeling, two reviewers not independent, source split leakage, SSRF/redirect/DNS destination bypass, token/time cap, wrong sandbox version, private data in transcript and model-generated votes counted as humans.

**Gate:** reviewed sample dataset exports preserve original labels, adjudication and rights; no live production operations or synthetic human evidence.

## 20. P14 — Product, marketing and business templates

Create versioned template recipes over shared registry types; no new customer-industry response tables.

| Template family | Cases covered | Expected report |
|---|---|---|
| Product discovery | Concept, pricing, competitor, feature ranking | Understanding/preferences with willingness-to-pay caveat |
| Product journey | Onboarding, checkout, registration, full journey | Task-level completion/missingness, self-report provenance |
| Marketing | Ad message, landing page, video, audience, brand, prelaunch offer | Recall, clarity, preference; not guaranteed conversion lift |
| Business | Forms, policies, support scripts, packages, market entry | Observed comprehension and descriptive cohort differences |
| Language/localization | Tunisian Arabic, French, formal Arabic, Arabizi | Reviewer qualifications, original quotes and language-specific outcomes |

**Tests:** instantiate every template, validate it, complete its synthetic participant paths, generate known metrics and redacted report. Assert no duplicate implementations for identical blocks; translating a label cannot change stable IDs or comparison assignment.

**Gate:** all requested use cases appear in a template/feature catalogue with an enabled method and matching acceptance fixture.

## 21. P15 — Commercial billing and usage

**Models:** plans/plan versions as configuration snapshots, subscriptions, usage_events, invoices, invoice_lines, customer_payments; reuse the P08 ledger rather than a second accounting engine.

- Add pay-per-study/response, team-plan allowances, specialist surcharges and AI add-on pricing with frozen rate/currency/tax metadata.
- Record grants/reservations/consumption, visible usage meters and manual customer payment evidence; no card storage or bank automation.
- Separate provider AI cost from customer selling price and participant pay. Mixed currencies cannot be summed without an explicit frozen conversion record.
- Preserve original invoice and credit/reversal history; price changes affect future purchases only.
- Implement finite operational quotas even if a plan advertises unlimited publishing; disclose scope and do not promise infinite storage/AI.

**Tests:** allowance boundary/race, same response charged twice, snapshot price after plan change, cancellation dates, wrong currency/exponent, tax metadata absent, duplicated manual payment, over/underpayment policy, reversal, unpaid invoice and negative balance policy. Validate TND millime arithmetic independently.

**Gate:** manual records reconcile without moving money; commercial activation requires reviewed local invoice/payment rules.

## 22. P16 — Collaboration, APIs and integrations

**Models:** api_keys, report_comments, integrations, webhook_deliveries; notifications already exist from P12.

- Add scoped API credentials, shared templates, comments, granted report views and notification preferences.
- Add outgoing webhooks using stable delivery IDs, timestamped HMAC signatures and bounded retries; deliveries are ordinary DB jobs.
- Design links can work without fetching the page; a richer Figma/design connector needs its actual vendor API/permissions and is gated until configured.
- Provide calendar ICS exports locally; optional external synchronization uses approved connector capabilities, not another container.
- In-app notification records and dev console capture first; approved SMTP can be configured later without a local email service requirement.

**Tests:** key scope/revocation, stale member rights in queued job, comments exposing raw answers, replayed signature, destination redirect/private IP, duplicate delivery, vendor rate limit, secret leak, revoked integration, suppressed contact and stale calendar event.

**Gate:** no integration enables itself on upgrade or bypasses study data/consent restrictions.

## 23. P17 — Complete privacy, retention and restore

- Audit each data producer: identity, private panel, answers/events, recordings, transcripts, annotations, snapshots, AI sources/results, cache, exports, shares and notification attempts.
- Register owned deletion/invalidation handlers and test their dependency order. Do not hide retained personal content in JSON audit fields or deletion manifests.
- Immediate privacy restriction/epoch update precedes asynchronous purge; in-flight cloud jobs cannot publish old results.
- Retention and legal holds require reason, scope and review time. Financial minimum retention does not authorize retaining all raw research.
- Backups record privacy tombstones; restore into an isolated DB/files destination, replay restrictions and verify before serving.
- Document provider-side deletion limits; completed cloud calls cannot be retroactively made local or guaranteed forgotten.

**Tests:** repeated erasure, missing file, failed cache deletion, in-flight export, held financial record, linked source in several reports, restored revoked share, audit metadata leakage and participant request for another account.

**Gate:** a seeded subject is inaccessible across all derived outputs immediately and is physically purged according to policy; isolated restore preserves restrictions.

## 24. P18 — Development reliability and React contract tests

- Generate and review OpenAPI, consistent error schema and typed request examples. Use one canonical answer protocol from Section 3.
- React contract fixtures exercise registration, researcher study creation, participant completion, review, report and async AI status without implementing backend assumptions in UI.
- Expose only frontend publicly; test frontend proxy, cookie paths, CSRF, CORS, large body limits and revoked login.
- Stress one backend process with simultaneous response writes and a waiting mock LLM. Measure p50/p95 latency, queue age, DB pool usage and memory; define load against this hardware rather than inventing a production capacity.
- Test DB restart, cache flush, backend reload, job loop exception and full disk. Install no extra load-test service.
- Inspect dependencies/secrets, HTML/template/CSV injection, permissions, parser resource limits and SSRF.

**Gate:** no lost accepted submissions, no duplicate rewards, no cross-tenant read, no cloud spend in default tests and no fifth Compose service. Performance numbers are reported with hardware, payload, concurrency and duration.

## 25. P19 — Final full-product acceptance

Run these end-to-end stories against a clean migrated test database:

1. Workspace A creates French/Arabic preference study, recruits a public-panel participant, collects, reviews, rewards, builds metrics and approves cloud-assisted report.
2. Workspace B imports private contacts; A cannot discover them through APIs, search, AI, exports or matching email.
3. A participant loses network during autosave and retries after reload; one logical answer/submission/reward remains.
4. Two users request the last slot; one succeeds, the other receives a clear nonchargeable capacity result.
5. A diary participant completes several windows, misses one and withdraws; missingness and earned pay remain correct.
6. A design study exercises click geometry, tree backtracking, card grouping and keyboard alternatives; reports do not claim formal accessibility certification.
7. AI returns invented sources, then provider fails; collection continues, the false output stays unapproved and budget status is explicit.
8. A consent withdrawal occurs during cloud inference/export; final writes are fenced, shares revoked and deletion handlers run.
9. Invoice, software credit, AI cost and participant payout remain separate and idempotent across retries.
10. Restore a backup into an isolated target and verify data, private files, revocations and balanced journals before access.

**Final evidence:** phase log, model/test inventory, actual test outputs, migration history, approved OpenAPI, known limits, unresolved vendor/legal gates and measured performance. Do not label disabled integrations, unsupported browser behavior or unrun live-provider tests complete.

## 26. Shared model and API test obligations

Every implemented table gets: create valid row, reject missing/invalid fields, reject invalid FK, verify unique keys including NULL behavior, cross-tenant relationship attack, update rules, delete/retention behavior, relevant concurrency and migration round-trip on disposable data.

Every write endpoint gets: happy path, no authentication, wrong role, wrong workspace, unknown object, boundary/oversized/malformed body, stale revision, duplicate request, transaction rollback and safe error logging. Reads get pagination/filter/ordering and denied-field assertions. Snapshot/derived reads also get revocation and stale-cache tests.

Use real independent DB transactions for races. A single test transaction with rollback cannot prove worker visibility or locking. A fixture must tear down only its owned temporary data, even when setup fails. Never point tests at the ordinary development DB.

### Matrix of synthetic fixture groups

| Fixture | Must include |
|---|---|
| Actors | Two workspaces, each staff role, revoked/invited members, participant also a researcher, anonymous invite |
| Identity | Duplicate normalized emails, valid French/Arabic names, expired/replayed tokens |
| Studies | Draft/published/paused/closed, old/new version, invalid graph, all block kinds |
| Participants | Public opt-in, private contact in two clients, missing optional demographic fields, declined AI consent |
| Sessions | Partial, submitted, reviewed, rejected, appealed, withdrawn, expired, test-only |
| Time | Exact boundary timestamps, leap date, UTC/Tunis and daylight-saving foreign zone, backend restart |
| Text/media | Arabic, French, Arabizi, emoji/code-point spans, very long text, empty/invalid media, malicious markup |
| AI | Valid JSON, bad JSON, valid schema with false citation, partial usage, unknown outcome, long wait |
| Money | Zero allowed where appropriate, smallest TND unit, negative/overflow, duplicate and reversed payment |

## 27. Test organization and commands

Planned directories under `/Users/user/Workspace/startup-act/backend/tests/`:

- `unit/`: pure validators, reducers, price arithmetic, canonical hashes and redaction.
- `db/`: model constraints, migrations, row locks, retention and ledger triggers.
- `api/`: route schema/auth/permission/idempotency coverage.
- `jobs/`: lifecycle, lease, retry, cancellation and restart behavior.
- `contracts/`: every research block and cloud adapter response variant.
- `integration/`: full PostgreSQL-backed workflows and cache behavior.
- `security/`: tenant/source isolation, injection and secret checks.
- `e2e/`: complete stories; browser interaction checks coordinated with React.

Register pytest markers `unit`, `db`, `api`, `jobs`, `contract`, `integration`, `security`, `e2e`, `live_llm`, `load`. Unknown markers fail. Ordinary defaults exclude live cloud/load tests and prohibit external egress. API TestClient uses its context manager so lifespan is actually tested; HTTPX clients require explicit equivalent lifecycle handling.

The commands below are **future commands after P01 creates the app and Compose files**, not commands already run by writing this plan. Backend working directory is `/app/backend`.

```sh
docker compose --project-directory /Users/user/Workspace/startup-act -f /Users/user/Workspace/startup-act/compose.yaml -f /Users/user/Workspace/startup-act/compose.dev.yaml config --services
docker compose --project-directory /Users/user/Workspace/startup-act -f /Users/user/Workspace/startup-act/compose.yaml -f /Users/user/Workspace/startup-act/compose.dev.yaml up -d --build
docker compose --project-directory /Users/user/Workspace/startup-act -f /Users/user/Workspace/startup-act/compose.yaml -f /Users/user/Workspace/startup-act/compose.dev.yaml exec -T backend python -m alembic upgrade head
docker compose --project-directory /Users/user/Workspace/startup-act -f /Users/user/Workspace/startup-act/compose.yaml -f /Users/user/Workspace/startup-act/compose.dev.yaml exec -T backend python -m pytest -m "not live_llm and not load"
docker compose --project-directory /Users/user/Workspace/startup-act -f /Users/user/Workspace/startup-act/compose.yaml -f /Users/user/Workspace/startup-act/compose.dev.yaml exec -T backend python -m ruff check /app/backend
docker compose --project-directory /Users/user/Workspace/startup-act -f /Users/user/Workspace/startup-act/compose.yaml -f /Users/user/Workspace/startup-act/compose.dev.yaml exec -T backend python -m ruff format --check /app/backend
```

Use the same explicit Compose file set for all commands if an override changes execution context; P01 should provide a small tested wrapper to eliminate command drift. The test runner resolves a dedicated `TEST_DATABASE_URL`, refuses the application database name and verifies a destructive-test guard before migration/reset. Run tests with the default background loop disabled, except explicit lifespan/runner tests that own their jobs; a live application runner must never consume test jobs.

Migration tests cover clean upgrade to head, upgrade from each supported preceding release with fixtures, invalid data backfill failure, downgrade only where safe, and code rollback compatibility. Destructive migrations require backup/restore rather than a false promise of reversible deletion.

## 28. Completion checklist and boundaries

- [ ] Every phase has an actual implementation/evidence entry.
- [ ] Every implemented table is represented in the model/test inventory.
- [ ] Every enabled method has config, value, private projection, event, reducer and test coverage.
- [ ] All roles/capabilities and cross-tenant paths are tested.
- [ ] No unsupported frontend renderer can be published.
- [ ] Cloud compatibility and price settings are confirmed before live calls.
- [ ] Budget/compensation/idempotency race tests pass.
- [ ] Privacy reaches caches, files, reports and in-flight jobs.
- [ ] Four containers remain the only application services.
- [ ] Full tests and migration/restore checks are recorded honestly.
- [ ] Unrun vendor, browser, legal and performance checks are listed as outstanding.

No provider/model has been supplied yet. Core development proceeds with a mock; live credentials must be set privately, never requested in a committed document. Research method limitations, legal permissions and representative sampling cannot be proven by backend tests alone.

## 29. Primary references and current validation status

- FastAPI lifespan-aware tests: https://fastapi.tiangolo.com/advanced/testing-events/
- Pytest fixture isolation/cleanup: https://docs.pytest.org/en/stable/how-to/fixtures.html
- FastAPI lifespan: https://fastapi.tiangolo.com/advanced/events/
- SQLAlchemy sessions: https://docs.sqlalchemy.org/en/20/orm/session_basics.html
- PostgreSQL locking: https://www.postgresql.org/docs/16/sql-select.html
- OpenAI-compatible client configuration: https://github.com/openai/openai-python

The original planning task created this plan and static documentation checks only. Subsequent P01–P05 implementation evidence is recorded separately in `docs/backend/IMPLEMENTATION_STATUS.md`; the remaining phase checklists are not executed results. No live cloud validation is claimed.
