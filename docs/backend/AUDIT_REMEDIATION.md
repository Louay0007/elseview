# Backend audit remediation — September 24, 2026

This records corrections to the nine reported defects and the separately listed
privacy lifecycle gaps. It supersedes earlier P17 completeness claims. Existing
applied migrations through 017 were not rewritten.

Final validation: **854 backend tests passed**, zero skipped, **92% statement
coverage**; the default-excluded load test passed separately. Lint, formatting,
compilation, dependency consistency, OpenAPI drift and migration checks passed.
Local application database backed up and upgraded to **022_account_erasure**;
all four containers healthy with AI mocked and integrations disabled.

## Defect-to-fix map

| Finding | Implementation | Regression evidence |
| --- | --- | --- |
| Scoped withdrawals/retention absent from backups | Durable identifier-only restore events; strict signed manifest v3; session/optional-consent/asset/AI/snapshot/export and producer-local replay | `test_privacy_audit.py`, physical clone scenarios in `test_privacy_ops_restore_db.py` |
| Released snapshot holds suppress purge | Exact equality of current/restored active subject holds **and** unlinked-contact holds before destructive replay | Newer and stale hold clone tests; no readiness on mismatch |
| Held invalidated AI never expires | Select retained payload/evidence rather than visibility state; distinguish SQL NULL and JSON null | Held-run retention test in `test_privacy_ops_db.py` |
| Held assets starve batches | SQL expiry and owner/recording-hold exclusion before ordered bounded limit; durable deletion event before file I/O | More than 100 held rows ahead of eligible asset |
| Revocation after AI prepare still sends | Two-stage preparation; final authorized transaction transfers an in-process workspace gate through actual HTTP/1.1 request-body completion | Real transaction cancel/restriction races, gate blocks mutation commit, Unix-socket HTTP transport sends body before withheld response |
| Never-dispatched AI cannot retry | Explicit `never_dispatched` zero-cost release and immediate bounded replacement; dispatched uncertainty remains non-repeatable | Cancel/replacement budget test plus sent/unsent classification |
| Privileged actors counted as blind reviewers | Exclude creators/owners/admins/current raw grants and recorded raw disclosures; recheck at assignment/read/submit/report; historical unchecked assignments fail closed | `test_research_audit.py` privilege, disclosure, legacy assignment tests |
| Participant double-books across workspaces | Participant-scoped PostgreSQL advisory transaction lock before workspace capacity locks, also on rescheduling | Independent concurrent transactions across two workspaces |
| Released included allowance is lost | Separate immutable `included_allocation` provenance; service and SQL guard count live included allocations independently of quota usage | Included A/paid B/release A/included C; zero price, tight budget, race and forged SQL |

## Additional lifecycle coverage

- Contact-specific holds and erasure use explicit workspace/contact UUIDs, not
  guessed global email identity. Contact payload and lookup hash are minimized;
  linked candidate/screener/session data is removed or minimized and unused holds
  released. Minimal consent/financial identifiers are retained.
- Bounded reviewed-policy lifecycle sweeps cover contact expiry, evaluation
  datasets, recording/transcript bytes, closed/archived study/template content,
  recruitment snapshots, raw comments, audit detail JSON and idempotency bodies.
  Active studies are not silently deleted by an age sweep. Identifiers supporting
  duplicate prevention and financial records are not blindly removed.
- A study with financial reservations is **minimized**, not deleted: raw version,
  template, recruiting filter and title content is cleared, launches closed and
  grants removed, while reservation IDs/millimes and original hashes remain.
  SQL trigger exceptions permit only the designated empty-field transitions
  backed by a scoped privacy decision, not arbitrary edits to published content.
- Self-service account erasure requires current password and explicit confirmation.
  Last-owner and unsettled-reward/legal-hold conflicts return actionable errors.
  It creates scoped privacy requests, disables login, scrubs account/profile data
  and revokes credentials. Global completion waits for every scoped request.
  A client-generated 256-bit status capability permits recovery after a lost
  response; only its hash is stored. Workspace administrators cannot erase another
  user's global account. Global erasures are also included in restore manifests.

## New API surfaces

Prefix `/api/v1/workspaces/{workspace_id}/privacy-ops`:

- POST `/contact-holds`: `{contact_id, reason_code, review_deadline}`; privacy admin.
- POST `/contact-holds/{hold_id}/release`: explicitly release a reviewed hold.
- POST `/contacts/{contact_id}/erase`: scoped recruitment erasure.
- Existing POST `/retention/sweep` now includes lifecycle producer counts.

Global self-service:

- POST `/api/v1/account/erasure`: bearer authentication and body
  `{request_key, current_password, confirmation: "ERASE MY ACCOUNT", status_capability}`.
  Generate and retain `status_capability` as random 32-byte lowercase hex **before**
  sending. Never put it in URLs, logs or committed examples.
- POST `/api/v1/account/erasure/status`: `{request_key, status_capability}`; returns
  pending/completed, never another account's data. Checking the receipt finalizes
  only after the underlying workspace erasures have completed.

## Migration and recovery implications

`017 → 018_billing_allowances → 019_privacy_events → 020_review_access →
021_privacy_lifecycle → 022_account_erasure`.

018 does not reprice existing charges. Positive-price historical zero-net rows
identify included allocations. Zero-price history lacks release timestamps, so
the migration assigns a deterministic capped live allocation without altering
financial amounts. 020 does not retrospectively attest old assignments as blind;
unchecked legacy independent outcomes are excluded until correctly reassigned.

Manifest v3 is mandatory for this release, including resource events, both hold
scope sets and account restrictions. V1/v2 manifests cannot certify readiness.
Old backups must be migrated in an isolated target before current replay. Use
current trusted manifest digest and operator signing key; HMAC is not encryption.
Downgrade does not silently discard newer replay decisions: an older action
constraint is installed NOT VALID for existing records, so old replay fails
closed on unsupported manifests rather than claiming erased data was restored.

## Guarantees and limitations

The physical AI send gate applies to the planned **single backend process** and
coordinated application mutations. It releases after writing the request body,
not after the provider responds; no sender DB transaction spans cloud I/O.
Bytes already buffered in the OS/network and provider processing cannot be
recalled. Direct SQL writers or multiple backend processes require a different
coordinated dispatcher; do not scale worker processes without redesigning this.

No live provider/payment/email/calendar integration was enabled by these fixes.
External encryption, retention law, vendor forgetting and full browser/accessibility
certification remain independent gates, not software claims made by this patch.