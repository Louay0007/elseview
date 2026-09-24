# Elseview — Research feature contracts

**Brand:** Elseview — See what you’re missing.

Detailed optional feature contracts retained from the broader design. The four-container architecture in `/Users/user/Workspace/startup-act/BACKEND_BLUEPRINT.md` takes precedence. These are planned features, not a requirement to implement every endpoint or table at launch. Background work runs inside the backend; AI calls the configured cloud provider.

## 1. Private files

Uploads use generated private storage keys, bounded size, verified media type and quarantine before processing. Published stimuli are immutable. Every download checks workspace/session/share permission; a checksum is not authorization. Recordings need separate consent. Browser cross-origin restrictions mean a prototype link alone does not provide internal click tracking.

## 2. Permissions

Roles are owner/admin, researcher, assigned reviewer and viewer; participant access is separate. Explicit study grants control raw-data visibility, publication, AI dispatch and export. Never permit another workspace's IDs to bypass object checks. Reviewers cannot assess their own participation. API credentials and cloud keys never enter client payloads.

## 3. Compensation and usage

Software credits, customer invoices and participant rewards are distinct. Use integer monetary units, currency, unique event keys and append-only corrections. Real compensated studies need a reward record and manual payout reconciliation before launch. Automated AI flags cannot deny compensation. Transfers, escrow and tax reporting are not performed by the backend merely because it stores a payment record.

## 4. Quality review

Versioned rules flag duplicate submissions, implausible timing, attention checks and off-topic text. Distinguish a network retry from dishonest participation. Record reviewer reasons, evidence and appeal outcomes. No model-produced confidence score is accepted as proof of fraud.

## 5. Reports

Freeze source/version/consent snapshots. Compute counts in SQL/Python, show numerator/denominator/missing values and describe panel sampling limits. AI writes drafts linked to verified source quotes. Approval creates a report revision. Revocation invalidates derived copies and shares. Spreadsheet exports escape formula-like values; private recordings and raw identities require separate permission.

## 6. API families

Use /api/v1 and schema-validated JSON. All work is inside the same backend container.

| Family | Planned operations | Rule |
|---|---|---|
| Auth | Register, login, refresh, logout, recovery | Hashed secrets, rate limits and revoked-session checks |
| Workspaces | Membership and study grants | No broad default raw-data visibility |
| Studies | Draft, versions, blocks, preview, publish, pause, close | Published definitions immutable |
| Recruitment | Invitation, screener, reservation | Atomic capacity and compensation commitment |
| Collection | Resume, answer revision, events, submit, withdraw | Session-bound token, safe block projection, idempotency |
| Reviews | Flags, assignment, decisions, appeals | Human evidence and conflict checks |
| Storage | Upload intent, content, complete, authorized download | Quarantine and retention |
| Analysis | Snapshot, metrics, comparisons | Reproducible source population |
| AI | Estimate, run, status, cancel, review | Cloud cost reservation and provider/consent policy |
| Reports | Draft, approve, export, share, revoke | Source permissions and export scope |
| Jobs | Status and controlled retry | PostgreSQL leases and persisted results |
| Privacy | Consent, access, withdrawal, deletion | Propagate to permitted derivatives |
| Billing | Usage, rewards, manual payment records | No automatic financial transfer |

This catalogue describes features rather than a requirement to implement all routes immediately. The detailed normalized dictionary is a later reference; the lightweight main blueprint defines launch scope.

## 7. Feature coverage and acceptance

The detailed method registry is `/Users/user/Workspace/startup-act/docs/backend/RESEARCH_METHODS.md`. The table below traces every requested feature family to an implementation owner and testable outcome; a template reuses blocks instead of creating a parallel backend.

