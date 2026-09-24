# Frontend verification

## Current account and navigation increment

The default page now uses `AccountApp.jsx`, not the manual-token diagnostic forms. It supports registration, email-code verification/resend, password recovery/reset, sign-in, workspace creation/listing, authorized studies/version history, current-reviewer assignment navigation, existing participant schedules, and login-session listing/revocation. `accountSession.js` keeps bearer and CSRF credentials in memory, serializes refresh, never automatically replays business mutations, and fences late responses after sign-out. Reload deliberately requires reauthentication. Deep links contain resource IDs only. Participant-only accounts may open an authorized schedule resource link without researcher membership; there is not yet a participant study-discovery inbox.

Executed: **19 Node tests**, production build, and installed-Chrome account/research/longitudinal fixtures passed. Account fixtures cover generic email responses, validation, double submit, verification/recovery/reset, authorized workspace/study/reviewer/schedule navigation, session revocation, permission denial, empty/loading states, uncertain non-idempotent creation, sign-out and delayed-response isolation. Desktop 1440×900 and mobile 390×844 include native Enter, no overflow, a main landmark, text contrast 15.315:1 and action contrast 8.783:1. Credential values are absent from browser storage/URLs/rendered text. These use synthetic HTTP responses, **not** persisted browser/API/PostgreSQL journeys. Native VoiceOver, Arabic-reader and full WCAG acceptance remain unverified.

```sh
cd frontend && npm test && npm run build
# With a local Vite server already running:
CONTRACT_BASE_URL=http://127.0.0.1:8091 CONTRACT_VIEWPORT=390x844 \
  node scripts/browser_contracts.mjs /tests/account.html /tests/research.html /tests/longitudinal.html
```

V2 five-second collection now prepares and decodes a private image before start, enforces one durable attempt, conceals it after the timed window and interrupts on visibility loss or unresolved resume. `tests/exposure.html` plus `tests/run-exposure.mjs` cover synthetic desktop/mobile timing and native Enter. These are not physical display-timing guarantees or real participant evidence.

## Participant assessments and real account integration

`#/participant/assessments` is accessible to signed-in participants without workspace membership. `ParticipantAssessments.jsx` uses the current memory-only account transport and family scope. It provides separate consent, a paginated retained-consent history (including unused grants no longer represented in the catalogue), explicit withdrawal, approved assessment attempts, manual-review status, expiry and appeals. Unknown commands retain exact retry bodies; navigation and account changes fence late private responses. The component has no nested `main` and no operator/key access. `/tests/assessments.html` passed desktop/mobile browser contracts; the account fixture also checks authenticated navigation and landmark integration.

`backend/tests/test_live_account_browser.py` adds **two passing real browser/API/PostgreSQL/Valkey journeys**, at 1440×900 and 390×844. With a pre-provisioned verified synthetic identity, the current production build signs in, creates exactly one workspace, reloads/re-authenticates, retrieves persisted state, opens assessments, and revokes other/current login sessions. Database assertions verify one workspace and two revoked refresh families. Browser transport and cache are not mocked. The test-only route is never registered in the shipped application. No full ten-story, live-provider, native-screen-reader or Arabic-reader acceptance is implied.

```sh
backend/.venv/bin/python scripts/test_fresh.py --with-browser -q tests/test_live_account_browser.py
```

This needs cached pinned PostgreSQL/Valkey images, installed Chrome/Node and frontend dependencies. It builds the frontend, serves an isolated app on an ephemeral loopback port and cleans its own resources; it does not use the shared development deployment.

## Participant profile integration

`#/participant/profile` is linked from the signed-in account navigation without requiring workspace membership. `ParticipantProfile.jsx` provides public-panel creation/update/rejoin, version1/2 consent with exact digests, server vocabulary-driven country/city/self-reported experience fields, separate confirmed withdrawal and read-first reconciliation of uncertain requests. It never automatically retries a mutation or treats profile withdrawal as account erasure. First-use is GET404; withdrawn attributes are empty. The API has no pause command or interests attribute; the UI explicitly discloses these limits rather than substituting withdrawal or experience.

`/tests/profile.html` passed **51 synthetic checks at each desktop/mobile viewport**, actual CDP Enter-triggered save, AX-main,44px targets,15.315:1 text/8.783:1 action contrast and no overflow. After account integration,19 Node tests, production build and both account viewport fixtures passed; exact route/extra-segment rejection, authenticated adapter, current-page navigation and one main landmark are checked. The parent captured desktop/mobile screenshots in session artifacts. See [profile fixture contracts](profile.md) for the detailed state matrix. No real profile mutation journey, native screen-reader/Arabic-reader acceptance or new backend pause/interest implementation is implied.

