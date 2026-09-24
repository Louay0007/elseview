# Elseview — Completion and release plan

**Date:** September 24, 2026  
**Status:** Implementation started at the user's request; partial development increments are recorded below. This plan does not authorize database resets, provider activation, production migrations or release.  
**Goal:** Complete the research-platform idea, including the backend, required product interfaces, full acceptance evidence and production gates—not just close the existing phase labels.

## 1. Scope, baseline and meaning of complete

Sources: [research-platform idea](RESEARCH_PLATFORM.md), the research-platform section of [startup ideas](STARTUP_IDEAS.md), [original P01–P19 plan](BACKEND_IMPLEMENTATION_PLAN.md), [architecture](BACKEND_BLUEPRINT.md), [feature contracts](docs/backend/FEATURE_CONTRACTS.md), [research methods](docs/backend/RESEARCH_METHODS.md), [implementation evidence](docs/backend/IMPLEMENTATION_STATUS.md), and [P19 story map](docs/backend/P19_ACCEPTANCE.md).

This is a forward completion backlog. It does not replace canonical answer, permission, money or privacy contracts, and it does not rewrite historical execution evidence. The six unrelated startup ideas are out of scope.

### Verified planning baseline

- Backend modules already implement identity, studies, recruitment, collection, reviews, analytics, AI, longitudinal studies, evaluation, templates, billing, collaboration and privacy. Extend these; do not rebuild them.
- Latest recorded schema head: `022_account_erasure`. New revisions must follow the actual head at implementation time; never rewrite applied migrations.
- Latest status document records 854 passing tests, zero skipped, one separately passing load test and 92% statement coverage. These are historical results, **not tests rerun for this plan**.
- P01–P18 have development evidence. P19 is not unconditional full-product acceptance. Existing browser fixtures mock HTTP; three integrated backend workflows do not prove all ten complete product stories.
- The README and older checkpoint paragraphs contain stale statements about phases and migration heads. Reconcile them against current code rather than treating every historical sentence as current scope.

### Three separate completion levels

1. **Feature-complete development:** all in-scope features have real implementations, safe failure paths and executable tests. External adapters may use mock transports, but manual substitutes do not count as completed automatic features.
2. **Accepted product:** real authenticated browser/API/database workflows pass, including Arabic/French, participant interactions and accessibility checks. Selected live adapters pass controlled synthetic-data validation.
3. **Production-ready:** operational restore/load evidence, approved providers, email deliverability, commercial/privacy review and an explicit release decision exist.

A disabled or unvalidated integration stays `blocked-external`, not `done`. If a feature is explicitly removed from release scope, record the decision and update the public promise; do not call the original full idea complete.

### Architecture and safety boundaries

- Retain exactly four services: frontend, backend, database and cache. One backend application process with embedded durable jobs; no Celery, extra worker, local LLM, media server or object-storage server.
- PostgreSQL remains authoritative. Valkey loss cannot erase submissions, budgets, payments or job outcomes.
- Keep public/private panels separate; retain explicit study grants and consent-purpose checks for all new data.
- Preserve canonical `/api/v1` answer revisions, idempotency and immutable published versions. New fields have compatible defaults; new method/schema versions cannot reinterpret existing answers.
- Participant payouts and customer payments remain **manual records and reconciliation**. Bank/card transfers, escrow, FX and partial settlement are not required by the canonical plan.
- Conference hosting, guaranteed prototype cross-origin instrumentation, clinical/legal certification, representative sampling guarantees and automated emotion/fraud judgments are not promised.
- No provider is selected by this plan. Verify current official APIs, permissions, retention and pricing before implementation/activation; secrets remain outside source control.

### Current implementation checkpoint — partial, not acceptance