| Requested feature | Module/method | Acceptance evidence |
|---|---|---|
| Prototype and usability tasks | Studies/collection, `prototype_task` | Published owned task, safe asset, saved outcome with measurement provenance |
| Five-second impressions | Timed exposure + follow-up | Frontend visibility timing, hidden asset after exposure, timing anomaly flag |
| Preference comparison | Variant block, experiment assignment | Stable randomized order, tie handling, denominator shown |
| First-click and heatmap data | Geometry-aware block/events | Normalized coordinates tied to immutable image dimensions |
| Surveys and branching | Typed questions + safe graph | All allowed paths validated; hidden/rejected question answers cannot be forged |
| Card sorting | Card/group response | Each required card appears once; open/closed modes checked |
| Tree testing | Tree/path response | Valid path, target outcome and backtracking count |
| Interviews | Scheduling + assets | Conflict-free booking, consent, attendance, approved recording access |
| Diary studies | Occurrences + entries | Time-zone-safe due windows, dedupe and missing-day reporting |
| Accessibility research | Task/issue template | Assistive-tech context and evidence; no unsupported certification |
| Content/language testing | Text comprehension template | Original dialect recorded and reviewed translations separated |
| Product concept and pricing tests | Survey/preference templates | Choice evidence distinct from real buying behavior |
| Onboarding, journey and forms | Ordered tasks/events | Step-specific attempts and missingness, no inflated full-journey claim |
| Competitor and feature prioritisation | Comparison/ranking/constant sum | Compatible tasks, valid ranking/totals and fair interpretation |
| Marketing ads, brand, landing/video pages | Exposure/survey/task templates | Recall/clarity results not claimed as measured conversion lift |
| Audience and market-entry analysis | Recruitment segments + snapshots | Disclosed panel coverage and suppressed tiny segments |
| Business offer, instructions and support | Survey/task templates | Policy-grounded questions and observed comprehension outcomes |
| AI customer chatbot tasks | Authorized sandbox scenarios | Versioned model/policy and reproducible failures; no unrestricted live transactions |
| AI safety, response quality and preference | Specialist rubric + blind comparison | Human adjudication, criteria version and uncertainty |
| Voice and translation evaluation | Assets/transcripts + language review | Consent, imported or explicitly approved cloud transcript metrics and dialect-specific findings |
| Dataset labelling | Annotation tasks/reviews | Label schema, agreement and provenance/rights |
| AI thematic summaries/clustering | AI jobs + source evidence | No invented citation; counts from validated respondent membership |
| AI sentiment, ad critique and Q&A | AI draft tools | Labeled tentative output; human interpretation, not emotion/sales oracle |
| AI reports and comparisons | Fixed metrics + approved evidence | Draft/approval/version separation and revocation |
| Panel targeting, screeners and private panels | Panel/recruitment | Opt-in boundaries and no cross-client private contact discovery |
| Quality controls and appeals | Quality module | Supported reasons and review; no automatic AI payout denial |
| Team roles, workspaces and API | Identity/workspaces/integrations | Deny-by-default object access tests including workers |
| Pricing, usage and compensation | Billing/rewards | Replay-safe balanced records; no automatic financial transfer claim |
| Exports/sharing/locales | Reports/storage/localization | Arabic-readable output, formula-safe spreadsheet and revocable shares |
| Privacy and self-hosting | Privacy/ops | Mock-provider/offline core tests, cloud outage handling, derivative purge and successful isolated restore |

## 8. Implemented targeting increment (partial C03)

`GET /api/v1/recruiting/targeting-vocabulary` provides version `1`, the 249 allowed ISO alpha-2 country IDs, city-ID syntax, experience categories/levels, matching semantics and the private-targeting consent body/digest. These are self-reported targeting attributes, not verified qualifications.

- `country_id`: optional uppercase ISO alpha-2 identifier.
- `city_id`: optional `geonames:<positive ID of 1–10 digits>`; requires a country. The country/city association is **not verified** and no geolocation is inferred.
- `experience`: optional `{version:"1", categories:{category:level}}`, with 1–10 categories. Categories are `software`, `design`, `research`, `business`, `education`, `healthcare`, `finance`, `manufacturing`, `retail`, `hospitality`; levels are `beginner`, `intermediate`, `advanced`.
- Missing/null attributes remain unknown. A filter excludes unknown values. Levels match exactly, not by greater-than proficiency; requested categories intersect.

