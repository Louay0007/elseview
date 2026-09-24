# Elseview — Implementation status

**Brand:** Elseview — See what you’re missing.

## Audit remediation — September 24, 2026

The nine reported defects are corrected: scoped restore replay, bidirectional
hold reconciliation, held AI retention eligibility, starvation-free asset batching,
coordinated AI request-body dispatch, never-dispatched retry, blind-review eligibility,
cross-workspace participant booking serialization, and recycled included billing
allocations in both application and SQL enforcement.

Additional privacy work adds unlinked-contact holds/erasure, bounded producer
retention, financial-preserving study/template minimization, and password-confirmed
self-service global account erasure with capability-protected status recovery.
Current signed manifests preserve global account restrictions as well as scoped
events and both contact/subject holds. Earlier P17 completion language should be
read with the corrected scope and limits in `AUDIT_REMEDIATION.md`.

Executed validation: **854 passed**, **zero skipped**, **1 load test deselected**,
**92% statement coverage**, 216.36 seconds. The guarded load test was separately
run and **passed**. Focused privacy clone/backup checks: **32 passed**; final
lifecycle and migration checks: **13 passed**; real account API checks passed.
Lint/format, compilation, dependency consistency, OpenAPI drift and Alembic schema
checks passed. All four containers healthy and readiness successful.

Application database backed up before applying new migrations **018–022**; current
head is **`022_account_erasure`**. Applied migrations through 017 were not rewritten.
AI remains mocked; integrations disabled; no money transfers or paid calls occurred.

Important boundaries: the request-body dispatch gate requires the planned single
backend process and coordinated application writes; it cannot recall network-buffered
bytes or provider processing. Legacy independent assignments are not retroactively
certified blind. Historical zero-price billing allocations are deterministically
canonicalized without repricing existing records. Global account erasure preserves
minimal consent/financial identifiers and cannot bypass outstanding holds/rewards
or last-owner transfer requirements. No legal/vendor/production certification claimed.

Details: `/Users/user/Workspace/startup-act/docs/backend/AUDIT_REMEDIATION.md`.
No commit or push performed; pre-existing work preserved.

## P18/P19 — Reliability and acceptance, September 24, 2026

### Delivered and verified

- Checked-in deterministic OpenAPI for 167 paths, actual authentication schemes,
  canonical safe error envelopes, request examples/types and contract drift tests.
  Success projections without response models remain explicitly unconstrained.
- Thin React API client and accessible diagnostic workbench; registration 422
  correction, stable mutation retries, report reload, async AI status error/retry,
  canonical collection autosave replay/submission/remount tested in real Chrome
  with mocked HTTP responses. No client-side business rules were substituted.
- Fixed Vite proxy prefix (`/api/`) so frontend API-named modules are not proxied.
  New Node regression test protects the boundary. CDP runner uses installed Chrome
  and Node built-ins, blocks nonlocal page requests, and cleans its own profile.
- Explicit guarded load entry point, aggregate hardware/payload/pool/queue/RSS
  measurements, low-disk and job-loop failure tests. Four sessions, 48 durable
  autosaves and four once-only submissions progressed during blocked mock inference.
- Three coherent P19 backend acceptance workflows and ten-story test map. Restore
  test now seeds a nonzero balanced journal and verifies exact retained postings;
  replay refuses readiness for incomplete/unbalanced transactions.

### Actual results

- **798 passed, zero skipped, 1 load test deselected**, **92% statement coverage**,
  198.72 seconds. The excluded load test was run separately and **passed**.
- Final focused P19/restore run: **4 passed**. Frontend **11 Node tests passed**,
  production build passed, **4 Chrome fixture pages passed** (new workbench checks
  17 mocked requests). These are browser contract tests, not full browser/DB E2E.
- Load: p50 **63.24 ms**, p95 **123.02 ms**, 1.048-second measured write window,
  four concurrent sessions; TestClient topology and container-visible hardware
  are documented in `P18_RELIABILITY.md`. Not a sustained capacity claim.
- Backed up local application database, restarted actual PostgreSQL/cache/backend
  containers, verified readiness recovery and unchanged durable row counts.
- Ruff lint/format, compileall, dependency consistency, OpenAPI drift and Alembic
  checks passed. **No migration required**; head remains `017_privacy_ops`.
  No new dependencies/services, no paid cloud traffic or integration activation.

### Explicit incomplete gates

P19 is not unconditional full-product sign-off: a combined authenticated browser
journey across every story, full keyboard/screen-reader certification, live
provider/dialect validation, production encrypted/offsite archive restoration,
vendor deletion guarantees and legal/tax approval remain unverified. The diagnostic
workbench does not replace a finished product dashboard. See
`/Users/user/Workspace/startup-act/docs/backend/P18_P19_ACCEPTANCE.md` and
`/Users/user/Workspace/startup-act/docs/backend/P19_ACCEPTANCE.md` for exact scope.
Prior uncommitted work preserved; no commit/push performed.

## P16 and P17 — Development implementation, September 24, 2026

- P16 hash-stored scoped API keys, explicit report/template grants, raw-only report
  comments, participant notification preferences, revision-aware local ICS and
  metadata-only HMAC webhook jobs with bounded retry and disabled-default settings.
  Current membership, grant issuer authority, source restrictions and privacy epoch
  are revalidated. Live transport is opt-in; no vendor synchronization is enabled.
- P17 reviewed retention/holds, ordered producer erasure, raw JSON audit cleanup,
  conservative shared-data preservation under legal hold, settled financial
  beneficiary minimization and immediate access restriction before asynchronous purge.
  Raw/derived/export sweeps and existing asset sweep remain source/policy bounded.
