# P18/P19 — Development release evidence and boundaries

September 24, 2026. No new schema migration: head remains `017_privacy_ops`.

## Contracts

`/Users/user/Workspace/startup-act/backend/contracts/openapi.json` is generated from
the installed application. It covers 167 paths, actual request schemas, bearer,
session-capability, scoped-key and refresh-cookie authentication, and the canonical
`{error: {code, message}, request_id}` response. Drift, operation-ID uniqueness,
canonical answer shape and real error responses are tested. Success responses
without Pydantic response models remain explicitly unconstrained; this artifact
does not pretend to provide exhaustive typed success projections. Documentation
endpoints remain disabled publicly.

```sh
/Users/user/Workspace/startup-act/scripts/dev exec -T backend \
  python -m app.contracts --output /app/backend/contracts/openapi.json --check
```

`/Users/user/Workspace/startup-act/frontend/contracts.d.ts` documents the reviewed
request/error subset. No TypeScript compiler was added; server validation remains
authoritative. The React workbench uses the actual collection component and thin
transport, not reimplemented consent, review, payment or metrics logic. Its fixture
checks registration validation/correction, identical study retry, review, report
reload, AI status failure/retry, canonical autosave replay, submission and remount.
Seventeen mocked requests are explicitly **not** a real browser-to-DB journey.

## Browser and proxy

The existing local Chrome is driven with Node's built-in WebSocket and CDP; no
browser driver dependency, download or fifth service. Requests from fixture pages
are restricted to the local fixture origin. The runner waits for explicit PASS
and terminates its own ephemeral Chrome profile. This replaces the older
`--dump-dom` approach which did not reliably exit on this host.

```sh
node /Users/user/Workspace/startup-act/scripts/browser_contracts.mjs \
  /tests/renderers.html /tests/research.html /tests/longitudinal.html \
  /tests/contracts.html
cd /Users/user/Workspace/startup-act/frontend && npm test && npm run build
```

All four fixtures passed. Node tests cover transport, canonical errors, coordinate
geometry, Unicode selection and the corrected proxy boundary. Vite now proxies
`/api/`, not `/api`, so `/apiClient.js` is no longer incorrectly sent to FastAPI.
Only frontend publishes a loopback port. Actual proxy readiness and module delivery
were checked. Backend tests cover exact CORS origins, CSRF/cookie binding,
revoked login, request size caps and safe errors. Native inputs and error/status
regions do not establish screen-reader or WCAG certification.

## Measured load and restart evidence

Details and aggregate artifact interpretation are in
`/Users/user/Workspace/startup-act/docs/backend/P18_RELIABILITY.md`.
Four sessions × twelve autosaves = 48 accepted revisions; all four submissions
and identical retries persisted while a real durable AI job waited in a blocked
mock adapter. p50 **63.24 ms**, p95 **123.02 ms**, measured window **1.048 s**.
This is a bounded TestClient/ASGI same-event-loop benchmark, not network throughput
or a production capacity promise. It excludes production throttling and sustained
soak behavior. Container-visible hardware: Linux aarch64, eight logical CPUs,
8,319,770,624 physical memory bytes. Exact payloads, queue-created age, pool samples,
RSS and duration are recorded in the aggregate JSON.

A local database archive was saved before actual database/cache/backend container
restarts. Readiness recovered and durable row counts remained exactly unchanged:
users 2, sessions 0, jobs 1, rewards 0, ledger entries 0. This small development
restart smoke is not evidence of in-flight production failover. Populated durable
jobs, response/reward uniqueness and nonzero journal restoration are tested in
the separate guarded database suite. Low disk is tested by injected free-space
exhaustion and actual private-storage recovery, not by filling the host disk.

## P19 story coverage

`/Users/user/Workspace/startup-act/docs/backend/P19_ACCEPTANCE.md` maps all ten
stories to named executable tests and records their limitations. New coherent
workflows cover accepted answer → independent review → earned reward → metrics →
approved report → mock AI; lost-answer/submission replay; and consent withdrawal
between inference preparation and result persistence. The physical restore test
now includes a real two-entry nonzero journal and compares it exactly before and
after replay. The restore readiness gate refuses incomplete/unbalanced journals.

## Security and dependency review

No dependencies added. Python installation uses the hash-locked requirements file;
`pip check`, frontend lockfile installation/build and lint/compile checks are part
of validation. No provider secrets appear in the generated public contracts or
frontend fixtures; all fixture identities/payloads are synthetic. Existing tests
cover private projections, tenant/source revocation, CSV formula escaping, parser
limits, descriptor-relative storage, immutable accounting and webhook SSRF/DNS
pinning. React renders server text as text, not raw HTML. This review is not a
current external vulnerability-advisory scan or independent penetration test.

## Remaining release gates — not marked complete

- A single fully authenticated browser journey covering all ten stories, including
  real keyboard-only walks and screen-reader review, is not yet demonstrated.
- Story 1's live cloud-assisted bilingual preference report is not approved here:
  mock assistance is tested, but vendor compatibility/dialect evidence remains an
  explicit external gate. No paid requests were made.
- Some API success projections remain untyped; the reviewed OpenAPI documents
  this rather than fabricating response guarantees.
- Production archive encryption/offsite restoration, backup-key custody, actual
  vendor deletion, SMTP/design/calendar synchronization, legal/tax rules and
  hardware-specific sustained load need operator/vendor review.
- The new contract workbench is a diagnostic fixture surface, not a replacement
  for a complete researcher/participant product dashboard.

P18 has executable development evidence; P19 has substantial automated acceptance
coverage but is **not an unconditional full-product production sign-off**.