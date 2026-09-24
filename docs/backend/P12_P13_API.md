# P12/P13 — Longitudinal research and human evaluation

Development APIs in the existing four-service application. All routes use `/api/v1`.
Bearer authentication and current study permissions are required. No conference
hosting, cloud transcription, automated chatbot connector or paid call is enabled.

## Interviews

Researcher prefix: `/workspaces/{workspace_id}/longitudinal`.
Participant prefix: `/participant/longitudinal`.

- Researchers `POST /slots` with published `version_id`, IANA `timezone`, local
  `starts`/`ends` objects (`local`, optional `fold`), `capacity` and HTTPS `join_url`.
  Slots are future, 5–240 minutes. Nonexistent local times are rejected; repeated
  daylight-saving times require explicit fold. Resolved UTC instants are retained.
- Participants `GET /slots?workspace_id=...&version_id=...` without private join links.
  `POST /bookings` takes `slot_id` and stable UUID `request_key`. Booking verifies
  participation/consent and serializes capacity and overlapping appointments.
- `GET /bookings?workspace_id=...` shows only the caller's bookings. Join links are
  returned only for current authorized booked participation, not cancelled or
  consent-withdrawn participation.
- `POST /bookings/{id}/cancel` requires `expected_revision`.
  `/reschedule` additionally takes replacement `slot_id`. Old reminder revisions
  become invalid; changing the booking cannot create a second live capacity claim.
- Researcher `POST /bookings/{id}/attendance` takes `expected_revision`,
  `attendance: attended|absent` and a note. Actor and server timestamp are retained.
  Opening a link never establishes attendance; unknown remains a distinct state.
- Durable internal `longitudinal.reminder` jobs publish in-app notification records
  once, rechecking booking revision, time, consent and authority at completion.
  This is not email/SMS delivery. The participant notification inbox exposes only
  their own currently authorized reminders.

## Diary occurrences

- Researcher `POST /diary-schedules` takes `base_session_id`, IANA `timezone` and
  bounded ordered `windows` with local `opens`, `due`, `grace`. Windows cannot
  overlap, dates are unique and the series is immutable. Configure the series before
  initial participation is accepted so earning terms cannot change after acceptance.
- Participant `GET /diary-occurrences?workspace_id=...` returns their schedule and
  server-calculated open/grace/missed/submitted status.
- `POST /diary-occurrences/{id}/start` takes a cryptographically random URL-safe
  `capability`. Reuse the same capability for retry/resume. Each occurrence creates
  one separate `collection_sessions` row tied to the same candidate and version.
- Complete initial participation first. Diary v1 repeats the published core-survey
  version; unsupported methods are denied rather than partially rendered. It does
  not yet support a separate initial questionnaire and diary prompt subset.
- Answer/event/submission APIs remain the existing collection APIs. An optional
  supplied occurrence ID must match the authorized session. Server time controls
  open/due/grace boundaries; client timestamps cannot backdate submission.
- The initial reservation is consumed once. A series reward uses the base-session
  source identity and is earned only when the initial session and every required
  occurrence have final human acceptance, regardless of review order. Repeated
  acceptance cannot issue another full reward.
- Version-scoped metrics distinguish due/submitted/late occurrences from participant
  retention. Interview metrics count ended noncancelled bookings and retain unknown
  attendance. Metrics are descriptive, not population estimates.

## Private recordings and transcripts

Existing private upload intents accept bounded validated WAV files. Staff uploaders
need their existing recording authorization; attaching a participant recording also
requires the participant's exact study-version recording consent. Participants grant
or refuse it through the existing session `/optional-consent` API with
`purpose: "recording"`, exact displayed document/digest and their own bearer identity.

- Researcher `POST /recordings` supplies `asset_id`, `version_id`, `subject_id` and
  `consent_receipt_id`. The asset must be ready, unexpired and permission-valid.
- `GET /recordings/{id}` rechecks source and consent access.
- `POST /recordings/{id}/transcript` accepts exactly one of plain `text` or bounded
  `segments` (`start_ms`, `end_ms`, `speaker`, `text`). Segments are ordered,
  nonoverlapping and contained within immutable recording duration. Repeat identical
  imports are safe; changing an imported transcript conflicts.