- Version-2 signed tombstone/active-hold manifests; private-file inventory and
  database archive digests; isolated restore replay with matching nonce receipt.
  Both API and background worker quarantine restored databases before replay.
  New post-snapshot holds require operator reconciliation before destructive replay.

### Executed evidence

- Full PostgreSQL/cache/backend regression: **783 passed**, **zero skipped**,
  **92% statement coverage**, 191.06 seconds.
- Final focused collaboration/privacy/restore/backup tests: **44 passed** after
  tightening notification preference tenant scope. Real physical PostgreSQL clone
  test verifies post-snapshot restriction, revoked grants, raw-comment/file purge,
  missing-file replay, storage failure, missing current hold and marker quarantine.
- Ruff lint/format, compileall, pip dependency check, migration roundtrip and
  Alembic schema checks pass. Local schema upgraded from `015_billing` through
  `016_collaboration` to **`017_privacy_ops`**, after owner-only database backup.

### Boundaries and operations

No production legal, encrypted-backup or provider-side erasure certification.
Workspace erasure does not destroy global identity shared with other tenants.
The generic Redis aggregate helper has no production consumers; future consumers
must add explicit invalidation. Cloud requests already sent cannot be recalled.
The routine restore test is a physical PostgreSQL TEMPLATE clone, not a pg_dump
format drill. External PostgreSQL client/archive/encryption workflows are operator
prerequisites. The development-only test role now has CREATEDB for unique disposable
restore clones; runtime/migration roles do not. Restored DBs must remain isolated
until current signed restrictions/holds have been reconciled and replayed.
No new collaboration UI, SMTP, Figma or external calendar connector was claimed.
AI remains mocked and outgoing integrations remain disabled.

Contracts/runbook: `/Users/user/Workspace/startup-act/docs/backend/P16_P17_API.md`.
Producer inventory: `/Users/user/Workspace/startup-act/backend/app/privacy_ops/AUDIT.md`.
All prior uncommitted work preserved; no commit or push performed.

## P14 and P15 — Development implementation, September 23, 2026

### Delivered

- P14 versioned catalogue covering all 23 requested product discovery/journey,
  marketing, business and localization cases. Recipes reuse enabled shared methods;
  stable block/option IDs remain unchanged by translation. Required real assets,
  consent/retention policy, approved-label references and localization reviewer
  attestations are validated before creating a draft.
- Distinct purpose-specific prompts, four-stage journey tasks, comparison/ranking,
  language-review rubrics and original quotes; explicit willingness-to-pay,
  self-report, dialect and video-storyboard limitations. Immutable recipe hashes,
  configuration hashes and input provenance without duplicate response tables.
- P15 reviewed immutable plan versions, nonoverlapping subscriptions, explicit
  cancellation cutoff, included allowances, quota grants, finite operational limits
  and committed budgets. Never-activated development workspaces remain unbilled;
  cancelled/expired commercial workspaces cannot obtain new usage for free.
- Atomic publication, response/diary start-submit, withdrawal/expiry and AI add-on
  reservation/consumption hooks. Customer selling price is independent of Decimal
  provider cost and participant rewards. Old reservations retain frozen terms;
  permanent source uniqueness prevents duplicate charging.
- Immutable invoices/lines, rational half-up tax arithmetic, TND exponent 3, exact
  full manual settlement, evidence digests, separate reversal/credit records and
  visible usage/quotas. Reuses P08 ledger with commercial account codes, not a second
  accounting engine. SQL guards enforce prices, totals, journal topology and history.

### Files and migrations

Modules: `/Users/user/Workspace/startup-act/backend/app/templates/` and
`/Users/user/Workspace/startup-act/backend/app/billing/`, with shared publication,
collection/diary, AI and privacy-release hooks. New migrations:
`013_evaluation → 014_templates → 015_billing`. Tables: `template_instances`,
`billing_plan_versions`, `billing_subscriptions`, `billing_grants`, `billing_usage`,
`billing_invoices`, `billing_invoice_lines`, `billing_customer_payments`.
Earlier applied migrations remain unchanged; existing uncommitted work was preserved.

API contracts: `/Users/user/Workspace/startup-act/docs/backend/P14_P15_API.md`.

### Executed evidence

- Baseline **622 passed**, zero skipped, 81.10 seconds.
- P14 **25 unit + 24 database tests** passed: every recipe traverses actual HTTP
  instantiate/publish/participant response/human acceptance/known metrics/redacted
  report, plus tenant, idempotency, provenance and atomic-invalid-input checks.
- Initial billing focused suite **61 passed**; expanded billing/migration suite
  **93 passed**, including real publication, collection, AI sale, withdrawal/expiry,
  allowance/payment races, cancellation and invoice/reversal guards.
- **Final full guarded regression: 739 passed, zero skipped, 93% statement coverage,
  192.60 seconds.** Log:
  `/Users/user/Workspace/startup-act/.tools/p14-p15-final.log`.
- Ruff lint/format checks pass across 145 Python files; compilation, `pip check`,
  migration round-trip and schema drift checks pass. Fixed a PL/pgSQL ambiguous tax
  reference and missing template workspace index found by executed tests.
- Private local application database backup created under
  `/Users/user/Workspace/startup-act/.tools/p14-p15-backup/` before upgrade; archive
  structure validated with `pg_restore --list`, not a complete restore drill.
  Application schema is at `015_billing`; Alembic reports no new upgrade operations.
- Live readiness succeeds; all four containers are healthy. Runtime AI remains
  `mock` and the application database has **zero commercial subscriptions**. No
  activation, paid provider request or money transfer occurred.

### Explicit limits

- No new template/billing dashboard; API workflows reuse existing participant
  renderers. Video is a storyboard/key-frame content proxy, not playback analytics.
  Translation/reviewer qualification references are attestations, not certification.