| Package | Implemented in this checkpoint | Still required before package completion |
|---|---|---|
| C01 | Explicit auth, assessment, collection/history, report-index, notification preference and invitation success schemas; checked 202-path OpenAPI and effective authentication; matching client DTO subsets | Remaining success schemas/types, full traceability and artifact/job ownership contracts; reconcile final AI artifact/types after active work |
| C02 | Verified-TLS SMTP; durable auth/workspace/recruitment invitations and opt-in interview/diary reminders; stable resends, bounded retry, unknown-send quarantine, source/authority/privacy/restore gates and fair embedded execution | Provider/domain approval, real timing/privacy acceptance and live deliverability; hashed-only private contacts remain manual |
| C03 | Consented country/city/versioned experience targeting, private imports/frozen snapshots; reviewed assessment decisions/appeals/expiry and retained consent history; own response/review/appeal/reward/payment/attendance history | Genuine approved assessment content, profile UI (in progress), complete recruitment/participant journeys and human acceptance |
| C04 | Bounded private PDF/XLSX/CSV/JSON, raw/summary authorization and post-render recheck; privacy-safe report index; authenticated report versions/approval/download UI | Arabic-reader sign-off, populated real browser/API/database report journey and cross-platform resource/visual acceptance |
| C05 | Revision-1 quick/standard/deep **single-call** profiles, read-only estimates and pinned limits/cache identities | Revision-2 persisted multichunk/comparison orchestration is in progress; subgroup disclosure ledger, all-operation/UI coverage and human/live benchmarks remain |
| C06 | V2 prepare/asset/start/completed-or-interrupted five-second protocol, visibility handling, no replay on resume, legacy compatibility and PostgreSQL/browser regressions | Full real browser/API/database method journeys and remaining private media/accessibility evidence |
| C07 | Revision-fenced diary recovery preserving answers/locale/accounting; opt-in durable interview/diary email reminders | Repeating prompt subsets, expanded recordings, transcription/voice/sandbox automation and integrated acceptance |
| C08–C09 | Existing backend contracts retained; optional delivery source events now persist reminder work | Remaining real domain-event/vendor integrations and commercial contracts/acceptance listed below; no manual proxy counts as automation |
| C10 | Memory-only account/recovery/session flows, workspace/study/reviewer/schedule navigation, assessment/retained-consent UI, participant history and report versions/approval/downloads | Full researcher builder/AI/recruitment/billing and participant profile/invitation flows; full RTL/accessibility acceptance |
| C11–C12 | Fresh RAM-backed PostgreSQL and isolated authenticated nonpersistent Valkey; guarded migration/restore regressions; real built-frontend/account/API/database journeys at desktop/mobile | Expanded report/history real journey must rerun after029 readiness integration; ten full stories, final aggregate/load/physical-archive evidence remain |
| C13 | No external activation or release action | Operator-approved providers, qualified human reviewers, real pilot participants, commercial/privacy review and launch decision |

Current focused evidence includes **262 notification/auth/longitudinal/privacy regressions**, **14 delivery database/readiness/migration tests**, **51 assessment/retained-consent tests**, **75 report-index/export tests**, and **15 participant-history unit/database tests**. These overlapping runs are not a unique aggregate. The current200-path OpenAPI regeneration passed4 contract drift/security tests. Frontend **19 Node tests and production build passed**. Desktop/mobile account/report/history fixtures passed; reports have51 checks and history38 per viewport. Native Enter, AX-main, no-overflow,44px labeled targets and measured contrast were checked in their stated scopes; no human accessibility certification is implied.

A combined actual production-build account/API/PostgreSQL/Valkey/cache/harness/history run passed **36 tests**, including real desktop/mobile login, persistence/reload, assessments and session revocation. The later expanded report/history journey run passed41 backend tests but its two browser tests stopped at real readiness during active029 AI-head integration. That assertion remains enabled; the expanded navigation is not yet verified. The latest broad pre-notification/history run recorded **1,269 passed,1 deselected,2 CACHE_URL setup errors**; the isolated-cache harness correction subsequently passed13 cache and6 harness tests. A final aggregate run remains required.

`scripts/test_fresh.py` creates uniquely named RAM-backed PostgreSQL and optional authenticated nonpersistent Valkey containers from cached pinned images, verifies an empty dedicated database and cleans only its own resources. Default marker exclusions remain effective with explicit selectors; `--with-browser` also provisions cache. Migration/restore tests use separate child databases. Existing databases/volumes/cache are untouched. The last fully validated migration chain reaches028;029 revision-2 AI is in progress. No operator migration, live provider send/call, payment, deployment, commit or push occurred. None of C01–C13 is fully closed. Remaining internal work is a real backlog, **not merely external approval paperwork**.

## 2. Coverage and ownership map

`Cxx` work packages below supplement P01–P19. Owners identify responsibilities, not people already assigned.

