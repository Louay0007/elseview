# P10/P11 — Bounded AI assistance and advanced research methods

Development implementation. The four-service architecture is unchanged. No live
provider, cloud account or paid request is needed for ordinary tests.

## P10 configuration and operations

`AI_MODE` defaults to `mock`; `disabled` denies creation. `live` requires an exact
model, backend-only key, approved HTTPS host list, capability approval, privacy
approval/record and explicitly configured Decimal pricing. `.env.example` documents
all `LLM_*` controls. Changing a setting requires backend recreation; never put a key
in a browser, URL, source file, command log or client request.

The installed OpenAI SDK uses its HTTPX2 transport. The adapter disables SDK retries,
redirects and environment proxy configuration, uses Chat Completions, and sends only
the operator-declared output-limit/JSON-format arguments. No fallback provider,
tools, streaming, audio transcription or arbitrary endpoint is supported.

Under `/api/v1/workspaces/{workspace_id}/ai`:

- `POST /runs`: `study_id`, optional `snapshot_id`, `operation`, `instruction`,
  `command_key`, and `researcher_text_approved` when supplying researcher text.
- Operations: `study_helper`, `themes`, `failure_clustering`, `translation`,
  `report_writer`, `research_qa`, `quality_suggestion`, `campaign_clarity`,
  `sentiment_suggestion`.
- `GET /runs/{run_id}`: authorized run state, draft, exact coverage and charge state.
- `POST /runs/{run_id}/approve`: human approval of a valid draft; it does not change
  participant answers, report approval or compensation decisions.
- `POST /runs/{run_id}/reconcile`: authorized operator records nonnegative
  `actual_cost` and an opaque `reference` for a terminal uncertain attempt.

All operations return a strict draft findings/evidence/limitations structure, with
task-specific instructions. Translation remains separate from originals. These are
assistance drafts, not automatic study publication, emotional diagnosis or quality
rejection. Insufficient evidence is explicit. Counts are computed in code.

Human-only studies deny AI. Snapshot operations require current accepted-source
authority and each included participant's exact study-version `ai_processing`
consent. Provider inputs contain bounded textual sources, not identity/profile/event
records. Email/phone redaction is limited and must not be mistaken for comprehensive
PII detection. Operator privacy approval and minimum-data handling remain required.

### Cost and failure behavior

- UTF-8-byte upper bounds plus protocol overhead estimate input size when no verified
  model tokenizer exists. Prices and balances use Decimal provider currency, never
  participant TND millimes. Study and UTC daily workspace budgets reserve together.
- The embedded durable runner commits a sent marker before external I/O, then closes
  the transaction. Completion checks lease, source permissions, consent and configuration.
- Known rejection/connect-before-send failures release the hold. Read/write timeout,
  unknown server outcomes or absent usage remain conservatively charge-uncertain.
  There is no assumption that a timed-out request was free.
- SDK/job automatic retries are disabled for AI. A fresh explicit command may retry a
  known released 429/connect-before-send result, honoring Retry-After and a maximum
  of two attempts for the same request/cache identity. Uncertain attempts require
  reconciliation, not blind retry.
- Valid cached outputs are references to persisted runs, keyed by source, privacy,
  provider/model/configuration, prompt and schema. Access is revalidated on reuse.
- Chunk overlap and deduplicated quote spans record actual covered sources. Partial
  context is labeled partial. Evidence must match an allowed immutable original and
  a span actually supplied to the provider.

## Optional participant consent

Verified participants—not researchers acting for them—use:

- `GET /api/v1/collection/sessions/{session_id}/optional-consent?purpose=ai_processing`
  (or `accessibility_context`) to retrieve locale-matched documents and digests.
- `POST` the same path with `purpose`, `document_id`, `presented_digest`,
  `decision` (`granted`, `declined`, `withdrawn`) and unique `receipt_key`.

Bearer authentication must match the session's participant. Receipts bind the exact
study version; account membership in the researcher workspace is unnecessary.
Refusing AI/context does not imply withdrawal from ordinary collection. Revocation
invalidates AI derivatives conservatively within the workspace. Financial charge
metadata remains available for reconciliation; deleted research does not make an
already dispatched provider charge disappear.

## P11 registry methods

Every method has strict configuration/value/event contracts, safe projections,
publication validation, reducers and actual React renderers:

| Type | Contract highlights |
|---|---|
| `survey.ranking` | Unique allowed ordered keys, exact configured rank count; partial ranks use item-specific denominators, not implicit last place. |
| `survey.constant_sum` | Each option once, bounded nonnegative integer points, exact total. |
| `first_click` | Immutable asset/version/dimensions; finite normalized coordinates; declared pointer/keyboard mode; one accepted event latched before its matching answer. Private polygon AOIs never enter participant payloads. |
| `card_sort` | Open/closed/hybrid groups, unique card placements, explicit unplaced policy and bounded custom labels. |
| `tree_test` | Rooted acyclic navigation graph, adjacent paths, selected/gave-up distinction, detours/backtracking; private target paths excluded from projection. |
| `accessibility.issue` | Task-linked barriers and impact; no required diagnosis. Optional context is accepted only with explicit current version-bound consent. Evidence attachments are not enabled. |
| `language.review` | Pinned text stimulus/checksum, exact source quotes, every rubric dimension once, separate optional target-language rewrite. Reviewer basis is disclosed as unverified participant self-report, not professional certification. |

First-click clients send `first_click.recorded` through the existing event batch
endpoint with a fresh event ID and contiguous sequence starting at zero. The first
valid event is authoritative; a different second click conflicts. Exact event retries
are safe. Answer coordinates/mode/timing must match the latch. Invalid points do not
consume the first-click slot. AOI boundaries are inclusive; overlaps do not duplicate
the overall participant denominator, and pointer/keyboard strata stay separate.

## React client and geometry

`/Users/user/Workspace/startup-act/frontend/AdvancedMethods.jsx` is used by preview
and the participant runner. Spatial coordinates account for object-fit containment,
letterbox offsets, resize and orientation. Selection freezes synchronously before
network work. Keyboard cursor movement is explicit, with native controls for the
other methods. No hidden scoring keys are consumed by the browser.

An existing consented session can be resumed using the fragment parameters
`session`, `session_token` and `locale`. The runner removes credentials from the
address bar and keeps them in memory. It supports advanced methods plus core survey,
preference and prototype blocks; real five-second collection is explicitly blocked
until its browser attempt/event flow is implemented. Refresh requires reopening the
authorized entry link. Recruitment, session creation and optional-consent granting
remain API operations outside this minimal runner.

## Validation boundaries

Backend tests are mocked-provider by default. Live provider compatibility, pricing,
privacy terms and Arabic/French/dialect quality remain external human-reviewed gates.
The generic assistance schema is not a guarantee of semantic accuracy or injection
immunity. No paid call was made to validate this implementation.

The React production build, Node geometry tests and a Chrome synthetic renderer smoke
were executed. The Chrome DOM reported passing mount/ranking/issue/image checks,
but required timeout termination. Full authenticated browser E2E, real device
orientation/visibility, complete keyboard/screen-reader walkthrough and accessibility
conformance are **not** certified. See implementation status for exact test totals.