- Commercial rules, supplier/customer/tax references and retention interval must be
  explicitly reviewed by an operator; no local tax/legal compliance validation is
  claimed. Financial history retains opaque references, not research answers. The
  retention interval is a snapshot, not an implemented financial purge engine.
- TND integer millimes only; full settlement and full credit/reversal only. Mixed
  currencies, wrong exponent, over/underpayment and unsupported conversion are
  rejected. There is no card storage, bank automation, FX, escrow or wallet overdraft.
- Quota grants extend finite caps, not cash. AI selling price does not erase unknown
  provider charges. Reserved pre-cancellation work is fulfilled under its old terms.
- Rollback drops phase commercial tables while preserving historical P08 journal
  rows under the older account vocabulary's NOT VALID constraint. Backup and an
  explicit retention decision are required before downgrading a populated deployment.
- No commit, push or public-production deployment was made.

Older phase sections below are historical checkpoints, not current scope statements.

## P12 and P13 — Development implementation, September 23, 2026

### Delivered

- P12 future interview slots with UTC instants/IANA zone and explicit DST-fold/gap
  validation; serialized host/participant overlap and capacity checks; private
  consent-bound join links; booking revision/cancellation/rescheduling; attributed
  staff attendance with actor and server timestamp, never inferred from link access.
- Durable revision-bound in-app reminder jobs with completion-time authority checks,
  duplicate-safe delivery markers and a participant inbox. No email/SMS send claim.
- Immutable diary series and separate occurrence sessions, core-survey-only prompts,
  server open/due/grace enforcement, late/missed status, independent final answers
  and complete-series once-only reward identity. An out-of-order human acceptance
  test proves no reward until all sessions are accepted and one obligation afterward.
- Exact participant recording consent plus existing uploader private-storage consent;
  ready WAV evidence, immutable plain/segmented transcripts, scoped downloads,
  immediate revocation and linked physical-file erasure. Metrics distinguish
  occurrence completion from participant retention and retain unknown attendance.
- P13 immutable dataset/schema/item versions with rights, canonical content identity
  and train/evaluation split protection; blind stable pairwise assignments, rubric
  and language review, classification/Unicode spans/private-PNG polygons, independent
  originals followed by fresh adjudication and digest-reviewed exports.
- Manual fictional sandbox scenarios with revision/turn/duration/character bounds;
  infrastructure failures remain separate from evaluable model outcomes. Human
  provenance is server-attributed; AI-generated votes cannot be submitted as humans.
- Native React participant schedule and evaluation workbench forms, Unicode offset
  helpers, pointer/numeric-keyboard polygon entry and frozen retry payloads. These
  are standalone workflows, not falsely enabled unsupported study-registry methods.

### Files and migrations

New backend modules: `/Users/user/Workspace/startup-act/backend/app/longitudinal/`
and `/Users/user/Workspace/startup-act/backend/app/evaluation/`; shared integration
extends collection diary identity, rewards, jobs, optional consent, privacy and study
cleanup. New React components are `LongitudinalRunner.jsx` and `EvaluationRunner.jsx`
under `/Users/user/Workspace/startup-act/frontend/`, with `researchHelpers.js` tests.
Existing uncommitted changes were preserved; no commit or push was made.

Additive chain: `011_methods → 012_longitudinal → 013_evaluation`. P12 tables:
`schedule_slots`, `bookings`, `diary_occurrences`, `notifications`, `recordings`,
`transcript_segments`; collection adds an optional occurrence FK and separate base/
occurrence uniqueness. P13 tables: `evaluation_datasets`, `evaluation_identities`,
`evaluation_items`, `evaluation_assignments`, `evaluation_outcomes`,
`evaluation_export_reviews`. Applied earlier migrations were not rewritten.

### Executed evidence

- Baseline: **548 passed**, zero skipped, 43.64 seconds.
- Initial combined P12/P13 focused suite: **66 passed**, 5.74 seconds.
- Expanded P12 focused suite: **20 passed**, 6.62 seconds, including real human
  complete-series acceptance/reward and attributed attendance tests.
- **Final guarded regression: 622 passed, zero skipped, 93% statement coverage,
  146.30 seconds.** Log:
  `/Users/user/Workspace/startup-act/.tools/p12-p13-final.log`.
- Lint/format checks pass for 128 Python files; compilation and `pip check` pass.
  Migration downgrade/upgrade and metadata consistency pass. Frontend production
  build passes and combined geometry/Unicode Node suite has **5 passing tests**.
- Chrome headless synthetic DOM smoke exercised schedule booking/reschedule/cancel/
  diary display and evaluation forms/Unicode selection/unknown-judgment/private image.
  Chrome required timeout termination after 20 seconds; passing DOM assertions do
  not imply a clean browser-process exit or authenticated browser E2E certification.
- Backed up local application database before applying 012/013 to the private ignored
  `/Users/user/Workspace/startup-act/.tools/p12-p13-backup/` directory; archive structure
  validated with `pg_restore --list`, not a full restore drill. Application schema
  reached `013_evaluation` and `alembic check` found no new upgrade operations.
- Backend/frontend images rebuilt successfully; all four existing containers are
  healthy. Live `127.0.0.1:8080/api/v1/health/ready` returns ready and runtime AI
  mode remains `mock`.

### Explicit development limits

- No conference hosting, email/SMS provider, cloud transcription or external chatbot
  connector. Reminders are in-app; transcripts/sandbox turns are uploaded manual
  material, not verified recognition/model output. External destinations and adapter
  mode are disabled. No live production actions or paid calls occurred.
- Diary v1 repeats the full published core-survey version after initial participation;
  it does not yet provide a separate initial questionnaire and diary prompt subset.
  UTC instants are frozen, but an explicit tzdata release identifier is not retained.