| Idea or acceptance requirement | Current boundary | Completion owner |
|---|---|---|
| Auth, workspaces, invitations, recovery | Account UI and durable auth/recruitment/reminder SMTP implemented; approved live delivery remains | C01, C02, C10 |
| Study builder, branching, preview, versions | Backend present; product UI incomplete | C01, C06, C10 |
| Surveys, preference, first click, card/tree, ranking, usability | Existing methods need integrated product acceptance | C06, C10, C11 |
| Five-second research | V2 one-shot preparation/start/visibility/resume implemented; full real collection journey remains | C06, C11 |
| City, age, language, device, experience recruitment | Consented native country/city/experience attributes, filters, private imports and frozen targeting implemented | C03 |
| Public/private panels, screeners, quotas | Existing isolation and intersecting-cell rules retained; full recruitment product journey remains | C03, C11 |
| Qualified testers, quality scores/history, no-shows | Independent reviewed assessments and private scoped participation/attendance history implemented; approved content/profile/full acceptance remain | C03, C10 |
| Review, attention/duplicate flags, appeals, rewards | Human review/appeal and retained own financial history integrated; manual records remain distinct from transfers | C03, C09, C11 |
| Metrics, comparisons, charts, raw data and shares | Private four-format exports and authenticated report index/version/approval/download UI implemented; full visual/human acceptance remains | C04, C05, C10 |
| AI summaries, failures, translation, sentiment, clarity, Q&A | Nine revision-1 operations retained; all-operation revision-2 and live quality acceptance remain | C05, C11 |
| Comparison writing and subgroup insight finding | Bounded two-snapshot comparison is in progress; privacy-safe subgroup release history still required | C05 |
| Quick/standard/deep AI, costs, batching and cache | Versioned single-call depth/estimates implemented; persisted multichunk billing/retry work in progress | C05, C09 |
| Interviews, reminders, diary, transcripts/highlights | Opt-in email reminders and diary recovery implemented; prompt subsets/media/automation remain | C02, C07, C10 |
| Voice/accent and video-ad evaluation | Manual/import or storyboard proxies | C06, C07 |
| Chatbot, safety, preference, dialect and dataset evaluation | Human evaluation exists; external sandbox remains manual | C03, C07, C11 |
| Product, marketing, business and localization templates | 23 recipes exist; verify every idea use case, not just catalogue count | C06, C10, C11 |
| Design/project tools, calendars, webhooks and advanced API | Local ICS, test-event webhooks and partially typed API | C01, C08 |
| Plans, credits, AI add-ons, specialist fees and managed services | Manual billing present; validate product terms/workflows | C09, C10 |
| Consent, access, erasure, retention, provider deletion and backups | Existing privacy infrastructure; extend every new producer | All packages, C12 |
| Complete RTL/mobile/accessible product and ten end-to-end stories | Workbenches/contract fixtures are not final product acceptance | C10, C11 |
| Real local panel and operational service | Software cannot create representative participants or legal approvals | C13 |

## 3. Ordered work packages

Every package starts `pending`. A package closes only after its listed evidence exists. Each implementation change includes a narrow immediate test, then relevant integration/privacy/contract regression; run the complete guarded suite at a release checkpoint.

### C01 — Reconcile scope and finish shared contracts

**Owner:** backend + product + test. **Depends on:** none.

- [ ] Turn the coverage map into exact cases: implemented, partial, missing, externally blocked, or explicitly out of scope, with test identifiers and evidence dates.
- [ ] Reconcile README/current status/model inventory, including migrations 018–022 and current physical model names; keep historical test counts dated.
- [ ] Add explicit success-response schemas to affected APIs, then cover remaining public success projections. Preserve safe field sets and stable HTTP/error contracts.
- [ ] Update checked OpenAPI and frontend contracts together; specify pagination, status transitions, conflict/retry behavior and capability expiry.
- [ ] Define privacy ownership and durable job lifecycle for every planned artifact before adding its producer. Document dispatch/cancellation/unknown-external-outcome semantics.

**Paths:** `backend/app/*/{router,schemas}.py`, `backend/app/contracts.py`, `backend/contracts/openapi.json`, `frontend/contracts.d.ts`, `docs/backend/MODEL_TEST_MATRIX.md`.

**Exit evidence:** complete feature traceability, contract drift tests, response projection/role tests, additive-migration strategy and documented unresolved decisions. First cheap hypothesis check: compare the idea inventory with actual routes, request/response schemas and named tests; a phase label alone is not evidence.

### C02 — Production email and notification delivery

**Owner:** backend + operations. **Depends on:** C01.

- [ ] Keep private development mail capture and introduce an explicitly configured production SMTP or transactional-email adapter; no fifth service.
- [ ] Cover verification, password recovery, workspace invitations, recruitment invitations and opted-in reminders. Separate required transactional messages from optional notifications.
- [ ] Design a durable delivery record/job lifecycle that does not persist raw login/reset/invitation capabilities in generic JSON jobs or logs. Where delayed delivery needs recoverable content, use approved encrypted short-lived storage or a safely minted-at-dispatch design; keep verifier hashes and expiry/one-use rules.
- [ ] Prevent rollback/retry from invalidating already-sent links unexpectedly or duplicating business actions. Represent delivery failure/uncertainty, retry windows, suppression and cancellation honestly.
- [ ] Add authenticated provider callbacks only if supported/needed; verify signatures and dedupe. Configure sender-domain authentication and operator-visible delivery health.