Fetch `GET /api/v1/panel/consent?version=2` before a public profile PUT containing non-null targeting; send `document_version:"2"` and the presented digest. Version 1 remains the consent endpoint's default and its existing text/digest/replays remain compatible. Profile PUT is replacement, not patch. Profile responses retain `id`, `status`, `attributes` and add nullable `targeting_provenance` containing version, source, purpose, timestamp and consent metadata.

Workspace recruitment estimates, launch configuration/quotas and public recruitment filters accept the same attributes. Private CSV import mappings accept `country_id`, `city_id`, and `experience` (JSON cell). Non-null targeting additionally requires `targeting_consent` with version `1`, purpose `private_panel_targeting`, `confirmed:true`, the vocabulary's consent digest in `presented_digest`, and the referenced workspace document digest in `document_digest`. This is an operator assertion, not proof of a participant's consent: the workspace must obtain the approved purpose-specific consent. Import responses add `targeting_summary` with known/unknown counts per targeting field for accepted, nonduplicate rows.

Candidate snapshots remain frozen; private contacts are never merged across workspaces or with public profiles. A frozen public candidate containing targeting requires a current version-2 grant with the exact targeting-document digest: withdrawal followed by version-1 rejoining cannot reactivate its old targeting authorization. Legacy-only snapshots remain compatible with version 1. Existing privacy lifecycle rules still apply. Targeting PostgreSQL regressions have passed. Browser wiring, approved consent wording and qualifications/history acceptance remain; unit tests alone do not certify them.

## 9. Implemented AI-depth increment (partial C05)

`POST /api/v1/workspaces/{workspace_id}/ai/estimate` accepts `study_id`, optional `snapshot_id`, `operation`, optional `instruction` (at most 2,000 characters), `researcher_text_approved` (default false), and `depth` (default `standard`). It rejects `command_key`; run creation accepts the same fields plus that required idempotency key. Existing authorization, human-only, consent and researcher-text approval gates apply.

Revision `1` profiles are all bounded **single-call** executions. With the default 16,000-token context and 1,500 output-token configuration:

| Depth | Source-character ceiling, including overlap | Output-token ceiling | Output UTF-8 byte ceiling | Provider calls |
|---|---:|---:|---:|---:|
| quick | 2,666 | 750 | 50,000 | 1 |
| standard | 5,333 | 1,500 | 100,000 | 1 |
| deep | 8,000 | 1,500 | 100,000 | 1 |

Source spans use 2,400 characters with 200-character overlap. Standard coverage is one-third of configured context, quick is half standard, deep is half context (rounded down; minimum 500 source characters). Quick output is half the configured token ceiling (minimum 1); standard/deep preserve that ceiling. `max_chunks` is a conservative source-span bound equal to the character ceiling, **not the number of provider calls**. Full UTF-8/protocol accounting can still produce `AI_CONTEXT_LIMIT`; deep neither guarantees complete study coverage nor better findings.

The estimate returns `input_tokens_upper_bound`, `max_output_tokens`, `context_limit`, decimal-string `reserved_cost`/`other_charge_reserve`, `currency`, `depth_profile`, `coverage`, `source_chars_included_with_overlap`, and `chunks_included`. `reservation_created:false` and `budget_checked:false` are explicit: this is an estimate, not a reservation, price confirmation, budget-availability guarantee or provider call. Coverage reports text-answer revisions (not participants), included/total counts, a partial flag and `scope:"supplied_snapshot_text_only"`; estimates contain no source IDs/spans.

Run projections additionally expose `depth_profile`: name/revision, `execution:"single_call"`, `max_provider_calls:1`, effective source/span/output ceilings and limitations. Effective profiles persist with the run and participate in cache identity; old unprofiled runs synthesize a `legacy` revision from stored settings. Existing omitted-depth requests retain compatible standard behavior and existing billing selling units. Run coverage retains its source spans. Existing job/run states remain the progress mechanism: no new progress percentage, cancellation route, confirmation token or resumable multi-call execution is claimed. Focused AI PostgreSQL regressions have passed. Human review, multichunk synthesis, comparison/subgroup completion and live acceptance remain C05 work.