- Host/capacity exclusion is enforced by serialized service writes and tested HTTP
  races, not a PostgreSQL exclusion constraint. Direct SQL is not an application API.
- Rollback of 012 drops phase-owned diary occurrence responses before restoring the
  old candidate uniqueness rule; never downgrade a populated deployment without an
  explicit backup/data-retention decision. Initial participation and earned financial
  obligations are retained.
- Dataset rights and manual fictional-input assertions are operator declarations,
  not automatic legal or comprehensive PII validation. Language/rubric scoring does
  not certify specialist medical/legal/financial competence. Agreement is not truth.
- UI tokens/capabilities remain in memory; complete reload requires original diary
  credentials. Full authenticated browser E2E, device keyboard/pointer behavior,
  screen-reader traversal and accessibility certification remain unverified.

Usage: `/Users/user/Workspace/startup-act/docs/backend/P12_P13_API.md`.
Older phase sections below are historical checkpoints, not current scope statements.

## P10 and P11 — Development implementation, September 23, 2026

### Delivered scope

- P10 async OpenAI-compatible Chat Completions adapter using the installed SDK's
  HTTPX2 transport, zero SDK retries, no redirects/environment proxies, explicit
  model/output-format capabilities and fail-closed live host/privacy/pricing gates.
- Durable `ai.generate` jobs, Decimal study/UTC-day budget reservations, committed
  dispatch markers, known-rejection versus uncertain-outcome handling, Retry-After,
  bounded explicit safe retry and operator charge reconciliation. No cloud calls
  occur inside database transactions; ordinary tests use mock responses.
- Nine task-specific assistance operations share a strict draft findings/evidence/
  limitations schema. Snapshot input requires exact version-bound optional AI
  consent. Outputs retain covered spans, immutable quote evidence, partial-context
  labels and code-computed source counts. Cached results are persisted run references
  with live permission/consent/source checks, not an independent authoritative copy.
- P11 ranking, constant sum, first click, card sorting, tree testing, accessibility
  issues and language review: strict configurations/values/events, pinned assets,
  private evaluation projection, publication validation and deterministic reducers.
- First-click collection uses a server-latched first valid event with uniqueness,
  immutable coordinates and exact answer matching; pointer and keyboard-cursor
  modes remain distinct. Polygon boundaries/overlap and navigation graph/path rules
  have explicit tests. Optional accessibility context has exact consent checks.
- Actual React renderers, contain/letterbox geometry helpers, keyboard controls and
  a minimal existing-session runner with scoped asset loading and retry receipts.
  Published advanced methods are enabled only after renderer exports were verified.

### Files, migrations and operational state

Code: `/Users/user/Workspace/startup-act/backend/app/ai/`,
`/Users/user/Workspace/startup-act/backend/app/studies/advanced.py`, shared study/
collection/analytics/job integration, and
`/Users/user/Workspace/startup-act/backend/app/common/participant_consent.py`.
React: `/Users/user/Workspace/startup-act/frontend/AdvancedMethods.jsx`,
`/Users/user/Workspace/startup-act/frontend/CollectionRunner.jsx`, preview integration
and geometry tests. No dependency or fifth service was added.

Additive migrations `009_analytics → 010_ai → 011_methods` create `ai_runs`,
`ai_attempts`, `ai_evidence`, `usage_budgets`, first-click SQL guards and optional
consent scope support. Existing applied 001–009 migrations were not rewritten.
011 rollback retains historical new-purpose consent records using a NOT VALID
older-vocabulary check rather than silently deleting consent history.

The local database was backed up under private ignored
`/Users/user/Workspace/startup-act/.tools/p10-p11-backup/` before upgrade. Archive
structure was checked with `pg_restore --list`; this is not a full restore drill.
Both application migrations were applied; one head `011_methods`, no Alembic
metadata drift. Backend/frontend images rebuilt, all four containers healthy;
live `127.0.0.1:8080/api/v1/health/ready` returns ready and runtime AI mode is **mock**.
Existing uncommitted edits were preserved. No commit, push or public deployment.

### Executed evidence

- Baseline: **453 passed**, zero skipped, 42.20 seconds.
- Focused P11: **49 passed**, including 15 real PostgreSQL/API cases, 4.14 seconds.
- Focused AI/optional consent: **46 passed**, including SDK mock transport, actual
  embedded runner, HTTP approval/access, concurrent budget reservations and
  revoked-consent dispatch fencing, 3.31 seconds.
- **Final guarded backend regression: 548 passed, zero skipped, 94% statement
  coverage, 70.30 seconds.** Log:
  `/Users/user/Workspace/startup-act/.tools/p10-p11-final.log`.
- Ruff lint and formatting passed across 109 Python files; compilation, `pip check`,
  migration round-trip and schema drift tests passed. Frontend production build
  passed; Node geometry suite **3 passed**.
- Installed Chrome headless synthetic renderer smoke produced a PASS DOM for seven
  mounts, ranking interaction, issue editor insertion and blob image loading.
  Chrome required timeout termination after 18 seconds; this is not a successful
  clean-process browser run. Details are in
  `/Users/user/Workspace/startup-act/frontend/tests/README.md`.

### Remaining acceptance gaps and limits

- No live provider compatibility, account, key, spend or dialect-quality evaluation.
  Capabilities/prices/privacy terms require external operator verification. Regex
  email/phone redaction is not comprehensive PII detection. The shared assistance
  output schema and task prompts do not guarantee semantic correctness or immunity
  to prompt injection. No cloud audio, external tools or automatic quality rejection.
- One dispatch per durable AI job; at most two explicit attempts for a known safely
  retryable identical request. Uncertain outcomes retain budget until reconciliation.
- Accessibility evidence uploads are not enabled; optional consented context is.
  Language-review basis is disclosed as unverified participant self-report, not a
  professional qualification certification.
