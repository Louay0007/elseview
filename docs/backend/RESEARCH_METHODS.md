# Elseview — Backend research-method specification

**Brand:** Elseview — See what you’re missing.

## 1. Status, sources and ownership

**Status: proposed design, not implemented or runtime-validated.** “Must” states a proposed contract; limits and milestone choices below are product decisions, not requirements imposed by the cited standards.
Product basis: [RESEARCH_PLATFORM.md](/Users/user/Workspace/startup-act/RESEARCH_PLATFORM.md), especially methods, languages, quality and post-collection AI; and [STARTUP_IDEAS.md, Section 1](/Users/user/Workspace/startup-act/STARTUP_IDEAS.md#1-tunisian-user-research-and-ai-testing-platform), including the four-method launch recommendation, diaries, accessibility and AI datasets.
This document owns method behavior only. The main architecture owns migrations, physical columns/indexes, authentication, panel recruitment, payments, storage providers, queues and deployment. No implementation scaffolding is specified here.

| Shared table name | Method-level responsibility; not a physical schema definition |
|---|---|
| `study_versions` | Immutable published study, language content, branching, consent and analysis-policy references. |
| `blocks` | Ordered typed configurations belonging to exactly one study version; private evaluation configuration stays server-side. |
| `sessions` | One participant attempt pinned to one version, with consent, language, eligibility and lifecycle context. |
| `answers` | Validated final response facts and provenance; revisions/adjudication must not silently replace originals. |
| `response_events` | Typed interaction/lifecycle observations, source attribution and server receipt time; not arbitrary analytics payloads. |
| `assets` | Private immutable stimulus/evidence objects with rights, checksums, dimensions or duration and retention policy. |
| `experiment_assignments` | Persisted presentation order/variant assignment, algorithm revision and analysis grouping. |
| `diary_occurrences` | Materialized participant-specific reporting windows, status and links to repeated prompt answers. |

## 2. Registry and shared contracts

Use a closed registry keyed by `(type, schema_version)`, with author-config schema, participant-safe projection, response schema, semantic validator, event allowlist, metric definitions and minimum milestone. Proposed schema dialect: JSON Schema Draft 2020-12 [S1]; mathematical and cross-record constraints also require semantic validation.
Reject unknown types, versions and object properties; never accept executable scripts, arbitrary HTML, SQL, remote schema references or unrestricted URLs inside a block. Do not silently coerce strings to numbers or migrate a live session to another schema.

| Block envelope field | Type and publication contract |
|---|---|
| `block_id`, `study_version_id` | Required opaque identifier strings, 1–64 ASCII letters/digits/underscores/hyphens; server verifies ownership, not just syntax. |
| `type`, `schema_version` | Required registry discriminator and positive integer; fixtures use schema version `1`. |
| `required` | Required boolean; controls ordinary skip, not the participant's right to withdraw or report inability. |
| `prompt` | Required map of approved language tags to nonempty plain text, maximum 4,000 Unicode code points per value. |
| `config` | Required type-specific object; all fields listed in a method row are required unless marked optional or conditional. |
| `evaluation` | Optional author-only object: success keys, AOIs, reference policies, gold labels and scoring rules. Never in participant payloads. |

Localized labels use the same language-map shape as `prompt`; choice/card/node/variant IDs are stable strings, never translated labels or array indexes. `asset_ref` means `{asset_id, asset_version}` with a positive integer version; the referenced asset is immutable and must belong to the workspace and be authorized for this study. Participant asset access must not disclose private asset metadata, source filenames or evaluation attachments.
Proposed launch limits: 100 blocks/study; 100 choices/cards/tree nodes per block; 10 preference variants; 50 AOIs with 3–100 vertices each; 10,000 code points per free-text answer; 64 KiB answer JSON; 100 events/batch. Higher limits require a new supported policy, not silent truncation.
Publish checks include unique IDs, resolvable assets, complete approved language coverage, supported client capability, consent requirements and reachable acyclic branching. Branch predicates may inspect earlier answers through allowlisted operators only; the server returns the next authorized block, not private qualification rules.
Publishing freezes configuration, assets, language revisions, task/model/dataset versions, assignment algorithm, rubric and metric-policy version. Editing any of these creates a new `study_versions` entry. Old sessions continue on their pinned version; aggregate comparisons explicitly name versions and do not assume equivalence. Withdrawn rights or consent revoke access even to pinned content: immutable history is not permission to keep serving it.

| Answer envelope field | Submission contract |
|---|---|
| `study_version_id`, `block_id`, `schema_version` | Required; must exactly match the session's currently authorized block and registry version. Session comes from the authenticated route. |
| `client_submission_id` | Required opaque ID for retry deduplication; not participant identity. |
| `status` | Required enum `responded`, `skipped`, `unable`; `skipped` requires `required=false`; inability remains visible, not fabricated success. |
| `response` | Required typed object for `responded`; JSON `null` for `skipped`/`unable`. Empty strings/arrays are not substitutes for missing answers. |
| `occurrence_id` | Optional except diary prompt answers, where it is required and must identify an authorized open occurrence. |
| `reason_code` | Required only for `unable`: `technical`, `accessibility`, `declined`, `other`; no medical explanation required. |

One final answer per `(session, block, occurrence-or-none)` is accepted. Draft edits remain distinguishable from final facts; no participant overwrite after finalization. Corrections require an audited revision workflow. Required unanswered blocks prevent normal completion, but never prevent withdrawal or an explicit incomplete closure. Any `unable` response is retained as a terminal incomplete outcome, not normal successful completion.
`accepted` means structurally and contextually valid ingestion, not “truthful,” “quality approved,” “paid,” or “correct.” Client time, success reports and events are observations; server-assigned source and review decisions preserve that distinction.

## 3. Survey configurations and responses

All six survey types share optional `randomize_options:boolean` (default false), except rating/text where it is forbidden. When enabled, the server persists option order in `experiment_assignments`. Every option is `{id,label}`; every free-text value is `{text,language}` with original text retained.

| Type / first milestone | Required `config` fields | `response` contract and validation |
|---|---|---|
| `survey.single` / M1 | `options: option[2..100]` | `{option_id}`; exactly one configured ID. “Other” is an explicit option followed by a separate text block. |
| `survey.multi` / M1 | `options`, `min_selected:int`, `max_selected:int` | `{option_ids:string[]}`; unique configured IDs; `1 <= min_selected <= max_selected <= option count`. Model “none” separately, not an empty answered array. |
| `survey.rating` / M1 | `min:int`, `max:int`, `step:int`, `endpoint_labels:{low:language-map,high:language-map}` | `{value:number}`; `min < max`, positive step, range divisible by step; value lies on the configured discrete scale. |
| `survey.text` / M1 | `min_length:int`, `max_length:int` | `{text,language}`; `1 <= min_length <= max_length <= 10000`; count code points, reject whitespace-only, retain submitted spelling/spacing. |
| `survey.ranking` / M2 | `options`, `rank_count:int` | `{ordered_option_ids:string[]}`; unique known IDs, length exactly `rank_count` within 1..option count; order is best to worst; no tied ranks in v1. |
| `survey.constant_sum` / M2 | `options`, `total_points:int` | `{allocations:[{option_id,points:int}]}`; each option exactly once, nonnegative points, integer total exactly `total_points` within 1..10000; never renormalize. |

## 4. Visual and navigation methods

| Type / milestone | Required `config` fields | `response` contract; additional checks |
|---|---|---|
| `prototype.task` / M1 | `target:{mode:"asset_flow",asset_refs:asset_ref[]}` or `{mode:"external_link",url:https-URL,authorization_ref:id}`; `success_mode:"self_report"`; `time_limit_ms:int` | `{outcome:"completed"\|"failed"\|"gave_up",elapsed_ms:int,notes?:{text,language},termination_reason?:"timeout"}`; timer 1..3,600,000 ms, observed elapsed nonnegative. Timeout requires failed/gave-up, never completed. |
| `five_second` / M1 | `asset_ref`, `exposure_ms:5000`, `interruption_policy:"invalidate"`, `recall_block_ids:string[1..10]` | `{attempt_id,visible_ms:int,interrupted:boolean}`; reference subsequent `survey.text` blocks; recall answers are separate answers, not duplicated here. Server records timing-valid/invalid/unknown. |
| `preference` / M1 | `variants:[{id,asset_ref,label}]`, `randomization:"uniform_permutation"`, `allow_tie:boolean`, `allow_none:boolean` | `{assignment_id,decision:"variant"\|"tie"\|"none",selected_variant_id:string\|null,reason:{text,language}}`; 2..10 variants; selected ID required only for `variant`, otherwise null; permitted tie/none only. Reason required and nonblank. |
| `first_click` / M2 | `asset_ref`, `coordinate_space:"normalized_asset"`, `input_modes:["pointer"]` or `["pointer","keyboard_cursor"]` | `{asset_id,asset_version,x:number,y:number,elapsed_ms:int,input_mode}`; finite `x,y` in [0,1]; exact asset match; one first action only. Optional private `evaluation.aois:[{id,polygon:[[x,y],...],success:boolean}]`. |
| `card_sort` / M2 | `mode:"open"\|"closed"\|"hybrid"`, `cards:[{id,label}]`, `categories:[{id,label}]`, `allow_unplaced:boolean` | `{groups:[{group_id,card_ids,label?}],unplaced_card_ids:string[]}`; each card occurs exactly once across groups/unplaced; open categories empty; closed/hybrid configured groups use configured IDs and omit label. New open/hybrid groups require `label:{text,language}`. |
| `tree_test` / M2 | `nodes:[{id,parent_id:string\|null,label,selectable:boolean}]`, `root_id` | `{visited_node_ids:string[],selected_node_id:string\|null,outcome:"selected"\|"gave_up",elapsed_ms:int}`; rooted acyclic connected tree; path starts at root and each transition is parent↔child; selected final node must be selectable. Private `evaluation.target_paths:string[][]` lists accepted root-to-target paths. |

**Prototype boundary.** External-link mode means instructions, explicit launch/return and participant-reported outcome only. Browsers isolate different origins; an embedded page is not permission to read its DOM or clicks [S2]. No arbitrary cross-origin capture, proxy scraping, injected tracking, credential collection or real production transactions. Uploaded asset flows may record platform-local steps, but a new verified-success mode needs a separate registry version and trustworthy instrumentation contract.
Only researcher-approved HTTPS destinations with recorded authorization are launchable; the backend must not fetch a supplied link to generate a preview. A pinned URL does not freeze the remote content: record the customer's reported build revision in the authorization record and label unverified remote revisions in comparisons. Partner telemetry is M3 opt-in, with origin/source checks and a session-bound nonce. Unavailable embedding falls back to an explicit new-tab link, without claiming step-level drop-off data.
**Five-second lifecycle.** Obtain one server-issued attempt ID before reveal; preload/decode without showing, then start a monotonic client timer at visible render, hide at the 5,000 ms deadline, and reveal recall prompts only after hiding. `performance.now()` is appropriate for elapsed client time [S3], not proof of attention.
Hide immediately on loss of visibility; interruption or refresh consumes that attempt and marks it invalid rather than allowing a clean retry. Proposed timing-valid window is 4,900–5,250 ms, uninterrupted, with matched start/end events; otherwise retain recall answers under an invalid/unknown timing stratum. Delayed telemetry leaves timing unknown until reconciliation, not the answer rejected. Report actual recorded duration and overshoot. Timing validity never certifies exact exposure or prevents screenshots/browser inspection.
**Preference assignment.** Before first exposure, persist one server-generated uniform random permutation per session/block; return its ID and ordered variants. Resume/retry returns the same assignment. Log actual renders and do not reshuffle on locale/device changes. This is within-person preference, not a production conversion experiment; no causal lift claims.
**First-click geometry.** `assets` fixes canonical decoded width/height in pixels after orientation correction, checksum and version. Replacement, cropping or rotation creates a new asset version and new AOIs. Scale uniformly with no crop: `x=(clientX-contentLeft)/contentWidth`, `y=(clientY-contentTop)/contentHeight`; measure the rendered image content rectangle, not borders, letterboxing, CSS container or device pixels.
Reject clicks outside that rectangle; never clamp them into success. Record input mode and optional rendered dimensions as diagnostics, not canonical dimensions. Reject zero-size geometry and nonfinite values. AOI polygons are normalized, simple, nonzero-area, implicitly closed and within [0,1]; the server tests the point against pinned polygons, including boundaries. Keep every overlapping AOI hit; success is “at least one successful AOI,” never double-count the click. Return no AOI labels or correctness to participants.
**Navigation fidelity.** Card-sort closed categories must all be represented (empty groups allowed); open/hybrid participant IDs cannot collide with configured IDs. Unplaced cards require `allow_unplaced=true`. Tree backtracking is retained in visit order; selecting a target is indirect success if the path contains a detour. `gave_up` requires null `selected_node_id`; a selected result must end at that selected node.

## 5. Longitudinal, moderated and language methods

| Type / milestone | Required `config` fields | Response and validation |
|---|---|---|
| `interview` / M2 | `duration_minutes:int`, `timezone:string`, `slot_set_ref:id`, `join_instructions_ref:id`, `recording_requested:boolean` | `{booking_id,action:"confirm"\|"cancel"}`; booking must belong to this participant and configured slot set. Slot selection uses an atomic reservation operation; submitting an answer does not reserve capacity. |
| `diary` / M2 | `timezone:string`, `local_dates:string[]`, `opens_at_local:"HH:MM"`, `window_minutes:int`, `grace_minutes:int`, `prompt_block_ids:string[]` | No fabricated diary answer: answer each referenced survey prompt with `occurrence_id`. Schedule must resolve to unambiguous UTC windows; repeated prompt blocks cannot also execute as ordinary study steps. |
| `accessibility.issue` / M2 | `task_block_id`, `capture_context:boolean`, `criterion_refs:string[]` | `{issues:[{description:{text,language},impact:"blocked"\|"difficult"\|"minor",context?:{input_method,assistive_technology},criterion_ref?:string,evidence_asset_ref?:asset_ref}]}`; empty issues allowed; context optional and consented, criteria limited to configured references. |
| `language.review` / M2 | `source_asset_ref`, `source_language`, `target_language`, `rubric_version`, `dimensions:[{id,min:int,max:int}]` | `{ratings:[{dimension_id,value:int}],issues:[{quote,explanation:{text,language}}],rewrite?:{text,language}}`; each dimension exactly once, bounded ratings; quote must occur in pinned source text. A paraphrase belongs in explanation, not a fabricated quote. |

Interview scope is scheduling, reminders, rescheduling, attendance, consent and provider join-link metadata—not video hosting, conferencing, streaming or recording infrastructure. Keep join links/contact data private until an authorized booking. Store UTC slot instants and the chosen IANA time-zone name [S8]; reject ambiguous local-time choices until an offset is selected. Capacity conflicts return 409; cancellation/reschedule releases capacity atomically and invalidates obsolete reminders.
Proposed scheduling bounds: interview duration 5..240 minutes; diary 1..90 unique `YYYY-MM-DD` dates, reporting window 1..1440 minutes and grace 0..1440 minutes. Reject overlapping windows including grace, invalid local clock times and unknown zones; pin the zone-rule revision used to resolve each occurrence. Recurring prompts are limited to M1 survey types in diary v1; other repeated methods need separate schema support.
Attendance is an attributed host/provider observation (`attended`, `no_show`, `unknown`), not inferred from a participant clicking a join link. The interview answer records an initial decision; later cancellation/rescheduling uses the booking lifecycle, not a second final answer. Recording consent is separate from participation; declining must have a stated nonrecorded path. M3 may accept authorized recording uploads with separate retention and transcript review.
Each diary occurrence has a stable ID, planned open/close/grace instants and status `scheduled`, `open`, `submitted`, `missed` or `cancelled`. Materialize occurrences before sending reminders; retries must not create duplicates. Mark submitted only when all required prompt answers are final. Accept late answers within grace and label them late; mark incomplete occurrences missed at grace expiry and reject later answers. Use server receipt time, so offline entry time cannot backdate submission. Freeze future windows unless an audited schedule revision is accepted; past windows never shift.
Accessibility issues describe observed user-research barriers, not compliance certification or a WCAG pass/fail badge. WCAG conformance has formal scope, full-page and complete-process requirements [S6]; a recruited sample and an issue list do not establish them. Do not require a diagnosis, disability proof or unnecessary health data. Record task context and accommodation separately from severity; an absence of reports is not an absence of barriers.
Use BCP 47 tags for text language [S5], with separate dialect/script metadata where necessary: Arabic, French, Tunisian Arabic, mixed speech and Arabizi are not interchangeable cohorts. Do not infer language qualification from a tag or auto-detection. Research prompts and their translations are reviewed and frozen before publication; participant UI language and answer language may differ.
Preserve every original answer and source text verbatim. Each derived translation identifies source answer/asset revision, target language, translator human/model, model/prompt revision if relevant, creation time and reviewer status. Never overwrite originals or send translations to an external service by default. Comparisons must state whether a human read the original or a translation; mixed-language scoring needs qualified reviewers.

## 6. AI evaluation, datasets and optional media (M3)

| Type | Required `config` fields | Response and validation |
|---|---|---|
| `ai.pairwise` | `item_ref:{dataset_id,dataset_version,item_id}`, `candidates:[{id,asset_ref}]` (exactly two), `rubric_version`, `dimensions:[{id,min:int,max:int}]`, `blind:true`, `randomization:"uniform_permutation"` | `{assignment_id,choice:"left"\|"right"\|"tie"\|"both_bad"\|"cannot_judge",ratings:[{candidate_id,dimension_id,value:int}],reason:{text,language}}`; rating for every candidate/dimension except `cannot_judge` requires empty ratings; reason always required. |
| `annotation` | `dataset_ref:{dataset_id,dataset_version}`, `item_id`, `task:"classification"\|"text_spans"\|"image_polygons"`, `label_set:[{id,label}]`, `instructions_version`, `min_annotations:int`, `max_annotations:int` | `{annotations:[{label_id,...}]}`; classification adds no fields; spans add integer `start,end`; polygons add `polygon:[[x,y],...]`. Labels known; unique classes; counts bounded; geometry pinned to source item. |
| `chatbot.sandbox` | `scenario_ref`, `business_policy_version`, `sandbox_revision`, `max_turns:int` (1..50), `max_duration_ms:int` (1..3,600,000), `mode:"manual_transcript"\|"adapter"`; `adapter_ref` required only in adapter mode | `{outcome:"completed"\|"failed"\|"gave_up",turns:[{role:"user"\|"assistant",text,language}],notes?:{text,language}}` in manual mode; adapter mode replaces `turns` with `transcript_ref`. Server attributes manual transcripts as participant-supplied, not verified bot output. |
| `media.review` | `asset_ref`, `kind:"video"\|"audio"`, `followup_block_ids:string[]`, `replay_allowed:boolean` | `{played_ms:int,completed:boolean,play_count:int}`; nonnegative bounded observations, not evidence of attention; asset MIME/duration must match kind. Answers to followups remain separate. |

**Human evaluation and tie-break.** Pairwise candidate content is intended stimulus, not another participant's study response; hide model/provider identities and left/right mapping until reporting. Freeze prompt, generated outputs, model revision/settings and rubric per dataset item. Do not regenerate candidates between reviewers. Resolve chosen side through the saved assignment; position bias remains reportable.
Language/pairwise rubric dimensions must have unique IDs, integer `min < max`, and 1..20 dimensions; accept each requested rating once within bounds. Candidate IDs are opaque participant-safe aliases, not model names. Media v1 allows at most 10 plays (one if replay is disabled); `played_ms` is cumulative observed playback and cannot exceed immutable duration × play count plus a disclosed 1,000 ms telemetry tolerance. Record seeking as playback behavior, not comprehension.
Ties, both-bad and cannot-judge are distinct outcomes, not half-wins by default. Preserve equal preference counts as “no winner.” For conflicting annotations or safety judgments, use independent blinded second review; unresolved disagreement goes to an authorized third reviewer/adjudicator. Retain all originals and reasoned adjudication; an AI vote never breaks a human tie. General testers cannot sign off medical, legal, financial or safety conclusions.
**Annotation precision.** Require `0 <= min_annotations <= max_annotations <= 100`; classification has at most one entry per known label. Text offsets are zero-based Unicode code-point offsets with exclusive end into the immutable original, `0 <= start < end <= length`; the frontend converts from its string indexing convention. Polygon coordinates use the first-click geometry contract. Label whether spans/polygons may overlap in a versioned dataset instruction; v1 defaults to no overlap within one answer. Separate contributor labels, adjudicated labels, hidden gold checks and training/export views.
Dataset ownership, contributor compensation terms, reuse/training permission and label license must be agreed before collection. Split train/evaluation items by stable item identity to avoid leakage; reviewers must not see others' labels or hidden gold. A reviewed dataset export pins source items, original labels, adjudication and consent scope; it is not automatically permission to resell customer data.
**Chatbot boundary.** Manual mode uses a customer-authorized sandbox and fictional task data. The adapter is optional, disabled by default and requires explicit customer authorization; it is not a field accepting any chatbot URL. Register server-side allowed destinations, credentials, version and permission scope; block private/link-local/metadata targets and redirects outside that allowlist, including after DNS resolution. Never expose credentials, invoke production actions or allow participant-supplied tools/endpoints. Enforce turn/time/token budgets, cancellation and tenant-scoped transcript access.
In adapter mode the server owns the transcript; participant answers cannot forge bot turns. Operational network failure is not model task failure. Adapters and external providers require explicit enablement and data-transfer approval; the default collection path depends on neither. AI analysis occurs after collection in bounded batches, with source-linked claims, cached versioned results and human approval; it cannot read another tenant's responses.
**No synthetic humans.** Preview data, model-generated answers and automated pre-scores are labeled nonhuman and excluded from human sessions, panel counts, incentives and human denominators. Models may assist translation, clustering and report drafting, not manufacture respondents or replace source evidence. Revoking AI consent prevents new analysis and triggers the applicable derived-data deletion policy.
**Media boundary.** M3 uploads/voice or screen evidence require separate explicit consent, rights, retention and private asset access; no silent capture. Browser display capture uses a user-mediated selection/permission flow [S4]; support and suitability remain to be verified. No face/emotion inference or biometric identity matching is implied. Voice accuracy needs a reviewed reference transcript and explicit error metric, not a “played” event.

## 7. Deterministic metrics and denominator rules

Every report states study/block/asset/rubric/metric versions, period, language/device/input-mode strata, assigned/exposed/started counts, valid responses, skips, inability, missingness, timing failures and review exclusions. Use human, consent-valid final responses under a named review-policy snapshot; show raw and reviewed counts separately. Ingestion acceptance is not review approval. Do not count events or answer revisions as extra people.
Do not silently drop incomplete sessions from attempt-based denominators. An unobserved event is unknown, not proof of nonexposure. Empty denominators yield `null` plus `n=0`, not zero percent. Show counts alongside rates; small recruited samples and opt-in panels do not justify population claims. Cross-study differences are descriptive unless a prespecified design supports stronger inference.

| Method | Metric contract and limitation |
|---|---|
| Single/multi | Selection count / valid answered question count; multi percentages may exceed 100% in total. Skips, inability and missing answers shown separately. |
| Rating/text | Rating distribution, median and optionally descriptive mean over valid ratings with scale shown; no automatic conversion across scales. Theme prevalence counts distinct source answers / reviewed eligible text answers, not quotes or model tokens; overlapping themes can exceed 100%. |
| Ranking/constant-sum | Rank distribution per item over respondents ranking it; show item-specific n for partial rankings, never give unranked items a last rank. Mean allocated points / complete valid allocations; zero is a real allocation, missing is not zero. |
| Prototype/tasks | Self-reported completed / task starts, with failed/gave-up/unknown counts; confirmed completion needs a future verified evidence mode. Median elapsed for completed tasks shows its n and cannot characterize people who abandoned. External links cannot provide field-by-field abandonment. |
| Five-second | Recall coding counts / eligible recall answers from timing-valid exposures; show timing-invalid/unknown strata and missing followups separately. Coding needs a pinned human-reviewed rubric; time is observed, not guaranteed attention. |
| Preference/pairwise | Variant votes or candidate wins / valid decisions, retaining ties/none/both-bad; cannot-judge reported separately and excluded from judged-decision denominator. A decisive-only rate may also be shown with its smaller n explicitly labeled. Never break equal vote totals arbitrarily. |
| First-click | Hits in any successful AOI / valid first clicks; no-click starts reported separately. Heatmaps include all valid points; overlapping AOIs do not increase total n. Compare keyboard-cursor and pointer strata separately. |
| Card/tree | Co-grouped card pair / responses placing both cards; unplaced pairs are not disagreement. Tree target selections / task starts, plus direct/indirect/failed/unknown; time among completed selections only, with n. |
| Interview/diary | Attended / scheduled noncancelled bookings whose end time has passed; unknown attendance shown. Diary submitted / due noncancelled occurrences, with on-time/late split; report participant retention separately so prolific diarists do not dominate. |
| Accessibility/language | Participants reporting each barrier / participants attempting that task; issue counts are not prevalence or WCAG conformance. Language dimension distributions show qualified reviewers and original-versus-translated basis; small dialect groups are not interchangeable. |
| Annotation/chatbot/media | Exact agreement / items independently double-labeled under the same task/rubric; agreement is not truth and cannot be computed on adjudicated labels as if independent. Chatbot reviewed success / evaluable sandbox attempts, alongside excluded infrastructure failures. Media completion is reported playback, not recall or persuasion. |

## 8. Events and frontend responsibilities

Event envelope: `event_id`, `schema_version:1`, `block_id`, `study_version_id`, `attempt_id` (ID or null for scheduling events), `sequence` (positive integer), `name`, `client_elapsed_ms` (nonnegative integer or null), optional `occurrence_id`, and allowlisted `payload`. Sequence is scoped to source/session/block/attempt-or-occurrence. Server binds session/source, assigns `received_at` and stores events in `response_events`; client timestamps are not authoritative. Deduplicate event IDs and reject reuse with different content; retain reordered receipt separately from declared sequence. No raw answers, contact details, credentials or transcripts in telemetry.

| Event names | Source and allowed purpose |
|---|---|
| `block.started`, `block.rendered`, `block.skipped`, `block.unable`, `answer.accepted`, `session.completed`, `session.withdrawn` | Start/accept/completion/withdrawal are server lifecycle events; session-wide events use null `block_id`/`attempt_id`; render is client observation; skip/inability emitted after validated status. |
| `prototype.launched`, `prototype.returned`, `prototype.step_reported`, `prototype.finished` | Client launch/return; steps only in platform-controlled asset flows; finish follows accepted outcome. |
| `exposure.started`, `exposure.ended`, `exposure.interrupted`, `visibility.changed` | Client timing/visibility with attempt ID; no claim of gaze tracking. |
| `assignment.created`, `variant.rendered`, `first_click.recorded`, `card_sort.changed`, `tree.node_visited` | Assignment is server-owned; render/navigation client-owned; first click accepted once; card changes carry IDs/counts, not category free text. |
| `interview.booked`, `interview.rescheduled`, `interview.cancelled`, `interview.attendance_recorded` | Server/authorized host/provider; booking IDs only, never meeting secrets. |
| `diary.occurrence_opened`, `diary.reminder_sent`, `diary.occurrence_submitted`, `diary.occurrence_missed` | Server/scheduler; occurrence IDs; notification send does not prove delivery or reading. |
| `issue.submitted`, `language_review.submitted`, `pairwise.submitted`, `annotation.submitted` | Server after answer acceptance; IDs and status only. |
| `chatbot.turn_recorded`, `chatbot.adapter_failed`, `media.played`, `media.ended`, `media.capture_consented` | Adapter turn references, operational error class, client playback observations, consent reference; no transcript text. |

Frontend must render only participant-safe projections; support Arabic RTL, mixed-direction text, keyboard interaction and labeled controls without encoding answers through color alone. Present planned task demands before enrollment and provide an inability/withdrawal path. Timed visual and spatial methods may need a separately labeled accommodated study; do not silently combine different protocols.
Use server-provided order/assignment, stable choice IDs and current asset geometry; no client reshuffle, client scoring or hidden answer keys. Block-local prevalidation improves feedback but never replaces backend validation. Prevent accidental double submission while retrying with the same key; show saved/unsaved state accurately.
Preload five-second assets, handle visibility/refresh, remove stimuli from the accessible tree after exposure, and do not let back-navigation restart primary exposure. Freeze first click before asynchronous upload. Supply keyboard alternatives for sorting/ranking and a declared keyboard-cursor mode for spatial tasks; preserve input mode in analysis.
Do not preload private answers, gold labels, AOIs, model identities, aggregate findings or other participants' data. Persist only minimal retry state with consent and a short expiry; purge it on logout/withdrawal. Sensitive responses must not enter third-party analytics, session replay or browser error reports.

## 9. Concrete JSON fixtures

Each fixture is an author-side block plus a valid responded answer under the contracts above, not a participant GET payload. Opaque references assume authorized records already exist; referential/database validation has not been executed. Fixture assets are illustrative private immutable image records; `as_home` version 1 has canonical dimensions 1200×800. Companion recall block `b_recall` is a required French `survey.text` with lengths 1..1000 in the same study version.

### A. Constant-sum prioritization
```json
{
  "block": {"block_id":"b_budget","study_version_id":"sv_demo_v1","type":"survey.constant_sum","schema_version":1,"required":true,"prompt":{"fr":"Répartissez 100 points entre ces priorités."},"config":{"options":[{"id":"speed","label":{"fr":"Rapidité"}},{"id":"support","label":{"fr":"Assistance"}},{"id":"price","label":{"fr":"Prix"}}],"total_points":100}},
  "answer": {"study_version_id":"sv_demo_v1","block_id":"b_budget","schema_version":1,"client_submission_id":"sub_budget_1","status":"responded","response":{"allocations":[{"option_id":"speed","points":40},{"option_id":"support","points":25},{"option_id":"price","points":35}]}}
}
```

### B. Five-second exposure (recall collected separately)
```json
{
  "block": {"block_id":"b_exposure","study_version_id":"sv_demo_v1","type":"five_second","schema_version":1,"required":true,"prompt":{"fr":"Regardez cette page pendant cinq secondes."},"config":{"asset_ref":{"asset_id":"as_home","asset_version":1},"exposure_ms":5000,"interruption_policy":"invalidate","recall_block_ids":["b_recall"]}},
  "answer": {"study_version_id":"sv_demo_v1","block_id":"b_exposure","schema_version":1,"client_submission_id":"sub_exposure_1","status":"responded","response":{"attempt_id":"attempt_exposure_1","visible_ms":5012,"interrupted":false}}
}
```

### C. Randomized preference with a reason
```json
{
  "block": {"block_id":"b_preference","study_version_id":"sv_demo_v1","type":"preference","schema_version":1,"required":true,"prompt":{"fr":"Quelle page préférez-vous, et pourquoi ?"},"config":{"variants":[{"id":"v_a","asset_ref":{"asset_id":"as_checkout_a","asset_version":1},"label":{"fr":"Option A"}},{"id":"v_b","asset_ref":{"asset_id":"as_checkout_b","asset_version":1},"label":{"fr":"Option B"}}],"randomization":"uniform_permutation","allow_tie":true,"allow_none":true}},
  "assignment": {"assignment_id":"assign_pref_1","study_version_id":"sv_demo_v1","block_id":"b_preference","session_id":"se_demo","ordered_variant_ids":["v_b","v_a"]},
  "answer": {"study_version_id":"sv_demo_v1","block_id":"b_preference","schema_version":1,"client_submission_id":"sub_pref_1","status":"responded","response":{"assignment_id":"assign_pref_1","decision":"variant","selected_variant_id":"v_b","reason":{"text":"Le prix total est plus visible.","language":"fr"}}}
}
```

### D. First click with a private AOI
```json
{
  "block": {"block_id":"b_click","study_version_id":"sv_demo_v1","type":"first_click","schema_version":1,"required":true,"prompt":{"fr":"Où cliqueriez-vous pour suivre votre commande ?"},"config":{"asset_ref":{"asset_id":"as_home","asset_version":1},"coordinate_space":"normalized_asset","input_modes":["pointer","keyboard_cursor"]},"evaluation":{"aois":[{"id":"aoi_tracking","polygon":[[0.7,0.1],[0.9,0.1],[0.9,0.25],[0.7,0.25]],"success":true}]}},
  "answer": {"study_version_id":"sv_demo_v1","block_id":"b_click","schema_version":1,"client_submission_id":"sub_click_1","status":"responded","response":{"asset_id":"as_home","asset_version":1,"x":0.8,"y":0.18,"elapsed_ms":2300,"input_mode":"pointer"}}
}
```

## 10. Example API contract

Proposed participant endpoint: `POST /v1/sessions/se_demo/answers`; HTTPS, scoped participant authorization, `Content-Type: application/json`, `Idempotency-Key: sub_click_1`. Body is fixture D's `answer` object exactly. Server verifies tenant/session/consent/version/current block/asset, first-click uniqueness and limits, then commits the answer and server event atomically. Metric computation is not part of the participant response.
On first acceptance: HTTP `201 Created`, `Location: /v1/sessions/se_demo/answers/an_click_1`, `Cache-Control: no-store` [S7]. The Location is an own-session receipt resource, not a report or scoring endpoint.
```json
{"answer_id":"an_click_1","client_submission_id":"sub_click_1","status":"accepted","study_version_id":"sv_demo_v1","block_id":"b_click","next_block_id":null,"session_ready_to_complete":true}
```
Within the authenticated session, bind the idempotency key to a canonical-body hash and stored receipt for the session's retention period; same key/body returns the original status and receipt, including after finalization, only while receipt access remains authorized. Different body/key reuse returns 409. A new key attempting a second final answer also returns 409. These retry semantics are application choices, not an assertion that POST is inherently idempotent [S7].
Return 400 for malformed JSON, 401 for missing/expired authentication, 404 for inaccessible session/block, 409 for version/state/assignment conflicts, 413 for size limits, 422 for field/semantic errors and 429 for rate limits. Error details identify public field paths only; never reveal private expected answers, AOIs, gold labels or another session's existence.
```json
{"error":{"code":"invalid_response","fields":[{"path":"response.x","code":"out_of_range"}],"retryable":false}}
```
`GET /v1/sessions/se_demo/next-block` returns only the authorized participant projection and saved assignment; author configuration is a separate researcher capability. `POST /v1/sessions/se_demo/blocks/b_exposure/start` issues/resumes the bound attempt ID without creating an extra exposure. Event batches use `POST /v1/sessions/se_demo/events`; completion is a separate `POST /v1/sessions/se_demo/complete` checking required reachable answers. No endpoint here grants access to study-wide responses or reports.

## 11. Templates, staging and privacy gates

Templates are versioned recipes of registry blocks, prompts, branching and report presets—not separate business/product/marketing response tables. Copy a template into a draft; later template edits never alter published studies.

| Cases in the product documents | Reused template blocks |
|---|---|
| Concept, pricing/offer, competitor comparison, feature prioritization | Preference + single/rating/text; ranking or constant-sum for priorities. Stated willingness to pay is not a purchase. |
| Onboarding, forms, customer journey, support knowledge/instructions | Prototype tasks + tree/first-click + comprehension text/rating; authorized test environments, not production credential capture. |
| Ad messages, brand perception, landing pages, audience discovery, pre-launch checks | Five-second + preference + survey + first-click; recruitment strata belong to the study, not duplicated block types. |
| Market entry, language/dialect clarity, accessibility | Survey + language review + task-linked accessibility issues; freeze language and task versions. |
| Video ads, voice review, chatbot quality/safety, dataset creation | Media review + survey; authorized chatbot + pairwise/rating; annotation with specialist review where needed. |

| Stage | Proposed delivery boundary |
|---|---|
| M1 — basic | Single/multi/rating/text surveys, text-reported prototype tasks, five-second images, randomized preference, immutable publishing, private assets, consent, basic deterministic reporting and retry safety. No recordings or automatic AI. |
| M2 — methods | Ranking/constant-sum, first-click/AOI reporting, card sort/tree test, interview scheduling, diary occurrences, accessibility issues, language review and expanded templates. |
| M3 — media / AI extended | Pairwise datasets, annotation, separately consented media/voice, source-linked post-collection AI, optional authorized chatbot adapter/partner telemetry. Cloud AI is the chosen analysis provider; collection itself must continue during provider outages. |

M0 foundations and M4 deployment hardening are owned by the main blueprint; this method schedule does not supersede them. Registry publication must reject unavailable stages, rather than allow a study the participant frontend cannot run.
Privacy gates apply before every release: tenant/private-panel isolation; purpose-specific consent; minimal demographic/context collection; private assets with short-lived authorized access; no raw answer bodies in logs; retention/deletion covering answers, events, recordings, translations, exports and AI caches. Separate contact/scheduling identity from research IDs; no participant can enumerate other sessions or see study answers, reviewer notes, hidden correctness rules or aggregate results.
Participant-visible candidate AI responses and task instructions are explicitly approved stimuli, not a loophole for exposing collected answers. Shared reports require researcher authorization, redaction and aggregation thresholds; small language/disability cohorts need disclosure review. Customer reuse/training and international transfers require explicit permission and qualified local legal review, not a claim that this design establishes compliance.

## 12. Primary technical references and review checklist

- [S1 — JSON Schema Draft 2020-12 Core](https://json-schema.org/draft/2020-12/json-schema-core.html), schema dialect/identifiers; proposed validation choice, not a supplied executable schema.
- [S2 — WHATWG HTML: origins](https://html.spec.whatwg.org/multipage/browsers.html#concept-origin), browser cross-origin isolation and DOM-access boundary.
- [S3 — W3C High Resolution Time](https://www.w3.org/TR/hr-time-3/), monotonic elapsed-time model; current publication is a Working Draft, not a guarantee of browser timing precision.
- [S4 — W3C Screen Capture](https://www.w3.org/TR/screen-capture/), user-mediated capture and permission model; Working Draft, with runtime/browser support unverified here.
- [S5 — RFC 5646 / BCP 47](https://www.rfc-editor.org/rfc/rfc5646), language/script tagging; cohort and dialect policies here remain product choices.
- [S6 — WCAG 2.2 conformance requirements](https://www.w3.org/TR/WCAG22/#conformance-reqs), formal conformance scope rather than research-study certification.
- [S7 — RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes), HTTP status semantics; retry deduplication above is a proposed application contract.
- [S8 — IANA Time Zone Database](https://www.iana.org/time-zones), time-zone rule data; freeze resolved diary/booking instants rather than relying on an unversioned local clock.

Design review checks: all registry types have config/response/event/metric ownership; four fixtures are JSON and obey their stated local constraints; participant projections exclude evaluation data; missingness and ties remain explicit; all product use cases map to templates/stages. Future implementation tests must cover tampered assignments, inaccessible assets, duplicate submits, invalid polygons/paths/sums, interrupted exposure, late diaries, booking races, translated-text provenance and cross-tenant access. Document checks are not evidence these runtime tests have passed.