**Paths:** `backend/app/auth/delivery.py`, auth/recruiting/longitudinal/collaboration services, `jobs/`, `config.py`.

**Exit evidence:** mock transport tests for success/rejection/timeout/replay, revoked/expired tokens, privacy and notification preferences; approved live synthetic verification/reset/recruitment/reminder flows and deliverability checks. Live sending requires separately approved account/domain and spending limits.

### C03 — Recruitment and credible participant qualifications

**Owner:** backend + research operations. **Depends on:** C01; delivery integration follows C02.

- [ ] Add optional country/city identifiers and bounded experience categories/levels with versioned vocabulary, provenance and purpose-specific consent. Existing missing values stay unknown, never inferred.
- [ ] Extend profile editing, private-contact import/preview, filters, estimates, screeners and intersecting quota cells. Freeze candidate attribute snapshots; do not merge matching contacts across workspaces.
- [ ] Replace development-only qualification claims with versioned researcher-reviewed language assessments, private answer keys, attempts/cooldowns, expiry/reassessment and human adjudication. Distinguish Tunisian Arabic, formal Arabic, French and Arabizi; do not infer professional credentials from language scores.
- [ ] Verify and complete participant-visible response/payment/attendance history and study- or workspace-scoped quality summaries. Expose evidence, denominators, recency and appeals; avoid an undisclosed cross-client reputation score or automatic rejection/payment denial.
- [ ] Audit attention, duplicate, rapid-response and copied-answer coverage across locales; retain human review for uncertain flags.

**Paths:** `backend/app/recruiting/`, `collection/quality.py`, `reviews/`, `longitudinal/`, related privacy producers.

**Exit evidence:** filter/import boundaries, unknown attributes, two-workspace isolation, language assessment integrity, attempt/expiry tests, last-slot/overlapping-quota races and explainable history. Qualified human reviewers must approve assessment content before real qualification claims.

### C04 — Private PDF/XLSX exports and complete report outputs

**Owner:** backend + frontend. **Depends on:** C01.

- [ ] Extend export formats without changing CSV/JSON behavior. Use versioned report/snapshot inputs and explicit summary/raw permissions; default shares remain redacted summaries.
- [ ] Select minimal maintained PDF/spreadsheet dependencies after official documentation and Arabic shaping/font/licensing verification. Pin dependencies only when implementing.
- [ ] Generate bounded artifacts using existing private storage and durable jobs where needed. Keep rendering/network fetch disabled; bound CPU, memory, rows and output size outside the API event loop.
- [ ] Protect spreadsheets from formula injection; render original Arabic/French/Arabizi, numeric denominators, provenance and approved AI labels correctly.
- [ ] Recheck source consent/grants at start, finalization and download. Add expiry, revocation, interrupted-job cleanup and erasure coverage.

**Paths:** `backend/app/analytics/`, `common/private_storage.py`, `jobs/`, reporting frontend.

**Exit evidence:** independently expected snapshot values in CSV/JSON/XLSX/PDF, real visual Arabic checks, no network asset fetch, role tests, large-output failure/retry, withdrawal during export and artifact purge. Already downloaded external copies cannot be recalled; document that boundary.

### C05 — Complete AI product contracts and depth controls

**Owner:** backend + research quality + frontend. **Depends on:** C01; C09 integration before paid activation.

- [ ] Define versioned quick/standard/deep profiles with explicit input coverage, chunk/output ceilings, cost estimate and limitations. Keep one configured model initially; depth is not an unbounded promise.
- [ ] Add estimate/confirm, run/status/progress, permitted cancellation and review flows. New request fields default compatibly for existing clients.
- [ ] Persist bounded chunk membership/progress and resumable finalization where deeper analysis needs multiple calls. Reserve total conservative cost before dispatch, reconcile per-attempt usage, preserve uncertain charges, and never assume provider exactly-once execution.
- [ ] Include depth/profile revision in cache identity alongside provider/model/config, snapshot, prompt/schema, consent and source versions. Reopening unchanged approved results must not trigger another charge.
- [ ] Verify all existing operations against their actual use cases; complete structured comparison reports and subgroup insight requests with code-computed statistics and disclosure suppression. Do not let the model invent counts, correlations, causality or coverage.
- [ ] Preserve exact source/quote validation, immutable originals, translation provenance, tentative sentiment/clarity/quality labels, human approval and human-only mode.
- [ ] Create a synthetic bilingual/dialect benchmark and predeclare reviewer rubrics, acceptance thresholds and regression checks before live evaluation. Human quality approval is separate from schema-valid output.

**Paths:** `backend/app/ai/`, `analytics/`, `billing/`, `jobs/`, AI/report frontend.