- The minimal participant runner resumes already-created/consented sessions. It
  supports advanced methods and core surveys/preference/prototypes; real five-second
  browser collection remains explicitly unsupported in that runner. Recruitment,
  start and optional-consent grants are separate API operations.
- Full authenticated browser E2E, real pointer/keyboard/device orientation/visibility,
  network-loss recovery, screen-reader traversal and accessibility conformance have
  not been certified. Geometry/backend tests and a smoke DOM are not substitutes.

Contracts: `/Users/user/Workspace/startup-act/docs/backend/P10_P11_API.md`.
Older phase sections below are historical checkpoints, not current scope statements.

## P08 and P09 — Development implementation, September 23, 2026

### Delivered

- P08 deterministic quality flags from pinned private study policy; assigned blind
  independent review rounds, disagreement/adjudication, participant appeal/history,
  self-review prohibition and bounded administrative/reviewer/participant views.
- Nonzero accepted offers create one reward obligation and earning journal. Manual
  full payment, failed attempts, idempotent retries, unique external references and
  exact reversal postings remain separate from earning. Deferred PostgreSQL guards
  enforce balanced immutable journals and matching obligation/payment state.
- Explicit operator-reviewed financial retention policy, minimum beneficiary
  retention for open obligations and bounded settled-identity minimization. Research
  withdrawal/erasure does not destroy earned obligations. Reversal after beneficiary
  minimization is rejected rather than creating an unidentifiable payable.
- P09 bounded locked snapshots of final accepted response revisions, source digests,
  exact consent and review-generation context, pinned exclusions and typed metrics.
  Rates/medians/timing/missingness have declared denominator, source unit and provenance.
- Draft/approve/new-version reports, authorized JSON/CSV summary/raw exports, Unicode
  and spreadsheet-formula handling, expiring/revocable hashed report shares with a
  strict numeric-summary projection and live issuer/source permission rechecks.
- Small/complementary cell suppression plus release-history checks across individual
  snapshots/reports/summary exports/shares, including stored invalidated snapshots.
  Overlapping changes of fewer than five sessions suppress the whole nonraw summary.
- Privacy hooks invalidate on withdrawal and purge overlapping report/source trees
  before response erasure; owner-study cleanup also handles empty snapshots.

### Files and schema

New code is under `/Users/user/Workspace/startup-act/backend/app/reviews/` and
`/Users/user/Workspace/startup-act/backend/app/analytics/`. Shared integration extends
collection quality/privacy, study validation/erasure, privacy access exports, main
router registration, Alembic metadata and readiness. Existing uncommitted P01–P07
and frontend changes were preserved; no commit or push was made.

Additive migrations: `007_collection → 008_reviews → 009_analytics`, one head.
P08 tables: `review_cases`, `quality_flags`, `review_assignments`, `review_decisions`,
`appeals`, `financial_retention_policies`, `reward_records`, `payout_records`,
`ledger_accounts`, `ledger_transactions`, `ledger_entries`. P09 tables:
`analysis_snapshots`, `snapshot_sources`, `reports`, `report_versions`, `exports`,
`report_shares`. Existing applied migrations 001–007 were not rewritten.

API contracts and operational boundaries:
`/Users/user/Workspace/startup-act/docs/backend/P08_P09_API.md`.

### Validation evidence

- Baseline before P08/P09: **336 passed**, zero skipped.
- Focused initial review suite: **61 passed**; initial analytics suite: **38 passed**.
- Full review found and corrected a missing ORM partial-index declaration, a detached
  test-fixture identifier, duplicate no-store headers, cross-snapshot differencing
  access, and reverse-journal/payment-state consistency. Actual HTTP acceptance
  flows and direct SQL negative checks were added rather than relying only on services.
- Last intermediate full run: **452 passed, one failure** (duplicate no-store header
  assertion), **94% coverage**. After the header fix, the focused analytics/API suite
  passed **30 tests**.
- **Final full guarded regression: 453 passed, zero skipped, 94% statement coverage,
  69.30 seconds.** Evidence:
  `/Users/user/Workspace/startup-act/.tools/p08-p09-verified.log`.
- Ruff lint/format checks passed for 93 Python files; compilation, `pip check`,
  migration downgrade/upgrade and ORM/schema drift tests passed. Four existing
  service definitions remain; no new dependencies or containers were introduced.
- Backed up the local application database to the private ignored directory
  `/Users/user/Workspace/startup-act/.tools/p08-p09-backup/` before explicitly applying
  008/009. `pg_restore --list` validated archive structure, not a full restore drill.
  Application database is at `009_analytics`; `alembic check` reports no new operations.
- Live direct backend and frontend-container proxy readiness return
  `{"status":"ready"}`. Host `127.0.0.1:8080` also returns readiness; `localhost`
  resolves to another local app in this environment, so use the explicit IPv4 address.
  Direct unauthenticated review access returns 401; an unknown share returns 404.
  All four Elseview containers are healthy.

### Explicit limits

- Development implementation, not a public-production release or legal/accounting
  compliance certification. Payment records do not transfer money or implement escrow.
- Only TND integer millimes, one full settlement at a time and exact full reversals;
  partial settlement and automatic credits-to-cash conversion are rejected/absent.
- Exactly two independent reviews, one fresh adjudication for disagreement and one
  fresh appeal review after rejection. No hidden cross-client reputation score.
- Financial retention duration is explicitly configured and reviewed by an operator;
  it is not a legally prescribed default. Evidence must be non-sensitive reconciliation
  text; automatic PII detection and external payment-evidence validation are not claimed.
- Snapshot population is nonwithdrawn/nonerased sessions at capture, maximum 1,000;
  this is not an all-time participant count. Pending exclusions remain frozen. Source
  unit is session; uniqueness across different studies is not claimed.