## 10. Report-file increment (partial C04)

Existing report export requests now accept `format: "json"|"csv"|"pdf"|"xlsx"` and optional `scope: "summary"|"raw"` (default `summary`). Raw scope requires its own existing raw authorization. Migration `023_report_formats` extends the persisted format constraint. Downloads remain private and stateless: current grants, source/consent restrictions and privacy state are checked, then bytes are regenerated without storing a durable report file. CSV/JSON behavior is preserved.

Rendering occurs outside both database transactions and workspace dispatch gates: a short capture transaction is committed first, then a separate final authorization transaction rechecks the captured source/permission bindings before bytes are released. Concurrent autosave/withdrawal tests use the runtime two-second SQL timeout; a withdrawal or changed binding suppresses download. PDF uses local Unicode fonts and Arabic shaping support; XLSX writes untrusted text as text rather than formulas. Renderers have bounded inputs and isolated execution, no remote assets, and no public file route. Docker installs its local font runtime. macOS and Linux resource-limit behavior differs; inspect production limits before rollout. Bilingual output exists, but native Arabic-reader sign-off remains outstanding. A downloaded external copy cannot be recalled by revoking its original share/export.

`GET /api/v1/workspaces/{workspace_id}/analytics/reports?limit=25&offset=0` exposes a bounded, authorized report index: `{items:[{id,revision,state}],has_more}`. Source/privacy filtering cannot expose raw report contents or truncate pagination at an empty filtered page. The authenticated `#/workspaces/{workspace_id}/reports` interface lists reports, reads immutable versions, requests approval and private JSON/CSV/PDF/XLSX downloads, distinguishes summary/raw permission failures and cleans object URLs. Ambiguous commands retain exact manual retries and account/workspace changes fence stale results. Report-index/export regression run:75 passed; browser fixtures:51 checks per desktop/mobile viewport. These are not human Arabic-reader or full production acceptance.

## 11. Five-second exposure increment (partial C06)

The V2 collection protocol adds `/attempts/{block_key}/prepare` and `/start`. Preparation sends `protocol_version:2`, the pinned `version_id` and a 43–128-character base64url `capability`; start additionally sends the returned `attempt_id`. The private asset request uses `X-Exposure-Token`. Preparation lasts 30 seconds; decoding occurs before start, and the durable start boundary permits only one attempt. Completion/interruption preserves timing provenance; invisible, late, lost-start or resumed unresolved attempts are not silently re-exposed. `visible_ms` can be unknown rather than fabricated.

Legacy V1 semantics remain available. Migration `024_exposure_preparation` can be downgraded for an empty or V1-only database, but refuses rollback if retained V2 attempts exist, avoiding reinterpretation of evidence. Browser timing remains observed browser timing, not proof of physical display exposure. Mocked desktop/mobile browser and real PostgreSQL regressions passed; an integrated real browser/API/database method journey remains required.

## 12. Account navigation increment (partial C10)

The default app has native account forms and server-authorized workspace/study/version navigation. Session credentials and one-time codes are never persisted to browser storage or resource links. Single-flight refresh uses the HttpOnly refresh cookie plus the in-memory CSRF value; business commands are never automatically replayed. A reload requires sign-in again. Login-session controls can revoke the current or another family. Workspace creation is not backend-idempotent, so an unconfirmed response locks repeat creation until the user reconciles the server list.

Reviewers navigate only their authorized assignment list; `has_more` reflects the selected page before revoked-source filtering, so an empty filtered page does not truncate traversal. Evaluation and participant schedule runners receive an authorized Response transport, not a visible bearer token. Published-version links do not grant participation; the participant endpoints still authorize every booking/diary operation. Authenticated assessments, own participation history and reporting/downloads are now integrated below. The full builder, participant inbox/profile, AI and commercial interfaces are not yet claimed complete.