**Exit evidence:** known depth coverage/cost fixtures, cache/privacy invalidation, multi-chunk restart/dedupe, false citation rejection, partial-result labeling, provider error/unknown-charge reconciliation and responsive collection during analysis. Mock tests first; live compatibility/quality requires C13 provider approval.

### C06 — Close research-method and media gaps

**Owner:** backend + frontend + research quality. **Depends on:** C01; C04 for export acceptance.

- [ ] Finish real five-second participant collection: preload, server-bound attempt, hidden-tab interruption, no clean replay after reload, timing validity and honest unknown states. Match the published-method allowlist to actual collection renderers, not preview exports alone.
- [ ] Verify every existing advanced method through browser-to-database collection: geometry/letterboxing, first click, keyboard alternatives, card grouping, tree backtracking, ranking and constant-sum validation.
- [ ] Add bounded private audio/video stimulus support and actual media-review collection, with immutable duration/version, permitted playback/seek events, accessibility alternatives and replay policy. Keep storyboard templates distinct; do not relabel them as playback analytics.
- [ ] Complete consented accessibility-evidence uploads using private assets; do not require diagnosis or claim accessibility certification from participant feedback.
- [ ] Retest every template/use case against enabled methods, approved translations, correct denominators and representative reports. Preserve self-reported prototype outcomes unless an explicitly authorized instrumentation adapter is implemented.

**Paths:** `backend/app/studies/`, `collection/`, `analytics/metrics.py`, `common/` assets, `templates/`, frontend method renderers.

**Exit evidence:** registry contract tests plus real desktop/mobile keyboard/pointer/visibility tests, media parse/size bounds, safe authorized streaming/range behavior, replay/interruption/revocation cases and original method compatibility. No unbounded transcoding or extra media service; approval is needed for any external processing.

### C07 — Longitudinal, transcription, voice and sandbox automation

**Owner:** backend + frontend + provider operator. **Depends on:** C01, C05, C06; C02 for email reminders.

- [ ] Extend diary configuration with separate initial questionnaire and pinned repeating prompt subset, explicit schedule/timezone-rule provenance and safe resume after reauthentication. Preserve existing series, occurrences and earned reward semantics.
- [ ] Complete interview booking/rescheduling/attendance/reminder flows without implying hosted video calls. Support the idea's 30-minute interview example with explicit bounded recording duration/size and storage quotas; current ten-minute WAV limits cannot silently satisfy it.
- [ ] Introduce opt-in approved cloud transcription with separate capability, consent, pricing and durable work. Preserve manual transcript import. Store source/time spans, language, provider/version and machine-versus-human corrections.
- [ ] Produce source-linked interview highlights and follow-up drafts only from authorized transcripts; review before report inclusion.
- [ ] Add voice/accent evaluation with consented recordings, human reference transcripts and versioned normalization/metrics. Distinguish transcription error, infrastructure failure and subjective dialect judgments.
- [ ] Implement one operator-approved fictional-data chatbot sandbox connector with fixed destination/version/credential scope, turn/time/token caps, cancellation and immutable transcript provenance. No arbitrary participant URLs/tools or production side effects.
- [ ] Include all recordings, chunks, transcripts, provider references and outputs in erasure/holds/retention and late-result fencing.

**Paths:** `backend/app/longitudinal/`, `evaluation/`, `ai/`, `jobs/`, asset and privacy producers, participant/evaluation frontend.

**Exit evidence:** diary boundary/reload/missed-day/pay cases, real reschedule races, transcription fixture timing, voice ground truth, controlled provider failures, sandbox version/budget enforcement and withdrawal while remote work is pending. Live adapters require external approval; imported material alone is not automation evidence.

### C08 — Useful integrations and customer API

**Owner:** backend + frontend + integration operator. **Depends on:** C01, C02; relevant C04/C07 artifacts.

- [ ] Expand test-only webhooks to a documented minimal real event catalogue, such as approved-report availability and study lifecycle changes. Emit safe metadata transactionally with durable jobs, stable delivery IDs, signed timestamps and bounded retry.
- [ ] Let authorized customers inspect delivery status/replay safely. Recheck integration, issuer authority and current source permissions before dispatch; do not embed research answers or capabilities by default.
- [ ] Implement one approved design-tool connector, one calendar synchronization connector and one project-tool workflow. Choose vendors during scope approval; local ICS and public design links remain useful fallbacks, not proof of synchronization.
- [ ] Define OAuth/credential storage, refresh/revocation, least-privilege scope, permission changes, rate limits, reconciliation and remote deletion behavior. Handle callbacks/redirects without arbitrary destinations.
- [ ] Publish safe customer API documentation and examples from typed contracts, including scoped API keys, pagination, retries, limits and revocation.