- These transcripts are uploaded human/operator material, not verified speech
  recognition. Revocation denies recording access through both longitudinal and
  existing asset-download routes and removes dependent transcript access. Erasure
  also deletes linked physical files even when the uploader owns the storage asset.

## P13 human evaluation workbench

Prefix: `/workspaces/{workspace_id}/evaluation`. This is a standalone authenticated
human workbench; it does not falsely advertise unsupported study-registry methods.

1. `POST /datasets` creates an immutable dataset key/version with a study, rights,
   typed schema and bounded source items. Rights explicitly declare owner, reuse,
   training permission, label license, consent scope and compensation terms.
2. Supported tasks: `classification`, `text_spans`, `image_polygons`, `pairwise`,
   `language_review`, `sandbox`. Sources and schemas cannot be edited after creation;
   changes require another dataset version.
3. Source identity is content-derived across versions and caller keys. The same
   source identity cannot cross train/evaluation partitions. Image identity uses the
   checksum of a permission-checked, pinned private PNG, not a remote URL or SVG.
4. Study administrators `POST /datasets/{id}/assignments` with `item_id`,
   `reviewer_id` and `kind: independent|adjudication`. Two distinct independent human
   labels precede one fresh adjudicator. Reviewers cannot allocate their own work
   through mere review permission.
5. `GET /assignments` lists the caller's authorized work. `GET /assignments/{id}`
   returns a safe projection; pairwise model revisions/settings and internal mapping
   are hidden. Each assignment's side order is immutable. Adjudication originals
   are remapped into the adjudicator's displayed sides, not misleading raw positions.
6. `POST /assignments/{id}/outcome` records a typed outcome with mandatory human
   reason/language. Identical retries return the original; changed final answers
   conflict. The server attributes the authenticated human; clients cannot forge
   model votes or provenance.
7. `GET /datasets/{id}/report` keeps tie, both-bad and cannot-judge distinct, reports
   position choices, and computes agreement only from independent originals—not
   adjudicated labels counted as independent observations.
8. `POST /datasets/{id}/export-review` requires a reason and complete originals plus
   adjudication. `GET /datasets/{id}/export` returns the reviewed digest-bound
   original labels, adjudication, immutable sources/schema and rights. Revoked
   contributor/approver/source permissions invalidate access. Raw dataset access is
   separately permission-gated.

Classification labels must be known and unique. Text spans use Unicode code-point
offsets, exclusive end; React converts UTF-16 selection offsets and rejects split
surrogates. Polygons use finite normalized coordinates, simple nonzero-area shapes,
and the declared overlap policy. Pairwise/rubric ratings cover each candidate and
dimension exactly once; cannot-judge uses no ratings. Equal votes do not invent a winner.

Sandbox scenarios are explicitly approved, versioned and fictional-input-only.
Only manual transcripts are enabled, with turn/duration/character caps and separate
infrastructure-failure outcomes. Destination URLs, adapter mode, credentials and
production actions are rejected. Transcript authenticity is participant-supplied,
unverified; bounded pattern checks do not guarantee comprehensive PII detection.

## Client and validation boundaries

The diagnostic landing page offers forms for an authorized participant schedule and
assigned human evaluation. Tokens remain in memory, not URLs/local storage. Closing
or refreshing clears them. Diary child capabilities must be retained for resume;
the minimal UI does not implement account-based capability recovery after reload.

Native labeled controls, numeric keyboard polygon entry, Unicode helpers and stable
retry payloads are implemented. Build/Node tests and synthetic Chrome DOM smoke
checks are recorded in `/Users/user/Workspace/startup-act/frontend/tests/README.md`.
They are not full authenticated browser E2E, device, screen-reader or accessibility
certification. Cloud transcription and optional external sandbox connectors remain
disabled; no external service compatibility or human dialect quality is claimed.

Migration rollback drops P12 occurrence responses before restoring the old one-session
constraint; do not downgrade a populated deployment without an explicit backup and
data-retention decision. Executed evidence and other limits are in
`/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md`.