- Conservative suppression is not differential privacy, and previously downloaded
  exports cannot be recalled. The server checks current source authority on each access.
- JSON and CSV exports only. No XLSX/PDF dependencies, new report frontend, browser
  Arabic-layout verification, AI calls or paid-provider use were added. Unicode is
  covered by backend serialization/CSV tests, not visual browser certification.

The P01–P07 sections below are historical checkpoints; their deferred P08/P09
statements describe the implementation at those earlier checkpoints.

## P06 and P07 — Development implementation, September 23, 2026

### Delivered scope

- Purpose-separated public panel opt-in/profile editing, version/digest-bound consent,
  expiring server-assessed basic language qualifications, aggregate eligibility,
  mapped private-contact import preview, duplicate policy, source/consent provenance,
  workspace-keyed email lookups, suppression and verified invitation identity binding.
- Immutable launch recruitment settings and candidate snapshots, server-only screener
  evaluation, hashed expiring invitation capabilities, launch-wide capacity/budget
  checks and stable overlapping quota-cell reservation locks.
- Real nonmember participant sessions pinned to published study/consent versions,
  private capabilities, safe next-block projection, logical answer pointers and
  append-only typed revisions, optimistic conflicts and replay receipts.
- Server-selected branching with downstream invalidation, immutable assignments,
  event batch dedupe/order/provenance, one-shot exposure attempts and scoped stimuli.
- Atomic final answer snapshot/reservation consumption/internal quality job enqueue;
  deterministic quality evidence remains pending human review, never a payout decision.
- Participant access/withdrawal/erasure integration and dependent cleanup when an
  owner erases studies. Privacy/job authority is rechecked at worker completion.

### Schema and files

Additive chain: `005_study_guards → 006_recruiting → 007_collection`, one Alembic
head. Existing P04/P05 files and other uncommitted user work were preserved. No
commit, push or deployment was created.

P06 models: `participant_profiles`, `panel_consents`, `qualifications`,
`private_contacts`, `private_contact_consents`, `recruitment_configs`, `candidates`,
`invitations`, `quota_cells`, `reservations`, `reservation_cells`, `screener_results`;
existing `launches` gains a composite tenant identity constraint. P07 models:
`collection_sessions`, `collection_answers`, `answer_revisions`, `response_events`,
`interaction_attempts`. The logical answer/revision split prevents counting autosave
revisions as additional participants. Assignments and final membership are session JSON.

Implementation lives under `/Users/user/Workspace/startup-act/backend/app/recruiting/`
and `/Users/user/Workspace/startup-act/backend/app/collection/`, with explicit router,
Alembic, privacy, studies and embedded-job integration. API usage and retry contracts:
`/Users/user/Workspace/startup-act/docs/backend/P06_P07_API.md`.

### Executed evidence

- Baseline: **278 passed**, zero skipped, guarded dedicated PostgreSQL test database.
- Integrated regression before final review hardening: **324 passed**, zero skipped,
  **94% statement coverage**, 48.18 seconds. Log:
  `/Users/user/Workspace/startup-act/.tools/p06-p07-full.log`.
- This includes recruitment capacity/budget/overlapping-cell races, expiry versus
  reservation consumption, duplicate submission concurrency, real nonmember HTTP
  collection, branch edits, typed/Unicode rejection, stable preference order,
  exposure/assets, event rollback, privacy and migration round-trip/metadata checks.
- Final review fixed session-withdrawal scope, persisted choice randomization,
  source-owner/account authority, public server-selected recruitment and database
  finality/cross-session reference guards. Added two-study withdrawal isolation,
  fenced quality-job completion/cancellation and direct SQL negative regressions.
- **Final guarded regression: 336 passed, zero skipped, 94% statement coverage,
  55.19 seconds.** Log:
  `/Users/user/Workspace/startup-act/.tools/p06-p07-final.log`.
- Ruff lint and formatting passed across 75 Python files; compilation and
  `pip check` passed. One Alembic head; guarded downgrade/upgrade and metadata
  drift checks passed.
- Backed up the local development application database before applying migrations
  to `007_collection`; archive structure validated with `pg_restore --list` (not
  a full restore drill). Backup is private/ignored under
  `/Users/user/Workspace/startup-act/.tools/p06-p07-backup/`.
- Application database `alembic check` reports no new upgrade operations. Live
  frontend-proxied readiness returned `{"status":"ready"}`, and `/api/v1/panel/consent`
  returned the expected document. All four existing containers are healthy.

### Explicit development boundaries

- Real payments/reward obligations, reviewer decisions and appeals remain P08.
  Integer-millime values here are development budget commitments only.
- Private import retains HMAC lookup values, not recoverable email addresses;
  invitations are delivered manually. Automated mail campaigns are not implemented.
- Verified accounts and invitations are mandatory. No anonymous/open-link flow or
  cookie-based claim of unique people is enabled.
- Basic synthetic language assessments are not professional skill certification.
- No new participant frontend is provided. Browser attention, cross-browser timing,
  and production usability are not certified by backend tests. Exposure bytes cannot
  be made impossible for an authorized participant to retain. Reused exposure stimuli
  are concealed outside their timed attempt even when another block references them.
- Global panel withdrawal and client-scoped withdrawal remain separate purposes.
  No public deployment, paid provider call or financial transfer occurred.

The P04/P05 section below is historical phase evidence; its statements that P06/P07
were not yet implemented describe that earlier checkpoint.

## P04 and P05 — Implemented in development mode, September 23, 2026

### Scope and change reference

Local, uncommitted P04/P05 implementation on the existing `main` workspace. Existing user edits were preserved; no commit, branch, push or deployment was created. The inspected repository has an initial commit, unlike the historical P01 environment description below.