**Paths:** `backend/app/collaboration/`, `jobs/`, `config.py`, `contracts.py`, integration settings frontend.

**Exit evidence:** real event payload tests, deduped redelivery, stale-grant suppression, vendor mock failure/recovery, calendar update/cancel reconciliation and controlled live smoke per selected connector. Ordinary test runs never contact vendors.

### C09 — Complete commercial behavior without payment automation

**Owner:** backend + product + financial operator. **Depends on:** C01; coordinate C03/C05 selling units.

- [ ] Validate every promised pricing mode: per study, per completed response, team allowances, specialist surcharge and depth-aware AI add-ons. Define response-count rounding, cancellation, partial AI coverage and unknown-provider-cost disclosure explicitly.
- [ ] Resolve non-expiring software credits as a product entitlement contract distinct from cash, finite operational quotas, subscription allowances and participant rewards. Do not claim existing quota grants are prepaid money; add durable purchase/redemption accounting only if needed by reviewed terms.
- [ ] Expose estimates, reservations, consumption, remaining allowance/credits, invoice status, manual payment evidence and full supported reversals. Preserve immutable historical prices and existing TND millime arithmetic.
- [ ] Specify managed-research service intake, authorized staff handoff and reviewed quote/invoice workflow using existing workspaces/roles rather than a second marketplace.
- [ ] Define financial retention/minimization after the reviewed interval, subject to holds/open obligations; do not delete immutable ledgers merely to claim erasure. Obtain operator/legal decisions for any archival or eventual purge mechanism.

**Paths:** `backend/app/billing/`, `reviews/`, publication/collection/AI hooks, commercial frontend.

**Exit evidence:** independent arithmetic fixtures, concurrent reservations/credit use, duplicate invoice/payment/reversal tests, cancellation and expiry behavior, clear visible usage, financial-preserving erasure and approved local invoice/retention terms. No money transfers are introduced.

### C10 — Complete the product interfaces, not only diagnostics

**Owner:** frontend + backend. **Depends on:** C01; deliver alongside C02–C09, not only afterward.

- [ ] Researcher: onboarding/workspaces, study builder/preview/version history, template catalogue, recruitment/quotas, review/adjudication, charts/comparisons, AI review, export/share, team/API/integrations, billing and privacy administration.
- [ ] Participant: account verification/recovery, consented profile/qualifications, invitations/screening/reservation, all enabled collection methods, safe resume/retry, interviews/diaries, history/rewards/appeals, notifications and account erasure.
- [ ] Replace manual token/session copy-paste with authorized navigation and recovery. Keep bearer/capability secrets out of URLs, logs and persistent browser storage; reissue only after server-side identity/ownership checks.
- [ ] Use the existing visual system and thin API client. Do not duplicate authorization, review, metric or money logic in React.
- [ ] For every workflow test loading, empty, validation, network failure, expired/revoked access, disabled, conflict and success states; protect unsaved work and confirm destructive actions.
- [ ] Verify Arabic/French RTL/LTR, mobile layouts, charts with readable tables/text alternatives, focus order, screen-reader announcements, keyboard-only operation and reduced motion.

**Paths:** `frontend/`, related API projections and contracts. Existing workbenches remain diagnostic fixtures, not the shipped dashboard.

**Exit evidence:** real authenticated vertical journeys for each user role; no feature requiring raw IDs/capabilities to be pasted into a workbench. Automated checks plus manual assistive-technology review; document exact accessibility scope rather than blanket certification.

### C11 — Finish P19 with reproducible end-to-end evidence

**Owner:** test + backend/frontend + research reviewer. **Depends on:** applicable C02–C10 slices; final sign-off after all.

- [ ] Create an isolated synthetic browser/API/PostgreSQL environment using the same four services, with explicit exclusive test-database approval. Extend existing browser tooling first; add a driver dependency only if justified.
- [ ] Run the ten original P19 stories as named coherent scenarios, not a claim inferred from unrelated test counts: bilingual recruit-to-report, tenant isolation, lost-network replay, last-slot race, diary/missingness/pay, design methods, AI false evidence/outage, withdrawal during work, distinct financial records, and isolated restore.
- [ ] Browser loss/reload tests must interrupt actual browser requests and recover persisted state; mock HTTP fixtures remain separate contract tests. Verify one logical submission/reward/charge where required.
- [ ] Add complete cases for C02–C09: email link round-trip, city/experience targeting, qualification expiry, Arabic PDF/XLSX, depth/cost confirmation, media/transcription/voice, sandbox connector and synchronized integration outcomes.
- [ ] Run mock and approved live-provider tiers separately. Require actual participant-source AI report approval for the relevant live story; researcher-only `study_helper` is not an equivalent substitute.
- [ ] Fill method M01–M08 and model D01–D10 evidence inventory with exact tests or justified not-applicable cases. Track contract/schema drift, dependencies, migrations and new privacy producers.