## Participant history and reporting integration

`#/participant/history` uses the authenticated account adapter to enumerate only the current participant's workspace references and scoped response/review/appeal/reward/payment/attendance history. No staff meeting link, payment evidence, global reputation score or private team name is exposed. Current research source/consent gates differ deliberately from retained financial access. Unknown appeal requests retain the exact command and reason; a confirmed appeal refreshes the history, while workspace/session changes and read denials clear private records. Loaded-record denominators are explicitly not complete-population scores. `/tests/history.html` passed **38 assertions per desktop/mobile viewport**, plus actual CDP Enter-triggered refresh and AX-main checks. Associated native radio labels and select/textarea controls meet the unchanged44px target check; contrast is15.315:1 for text and8.783:1 for actions, with no overflow.

`#/workspaces/{workspaceId}/reports` integrates `ResearchReports.jsx` and the real bounded report-index API. `/tests/reports.html` passed **51 checks per desktop/mobile viewport**: list/detail/version/approval, summary/raw permission errors, private JSON/CSV/PDF/XLSX downloads, exact unknown retries, session fencing and object-URL cleanup. The account fixture covers authenticated navigation to both reports and history with one main landmark. Production build and19 Node tests passed after integration.

The real account journey above has also been expanded to visit the actual report/history empty states. Its latest expanded run stopped at readiness during in-progress029 AI migration/head integration (41 backend index/history checks passed;2 browsers failed at readiness). Rerun after the migration chain is coherent; do not treat the earlier passing account journeys as proof of this expansion. These mocked UI fixtures and backend regressions do not replace the ten complete product stories, Arabic-reader review or native screen-reader certification.

```sh
CONTRACT_BASE_URL=http://127.0.0.1:8091 CONTRACT_VIEWPORT=390x844 \
  node scripts/browser_contracts.mjs /tests/account.html /tests/reports.html
CONTRACT_BASE_URL=http://127.0.0.1:8091 CONTRACT_VIEWPORT=390x844 \
  CONTRACT_KEYBOARD_SUBMIT='Refresh responses' \
  CONTRACT_KEYBOARD_RESULT='Keyboard refresh confirmed' \
  node scripts/browser_contracts.mjs /tests/history.html
```

## Current diary recovery increment

`LongitudinalRunner.jsx` offers explicit recovery of an existing active occurrence after reauthentication. A new memory-only capability and the observed `session_revision` are posted once; unknown outcomes retain the identical request, while conflicts require a **successful** schedule refresh before another rotation. Saved answers and server-pinned locale are preserved; the temporary language selector has been removed. Recovery ends the occurrence's access from other pages. Private state is cleared on permission denial and stale responses cannot repopulate an unmounted scope.

The revised `/tests/longitudinal.html` passed in installed Chrome at desktop and 390×844: actual start/recovery UI commands against synthetic HTTP, lost-ack replay, conflict plus failed/successful refresh, Arabic `lang`/RTL, one main landmark, no overflow, denial and late-response fencing. PostgreSQL recovery/concurrency/migration checks are separate backend tests. This is not a real browser/API/database journey or a native Arabic/screen-reader sign-off. The old recovery gap described below is historical and now superseded; diary v1 still repeats the full initial survey.

## Historical P12 participant schedule

The historical **Open participant schedule** form (now replaced by authenticated navigation) accepts workspace ID, published version ID, participant Bearer token, and pinned session language. `LongitudinalRunner.jsx` uses the actual `/api/v1/participant/longitudinal` contracts for slot listing, booking with stable random request key, revision-bound reschedule/cancel, occurrence listing and diary start. Native select/forms provide keyboard access; cancellation requires an explicit confirmation control. Published IANA zone times and server attendance observations are displayed without inferring attendance. Authorized join links use HTTPS and suppress referrer transmission.

Diary start creates a cryptographically random 256-bit capability held only in memory, sends it in the POST body, and mounts the existing `CollectionRunner` with the returned child `session_id`. Each child therefore uses its own collection session and unchanged answer occurrence `0`. Returning to the schedule preserves capabilities; full reload/closing intentionally does not. **Recovery gap:** backend existing-child start requires its original capability; this UI cannot recover a lost credential. It explicitly warns before starting and disables inaccessible existing sessions. Current backend diary v1 requires initial participation submitted and repeats the whole M1 survey, not a subset of prompt blocks. No staff scheduling dashboard, recording upload, consent issuance or transcription UI is added.