- P04: immutable localized consent/policy documents, exact digest-bound receipts, optional AI/recording decisions, private streaming upload intents, quarantine/format/checksum validation, scoped downloads/member links, quotas, immediate withdrawal restrictions, privacy epochs, access requests and retryable embedded erasure.
- P05: study ownership and role-bounded grants; strict typed block configuration/private rules; optimistic draft editing; cloning/new drafts; validation; immutable canonical publication; launch-ready/pause/close/archive lifecycle; seven core method value/event/reducer contracts and real React preview renderers.
- Exact study consent binds a published version and the document actually selected for that locale. A receipt for one study version does not silently authorize another. Human-only study policy denies the AI capability; no cloud adapter is enabled.
- Preview capabilities bind an authenticated session, actor, workspace, study/version/revision, locale and privacy epoch. Source access and grants are checked again on every preview request. Preview answers are transient validation inputs, never persisted participant records or report evidence.
- Methods enabled: single choice, multiple choice, rating, text, preference, five-second exposure and owned-image/authorized-external-link prototype tasks. All later methods remain unavailable for publication.

### Migrations, files and model coverage

Applied chain: `001_foundation → 002_identity → 003_jobs → 004_privacy → 005_studies → 005_study_guards`. There is one Alembic head. `005_study_guards` is a second, additive P05 revision: it protects document deletion and validated media dimensions without rewriting existing rows.

P04 tables: `consent_documents`, `consent_receipts`, `retention_policies`, `privacy_requests`, `privacy_restrictions`, `assets`, `upload_intents`, `asset_links`. P05 tables: `studies`, `study_versions`, `study_grants`, `launches`. Block/options/branch data remain typed version JSON, not duplicate SQL tables. Real FKs enforce applicable workspace relationships; JSON references are validated in services before publication/use.

Implementation is in `backend/app/common/privacy*.py`, `backend/app/common/private_storage.py`, `backend/app/studies/`, the existing embedded runner and three frozen migration files. `frontend/StudyPreview.jsx` and `frontend/preview.css` provide the test-only renderers; the default page remains a diagnostic, not an editor/dashboard. Executable fixtures and tests are in `backend/tests/test_privacy_assets.py`, `test_phase_contracts.py`, `test_studies.py`, `test_study_consent.py`, `test_privacy_guards.py`, `research_support.py` and `study_fixtures.py`.

### Executed evidence

- Baseline before edits: **176 passed, zero skipped, 95% statement coverage**.
- Final guarded PostgreSQL/Valkey regression: **278 passed, zero skipped, 94% total statement coverage**, 22.08 seconds in the Linux ARM64 development backend. The larger codebase changes the coverage denominator; this is not a claim of increased percentage coverage.
- Real independent transaction races: draft revision conflict, duplicate publication, storage reservation quota, repeated withdrawal, plus the existing identity/job/idempotency races.
- Failure/security tests: path traversal and symlink escapes, malformed/oversized/partial files, checksum mismatch, disk failure, abandoned uploads, cancellation cleanup, cross-tenant links/downloads/grants, role downgrade during upload, optional AI refusal, study-version consent mismatch, revoked source/preview access, erasure failure/retry, immutable records and publication.
- Migration upgrade/downgrade/re-upgrade checks run only on `elseview_test`, including the 003→004→head path. Final application `alembic check` reports no pending model/schema operations; `pip check` reports no broken requirements.
- Ruff lint and format checks passed; the actual updated frontend production bundle built successfully (16 modules). Blueprint validation passed for eight documents and nine JSON examples.
- Live browser/proxy smoke: synthetic registration, private-spool email verification, login, workspace, localized consent, retention policy, actual canvas-generated PNG upload/quarantine/completion, builder edit, publication and preview. The French eight-block sequence completed through actual React controls, including all seven methods. Loaded image dimensions were 640×300. Timed exposure hid the image before starting and after the five-second window and removed the repeat-start control. Arabic content rendered with RTL layout; the inspected narrow viewport had no horizontal overflow.
- Application data was backed up privately before migration. Before/after whole-row hashes and counts matched exactly across all **11 pre-existing application tables**; **12 new tables** were added. Subsequent browser smoke intentionally created separate synthetic rows. Backup and local outputs are ignored under `.tools/p04-p05-backup/` and `.tools/p04-p05-tests.log`; they are not public artifacts.
- Exactly four service definitions remain. No additional worker, broker, local model, storage server, dependency or paid cloud call was introduced.

Commands actually used (from the workspace root):

```sh
scripts/dev exec -T -e TEST_ALLOW_RESET=elseview_test backend python -m app.test_runner -q --cov=app --cov-report=term-missing
scripts/dev exec -T backend python -m ruff check app tests migrations
scripts/dev exec -T backend python -m ruff format --check app tests migrations
scripts/dev exec -T backend python -m alembic upgrade head
scripts/dev exec -T backend python -m alembic check
scripts/dev exec -T backend python -m pip check
scripts/dev up -d --no-deps --build frontend
scripts/dev exec -T frontend npm run build
scripts/dev config --services
scripts/dev ps
python3 scripts/validate_blueprint.py
git diff --check
```

During iteration, tests caught incorrect test expectations for Origin/domain error codes and a disposable test database holding an earlier draft of the new 005 migration. Expectations were corrected and the new migration's downgrade made compatible with that earlier draft; the complete guarded suite was rerun successfully. No failed/skipped case is included in the final passing count.

### Explicit boundaries and remaining gates