**Exit evidence:** all scoped stories pass, failures/skips and external blockers are explicit, and records include commit/change reference, environment, exact command, test totals, artifacts and reviewer decision. No screenshots/logs with credentials or real participant data.

### C12 — Production operations, privacy and reliability

**Owner:** operations + backend + privacy reviewer. **Depends on:** new producers and jobs from C02–C09; coordinate C11 restore tests.

- [ ] Validate four-service production configuration, TLS/proxy/cookies/origins, private storage, restricted database roles, dependency locks and explicit migrations. Keep one backend process until coordinated dispatch assumptions are deliberately redesigned and tested.
- [ ] Add actionable aggregate health/alerts for queue age/failure/uncertainty, provider costs, delivery failures, disk headroom, DB pool, erasure backlog and backup freshness without logging private payloads.
- [ ] Test prolonged AI/transcription/export work alongside autosave and notification delivery. Prevent one long handler from starving the single-flight queue with bounded resumable steps/fair scheduling inside the existing backend. Set measured targets before the run.
- [ ] Run representative proxy/network load and soak tests with production throttling; publish hardware, payloads, concurrency, duration, p50/p95, memory, queue delay and accepted-write durability. Do not extrapolate the earlier four-session benchmark into production capacity.
- [ ] Create encrypted, off-device matched database/private-file backups with approved key custody; conduct a real archive restore, not only a PostgreSQL TEMPLATE clone. Reconcile current tombstones/holds, verify private bytes and nonzero balanced journals, and deny access until replay is complete.
- [ ] Define and measure recovery point/time targets, failed-backup response, provider outage handling, release rollback and incident response. Reversible feature flags cannot retract sent mail or submitted provider requests.
- [ ] Perform the final permission/dependency/application security review and privacy review after implementation. Fix release-blocking findings; document actual provider retention/deletion and already-downloaded-copy limitations.

**Exit evidence:** approved real restore drill, sustained capacity envelope, monitored failure recovery, no unresolved release-blocking findings and runbooks executed by an operator. Destructive drills/deployments require separate explicit authorization.

### C13 — External validation and launch decision

**Owner:** product + research operations + provider/financial/privacy operators. **Depends on:** begin approvals early; final decision requires C01–C12.

- [ ] Supply privately managed provider accounts, exact models/capabilities, sender domain, chosen integration vendors, test accounts and bounded live-test budgets.
- [ ] Approve vendor data handling/retention/deletion, international-transfer requirements, participant consent materials, recording rights and local invoice/payment/financial-retention rules with qualified reviewers.
- [ ] Recruit an opt-in pilot panel with native-language reviewers and relevant specialists. Report real coverage/availability and recruitment cost; synthetic seed records do not establish a Tunisian/MENA panel or verified expertise.
- [ ] Run a controlled pilot with researchers and participants, support/appeal/managed-research procedures, manual payout reconciliation and human review of report usefulness.
- [ ] Record feature acceptance, operational readiness and external approvals separately. Launch only the explicitly approved scope; keep unapproved adapters disabled and unresolved full-idea features listed as blockers.

**Exit evidence:** dated release decision, approved scope/provider matrix, pilot outcomes and accountable operators. This plan cannot obtain legal/vendor certification or guarantee market demand.

## 4. Sequencing and practical delivery slices

| Milestone | Packages | Result |
|---|---|---|
| M0 — Truthful baseline | C01 | Accurate scope, contracts and acceptance inventory |
| M1 — Usable core research | C02, C03, core C06, corresponding C10 | Real account/recruitment/participant journey and research-method gaps closed |
| M2 — Complete reporting and commercial controls | C04, C05, C09, corresponding C10 | Exports, depth/cost UX, complete report and billing workflows |
| M3 — Media and connected workflows | media C06, C07, C08, remaining C10 | Actual video/voice/transcription/sandbox and selected vendor integrations |
| M4 — Accepted release candidate | C11 + C12 | Complete stories, privacy/restore and measured operational evidence |
| M5 — Approved launch | C13 | Live approvals, pilot evidence and explicit release decision |

Parallel work after C01: C02, C03, C04 and C05 can proceed on separate slices; C09 pricing contracts should be settled before depth UI is finalized. C10/C11 tests accompany each slice. C12 privacy work is part of every producer, not deferred cleanup. Start vendor/legal/domain approvals immediately so M3–M5 do not wait unnecessarily.