## 13. Reviewed-language assessment backend (partial C03)

Migration `026_language_assessments` adds human-reviewed assessment evidence, separate consent, immutable approved versions/private material, bounded attempts, independent decisions/appeals, expiry and retention. Language identifiers remain distinct: `tunisianArabic`, `formalArabic`, `french`, `arabizi`. Synthetic or legacy development qualifications cannot satisfy the separate `reviewed_language` recruitment filter. Approval, adjudication and appeal authority are separated; qualification is not automatically awarded from an unreviewed score or a general account role.

`LANGUAGE_ASSESSMENT_AUTHORITY_WORKSPACE_ID` and `LANGUAGE_ASSESSMENT_REVIEWERS` configure the authority workspace and per-user allowed languages. Defaults disable this authority. Qualified humans must approve real content; enabling configuration alone does not prove linguistic competence, representative sampling or professional credentials.

Participant APIs under `/api/v1/panel` expose `/language-assessments`, `/language-assessment-consent`, `/language-assessment-consents`, `/language-assessment-attempts` (including own detail, submit and appeal), and `/language-qualifications`. The plural consent endpoint lists **all retained own grants**, including unused historical grants no longer represented in the active catalogue: `{items:[{id,document_version,created_at,withdrawn_at}],next_offset}` with offset pagination and limit 1–100. No private keys or assessment material are included. The participant account UI can recover this history after reload and withdraw the exact retained grant. Authorized operator APIs under `/api/v1/workspaces/{workspace_id}/language-assessments` manage version creation, private material, approval/retirement, review queue/decisions and retention sweep. Checked OpenAPI contains explicit request/success schemas and effective prefixed-route authentication.

Recruitment freezes qualification provenance and the exact consent grant. Withdrawal/rejoin cannot revive a withdrawn snapshot; expiry blocks new recruitment without retroactively cancelling earned participation. Account purge and scoped privacy hooks include assessment evidence. Restore requires a freshly exported **version-4 manifest** with identifier-only assessment revocations; replay validates scope and runs retention cleanup before readiness. Focused assessment/recruiting/privacy/config regressions: 258 passed; assessment/account/restore/config rerun on migration027: 102 passed. Counts overlap.

## 14. Authenticated diary recovery (partial C07)

`POST /api/v1/participant/longitudinal/diary-occurrences/{occurrence_id}/recover` requires bearer authentication and `{capability, expected_revision}`. The capability is a new 43–128-character base64url value retained only in client memory. The revision is the strict nonnegative `session_revision` returned by occurrence listing. Recovery is available only to the participant owning an existing active child, while the occurrence window, original submitted participation, current consent and candidate authority remain valid. It does not create another child, extend expiry, change the original locale/answers/assignments/event sequence, reserve another billable response or change reward obligations.

A different capability rotates atomically and increments the child session revision once. A request with the **current** capability replays the latest saved state without another rotation, even if its observed revision is old. Competing different-capability requests with the same revision cannot both succeed. After a conflict, the UI requires a successful schedule refresh before generating a new request; ambiguous delivery retains the exact original body. An obsolete token is rechecked after locks and cannot authorize answer, event, submit or withdrawal commands. This is not an indefinite historical-token registry: do not intentionally recycle old capabilities.

Migration `027_diary_recovery` permits capability changes only on otherwise-unchanged active diary rows with exactly one revision increment. Other session identity and submitted-evidence guards remain. Downgrade disables future rotations without restoring old credentials or rewriting existing evidence. Revision027 is required for recovery; deployment readiness always requires the full current application migration head. Recovery and ordinary collection start/resume share an explicit `SessionResponse`, including the server-pinned locale; the diary UI no longer asks users to guess it after reauthentication.