- Scope is development P04/P05, not production readiness, global account erasure or completed P17 privacy compliance. Erasure is workspace-scoped; identity/membership, immutable organization policies, redacted audit and minimal tombstones remain. Later producers must implement deletion/invalidation, financial retention and backup-restore restrictions.
- Public-panel profiles and private contacts do not exist yet. Their consent subjects remain distinct P06 models; there is no implicit identity/contact merge. Real participant capabilities, stored sessions/assignments/autosave and event adjudication remain P06/P07.
- Retention checks deny expired assets immediately, while physical retention cleanup is an explicit bounded operator sweep. There is no claim of an autonomous full retention scheduler. File support is deliberately bounded PNG/UTF-8 CSV/text/PCM WAV, not antivirus scanning, general document processing or transcription; limits and exact API workflow are in `README.md`.
- The preview is not a full researcher dashboard. Its shell is English with authored French/Arabic content. Browser checks are local Chromium smoke checks, not a full cross-browser, screen-reader, accessibility-certification, timing-accuracy or device-performance audit. External prototype outcomes are self-reported.
- No recruitment, real collection, payments, analytics/report product, live LLM, external connector, legal approval or public release is claimed. Production email/credentials/TLS, privacy/legal review and broader reliability remain separate gates.

Historical P01–P03 evidence below is retained unchanged and does not describe the current feature ceiling.

## P02 and P03 — Implemented in development mode, September 23, 2026

### Scope delivered

- P02: registration, verification/resend, Argon2 password hashing, JWT claim validation, rotating hashed refresh tokens, CSRF/origin controls, logout/session revocation, one-use recovery and generic account responses.
- Workspaces: create/list/read, active membership checks, owner/admin controls, invitations/acceptance, last-owner locking and redacted audit events. Study-specific grants correctly remain deferred until studies exist in P05.
- P03: PostgreSQL durable jobs/attempts, immutable command deduplication, FIFO due claiming with `SKIP LOCKED`, lease fencing/renewal, cancellation, bounded retries, uncertain unsafe outcomes and supervised lifespan runner.
- Cache: tenant/version-scoped aggregate helpers, atomic HMAC-keyed rate counters and fail-closed security rate limiting; no broker dependency.
- Generic idempotency: transaction-owned callback, hashed key/request, replay receipt, conflicting/expired-key rejection and real concurrent-transaction tests.
- Development mail spool, not external SMTP. Only registered `system.check` job is enabled; research/cloud/payment job handlers remain future phases.

### Executed evidence

- Full guarded PostgreSQL/Valkey regression run: **176 passed, zero skipped; 95% total coverage**.
- Auth router, dependencies, schemas and model modules: 100% measured statement coverage; auth service 95%; job runner 96%; idempotency 98%. Coverage is not proof of every possible case.
- Real transaction races: two-owner removal, simultaneous refresh/reset use, job claims, duplicate job keys and idempotency callback effects.
- Schema upgrade/downgrade/re-upgrade tests; application migration now **003_jobs**. `alembic check` reports no pending schema differences; `pip check` reports no broken requirements.
- Live HTTP smoke: registration, private-spool verification, login, `/me`, workspace creation and duplicate-safe job submission through the frontend proxy.
- Restarted cache and backend with pending work: the persisted job completed as succeeded with exactly one attempt. No extra worker service was created.
- Application `p01_demo` row preserved. A pre-migration application dump is retained privately under `/Users/user/Workspace/startup-act/.tools/p02-backup/`.
- Ruff and formatting checks passed. Tests make no cloud LLM calls; no external provider charges occurred.

### Files and model inventory

- `/Users/user/Workspace/startup-act/backend/app/auth/`: models, schemas, security, service, dependencies, router and private development delivery.
- `/Users/user/Workspace/startup-act/backend/app/jobs/`: models, service, router and embedded runner.
- `/Users/user/Workspace/startup-act/backend/app/common/`: domain errors, cache/rate limiter and idempotency.
- Frozen migrations `002_identity.py` and `003_jobs.py`; expanded fixtures and six new auth/job/cache test modules.
- Identity tables: users, refresh_tokens, one_time_tokens, workspaces, memberships, workspace_invites, audit_events. Job tables: jobs, job_attempts, idempotency_records. No premature study-grants FK or research schema.

### Explicit limits

This completes the defined development P02/P03 scope, not production readiness. Email is a private local spool; research authorization awaits studies/panels; actual external-call reconciliation is tested using controlled handlers, not a paid provider. The React page remains a status page, not an auth dashboard. DB operators can alter audit records; production role separation and hardened retention remain later gates. No fully implemented payments or response collection is claimed by the synthetic job tests.

Historical P01 and brand-cutover results below remain unchanged as historical evidence.

## Elseview brand cutover — September 23, 2026

- Applied the name and exact tagline to all product/planning Markdown files, React heading and browser metadata, FastAPI metadata, package identities and the backend logger.
- Renamed the Compose project to `elseview`; four active containers now use that prefix. Active PostgreSQL/private-file volumes use `elseview_*` names.
- Copied volumes only after stopping the original services, preserving original volumes as rollback copies. Renamed databases in the copied volume to `elseview_app` and `elseview_test`; updated bootstrap SQL, test guards, DSNs and instructions consistently.
- Compared application metadata rows, including creation timestamps, before/after cutover: exact match. No application schema change was needed; migration remains `001_foundation`.
- Post-cutover full test run: **96 passed, zero skipped; 90% coverage**. Added branding and Compose naming assertions. Frontend production bundle built; live frontend title/tagline and proxied readiness checked.
- Internal service names, health response contracts, application roles, fixture identifiers and workspace directory remain stable. No new containers, features or cloud calls were introduced.

Original P01 validation below is historical evidence; the 96-test cutover result above is the newer result.

## P01 — Development foundation

**Implemented and validated September 23, 2026.** No git commit reference exists: this workspace is not a Git repository. This section records the historical P01 scope; see the P02/P03 update above for current status.

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