Do not promise calendar dates from phase counts. After C01, estimate each vertical slice from its migration/API/UI/test work and provider lead time; reassess after M1. Release blockers take priority over optional sophistication.

## 5. Validation and change discipline

### For every slice

1. Read the controlling implementation and nearest tests; state a falsifiable hypothesis and cheapest check.
2. Specify additive DTO/schema changes, roles, consent, error/retry and migration/backfill behavior before editing. Preserve unrelated work.
3. Implement one coherent vertical slice; immediately run its narrowest behavior check, then relevant database/contract/privacy tests.
4. Reuse current runner, dependency locks and browser tooling. No provider traffic or installations merely to write this plan.
5. Review final diff, regenerate affected contracts, update API documentation and record exact evidence in `IMPLEMENTATION_STATUS.md`.
6. After substantial changes, perform independent code review; resolve release-blocking findings before closing the slice.

### Current isolated validation commands

Run from the repository root with existing dependencies and cached pinned images. The isolated runner provisions and cleans only resources it creates. These command examples are not additional execution claims; exact results are recorded above.

```sh
backend/.venv/bin/python scripts/test_fresh.py -q tests/test_participant_history.py tests/test_participant_history_db.py
backend/.venv/bin/python scripts/test_fresh.py --with-browser -q tests/test_live_account_browser.py
# Broader ordinary/database/cache/local-browser checkpoint; live-provider/load stay excluded.
backend/.venv/bin/python scripts/test_fresh.py --with-browser -q
```

`--with-cache` enables isolated Valkey without browser tests. The real browser runner builds the shipped frontend and uses loopback HTTP, PostgreSQL and Valkey; default marker exclusions persist even when file selectors are supplied. Do not override them to enable live providers or operational load without approval.

### Existing configured-environment commands

The commands below require separately approved configured services. They are examples, not additional executed results.

```sh
# Non-destructive source/contract checks against the configured backend container.
scripts/dev exec -T backend python -m ruff check /app/backend
scripts/dev exec -T backend python -m ruff format --check /app/backend
scripts/dev exec -T backend python -m app.contracts --output /app/backend/contracts/openapi.json --check

# Existing frontend unit/build checks and mocked browser-contract fixtures.
(cd frontend && npm test && npm run build)
node scripts/browser_contracts.mjs /tests/renderers.html /tests/research.html /tests/longitudinal.html /tests/contracts.html
```

The following runner resets a dedicated test database. **Obtain explicit approval and exclusive ownership first; never run against the application database or another user's test database.** Substitute only an approved dedicated `_test` database guard matching the configured test URL. The example uses the repository's existing `elseview_test` convention.

```sh
# Narrow integrated acceptance; select the relevant existing/new file per slice.
scripts/dev exec -T -e TEST_ALLOW_RESET=elseview_test backend \
  python -m app.test_runner -q tests/test_product_acceptance.py

# Release checkpoint: ordinary regression excludes live-provider and load tiers.
scripts/dev exec -T -e TEST_ALLOW_RESET=elseview_test backend \
  python -m app.test_runner -q
```

Use separately approved guarded commands for load, live adapters, migration round-trips and physical restore. Final browser-to-database E2E commands will be documented when implemented; the existing fixture command does not satisfy that gate.

## 6. Final acceptance checklist

- [ ] Every research-platform idea feature maps to a real implementation and acceptance evidence; no manual proxy is mislabeled automation.
- [ ] All enabled methods have working participant collection and method-specific metrics, not just preview/schema support.
- [ ] All roles, private panels, scoped API credentials and source permissions remain isolated across API, jobs, reports and integrations.
- [ ] Arabic/French desktop/mobile and keyboard/screen-reader journeys pass their declared scope.
- [ ] Reports, exports, AI coverage/costs and financial records agree with independent fixtures and immutable source versions.
- [ ] Every new personal-data producer participates in consent, holds, retention, erasure and restore fencing.
- [ ] Ten P19 stories and new completion stories pass through real persistence; live and mock evidence are separated.
- [ ] Production email and selected live adapters are validated, approved and observable; no automatic activation on upgrade.
- [ ] Encrypted offsite archive restoration and representative sustained load pass predeclared operational targets.
- [ ] Commercial/privacy/provider approvals and real pilot evidence exist; unresolved requirements remain visible.
- [ ] Final documentation, model/test inventory and operational handoff are current; an explicit release decision is recorded.

**Next implementation action:** stabilize and verify revision-2 AI integration, finish profile/navigation acceptance, then continue the remaining internal C01/C03/C05–C12 work (including diary prompt subsets and complete product journeys). External provider/human/commercial approvals remain separate blocked gates. The implemented increments above do not constitute full-plan completion or release authorization.