Evidence: 78 focused recovery/schema/migration/collection/longitudinal/reward tests passed; 36 projection/exposure regressions passed; desktop/mobile Chrome contracts cover start, page-remount recovery, lost acknowledgement, exact retry, conflict/failed refresh, Arabic direction, denial and late-response fencing. These runs overlap. Browser HTTP is synthetic, not a persisted browser/database journey. Diary v1 still repeats the entire initial survey; repeating prompt subsets and the remaining C07 automation are not implied.

## 15. Invitation and reminder delivery (partial C02/C07/C08)

Migration028 adds source-bound durable optional delivery without a fifth service. Recruitment invitation creation accepts optional `delivery:"manual"|"email"` (default manual). Email returns a null invitation token and queued delivery; an explicit invitation `/delivery` command permits the original still-authorized issuer to request a bounded resend. Public/user-linked eligible email can be resolved at dispatch; hashed-only private contact addresses cannot be recovered and remain manual-only. New invitation capabilities are purpose-separated and stable for an authorized resend; legacy random/manual invitations remain usable but cannot be reconstructed for mail.

Collaboration preferences add `email_reminders:false`. Both in-app reminders and explicit email-reminder opt-in are required. Disabling cancels pending work; re-enabling does not revive old work. Newly created/revised interview bookings schedule a reminder24h before start (or immediately when nearer), expiring at start. New diary schedules notify at opening and expire at due, not the grace deadline. Content includes no study title, meeting link, answer, capability or research-source identifier.

The worker resolves current recipient/source/consent/issuer/epoch authority before dispatch. Durable rows hold source references and state, never recipient addresses or raw capabilities in generic JSON. SMTP runs outside SQL transactions; committed dispatch is an irreversible boundary, unknown outcomes are quarantined rather than automatically resent, and restored unfinished optional mail is quarantined. Terminal metadata has bounded expiry+7day cleanup. Local private spool bounds and approved verified-TLS SMTP share auth delivery infrastructure. The supported topology remains one embedded backend-worker process. See [NOTIFICATION_DELIVERY.md](../../backend/NOTIFICATION_DELIVERY.md) for precise retry, lock, retention and operator contracts. Deliverability/provider activation and real-address consent must be approved separately.

## 16. Private participant participation history (partial C03/C10)

Authenticated own-subject endpoints under `/api/v1/participant/history` return a bounded page `{items,next_offset}` (offset0–100000; limit1–50, default25):

- Root: opaque workspace IDs evidenced by the caller's collection session, reward or booking, never researcher membership alone or private team names.
- `/{workspace_id}/responses`: own submitted session/version/occurrence/locale/timestamp, human review state and appeal state, never answers, assignments, quality evidence or staff identity.
- `/{workspace_id}/rewards`: own retained TND obligations, earned/paid state and timestamps, explicitly `manual_record_only:true`.
- `/{workspace_id}/rewards/{reward_id}/payments`: only that own reward's recorded/failed/reversed payment records and timestamps, never external references, payment evidence or recipient details; also explicitly manual records.
- `/{workspace_id}/attendance`: own authorized booking times/IANA timezone and attributed attendance; unknown is not inferred absent. Meeting links, actor IDs and staff notes are excluded.

These routes are rate-limited and no-store. Nonfinancial reads recheck active source, exact study consent, privacy and workspace authority under canonical locks. Financial reads intentionally preserve legally retained own obligations after research restriction. Revocation does not grant a new role, transfer money or expose a shared score. Stable pagination uses lookahead and never emits an unsupported continuation past the maximum offset. No new table or retention producer is introduced.

The authenticated history UI uses canonical review status/appeal endpoints, preserves original multilingual reasons and evidence, retains exact uncertain appeal requests and fences stale workspace/account responses. Any loaded-record denominator is local to the selected workspace/page set, not a complete-population or cross-client reputation measure. Evidence:12 fresh PostgreSQL tests,3 bounded-pagination unit tests,38 browser assertions per viewport plus native keyboard/AX/layout checks, and an independent review with no high-confidence findings. Real populated browser/API/database history acceptance remains open.