Executed after P12 addition: production build passes, all 5 geometry/Unicode Node tests pass. Installed Chrome headless `/tests/longitudinal.html` captured **PASS: booking/reschedule/cancel forms; diary start; IANA display; unknown attendance. No submissions.** The browser again needed termination at 20 seconds after DOM capture. Fixture requests prohibit all mutations. No authenticated live booking/diary browser end-to-end, real keyboard/screen-reader audit, network-loss recovery or WCAG certification is claimed. The prior P13 smoke remains renderer-only evidence.

## Historical P13 human assignment workbench

The former diagnostic **Open assigned human review** form has been replaced by the authenticated workspace assignment list. No manual bearer-token entry is now required. The reusable runner's token-prop fallback remains compatible for existing callers; the account page injects an authorized response transport. Existing preview and collection fragment routes remain unchanged. Independent reviewers only request their assignment projection (never the raw dataset/report); adjudicators can inspect server-authorized original reviews.

`EvaluationRunner.jsx` renders pairwise choices including tie/both-bad/cannot-judge, all required rubric dimensions, language review, classification, Unicode code-point spans, private-blob image polygons and bounded manually entered fictional sandbox transcripts. Span selection uses native textarea selection, including Shift+arrows, converting UTF-16 positions without normalizing the original. Polygon vertices can be entered entirely through labeled numeric controls; pointer coordinates reuse `firstClickGeometry`. Server validation remains authoritative for overlap, count and polygon validity. Unsupported tasks fail closed, never manufacture outcomes. Manual sandbox transcripts are explicitly unverified; no connector/network destination or automatic bot execution is offered.

Unacknowledged outcome bodies are frozen and retried identically. HTTP 422 releases the draft for correction; ambiguous failures retain it and offer reload to reconcile already-saved outcomes. Reloading an unsaved assignment does not clear the frozen draft. Credentials and payloads are never logged by this UI.

Executed: `node --test researchHelpers.test.js firstClickGeometry.test.js` (5 passing); `npm run build` (React 19/Vite 8, no added dependencies). Installed Chrome headless on `/tests/research.html` reported **PASS: five real forms; Unicode selection; cannot-judge rubric exclusion; private blob image. No submissions sent.** Chrome required timeout termination after 20 seconds despite successful DOM capture, not a clean process exit. These fixtures are synthetic local renderer tests, not human study evidence and never call an outcome endpoint.

Validation gaps: authenticated backend/browser end-to-end including transport loss and authorization expiry, real pointer/keyboard walks on devices, polygon visual overlays, screen-reader traversal, automated accessibility audit, sandbox interaction smoke, and WCAG conformance are not established by these tests. UI uses native labeled controls, fieldsets, live status/error regions and existing visible-focus styles; this is not an accessibility certification.

- `cd frontend && node --test firstClickGeometry.test.js`: 3 passing tests (contain/letterbox offsets, viewport coordinates and edges, portrait resize, zero/invalid dimensions, keyboard clamping).
- `cd frontend && npm run build`: React 19 / Vite 8 production build succeeds using existing dependencies.
- Serve Vite, open `/tests/renderers.html`: synthetic fixtures mount all seven advanced renderers; smoke checks ranking button interactions, issue editor insertion and private-blob image loading. No backend/private participant data is used.
- Executed installed Google Chrome headless against local Vite port 8187 with `--virtual-time-budget=5000 --dump-dom`: resulting DOM reported `PASS: seven renderers mounted; ranking interaction; issue editor; private-asset loading`. Chrome required timeout termination after 18 seconds; successful DOM assertions are not a successful clean browser-process exit.

Not yet verified: live authenticated collection end-to-end, actual pointer and keyboard event capture in browser, visibility/orientation behavior on devices, network-loss/reload recovery, screen-reader traversal, WCAG conformance, and optional consent receipt flows. The geometry unit tests are not substitutes for these checks.

## Existing participant session entry

Open `/#session=SESSION_UUID&session_token=CAPABILITY&locale=en` (or the session's pinned locale). Fragment credentials are removed from the address bar and retained only in memory. Refresh requires reopening the authorized link. The runner resumes already-consented sessions; it does not recruit, start sessions or grant consent. It supports advanced methods plus core surveys, preference and prototype tasks. Five-second collection now uses the V2 preparation/start protocol described above. Preview remains separate, test-only.

The runner serializes events, retains identical unacknowledged event payloads/IDs, and prevents answer submission while an event is unacknowledged. First-click selection freezes synchronously before transport, rejects letterbox clicks, preserves pointer/keyboard mode, and uses the server-projected first-click latch after resume. No AOIs or target paths are read or rendered. Accessibility context appears only with the server's explicit consent projection; granting that optional consent is currently outside the runner. Evidence upload is unsupported.
