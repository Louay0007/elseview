# Source-linked recruitment and longitudinal email

This bounded C02 increment adds internal delivery on the existing embedded worker. It does not enable live mail, add a service, or represent completion of the overall backend plan. Migration `028_notification_delivery` follows `027_diary_recovery`.

## Public contracts

All paths are under `/api/v1`; existing bearer authentication and resource-level authorization remain mandatory.

- `POST /workspaces/{workspace_id}/recruiting/launches/{launch_id}/invitations` accepts the existing source and expiry fields plus optional `delivery: "manual" | "email"` (default `manual`). Manual responses retain the existing code and `delivery: "manual"`. Email responses return the existing invitation/candidate IDs and expiry, `invitation_token: null`, and `delivery: "queued"`. Queue acceptance is not delivery confirmation. Duplicate candidate creation remains a conflict.
- `POST /workspaces/{workspace_id}/recruiting/invitations/{invitation_id}/delivery` explicitly requests email or resends an existing invitation. It returns HTTP 202 and `{ "status": "queued" }`, with no raw code or delivery-row ID. Only the original issuer, still authorized to manage the launch, can request it. Pending/in-flight requests deduplicate; terminal requests have a 60-second creation-time cooldown. A restore-quarantined invitation may be explicitly requeued immediately. Resending uses the same valid capability without rotating or invalidating the original code.
- GET/PUT `/workspaces/{workspace_id}/collaboration/notification-preferences` include `email_reminders: boolean`. It defaults to false, including migrated rows. PUT still requires `reminders`; omitting `email_reminders` preserves the stored choice. Email requires **both** booleans true; in-app preferences retain their prior default. A participant need not be workspace staff, but must satisfy existing notification-subject authorization. Disabling either setting cancels pending reminder email. Re-enabling does not revive cancelled work.

Regenerate OpenAPI and any generated request types for these routes. No new generic Jobs enqueue permission or public delivery-status endpoint is introduced.

## Eligible sources and schedule

Recruitment email supports active, verified public-panel recipients with current panel consent, a valid invitation, current source/qualification authority, and an active verified original issuer with current launch permissions. New HTTP-issued invitations use a purpose-separated HMAC of the existing random invitation UUID; only its verifier hash is stored on the invitation. Historical random/manual capabilities remain usable but cannot be reconstructed for email. Private contacts currently retain only scoped address lookup hashes, not recoverable email addresses: they remain **manual delivery only**. A rejected email request rolls back candidate/invitation creation.

Email reminders are scheduled only for new booking revisions and new diary schedules created after explicit opt-in. Enabling email does not backfill historical sources. Interview email is due at slot start minus 24 hours (or immediately for nearer bookings), expires at slot start, and requires current booking revision/state, participant study consent, host authority, and verified active accounts. In-app notification completion neither blocks nor confirms email. Opting out must not prevent booking.

Diary email is due at the occurrence opening, expires at its due time (not grace), and requires completed initial participation, current study consent, current issuer authority, and an occurrence not already submitted/withdrawn/erased. No research answers, meeting URLs, study titles, source identifiers, or capabilities occur in reminder content. The fixed message asks the recipient to sign in and explains how to disable email reminders. Cancellation, revision changes, expired windows, or lost authority suppress stale work; there is no automatic reminder replay/backfill.

## Dispatch and failure boundary

`notification_deliveries` stores only scoped source FKs, recipient/issuer account IDs, privacy epoch, bounded outcome/state, attempts, and timing/lease metadata. It contains no email address, capability, arbitrary payload, or research data. Source composite FKs prevent cross-workspace references and cascade on source deletion. Generic job JSON contains no mail content. Existing `longitudinal.reminder` jobs continue to serve in-app effects.

The embedded worker alternates generic and mail work, and alternates auth and optional-notification mail with empty-queue fallback. A single retained physical-task fence covers both mail queues and synchronous privacy jobs. Timeout/stop quarantines the worker without cancelling or forgetting a running SMTP thread; restart cannot overlap it. Shutdown observes physical completion before closing database resources.

Claims serialize workspace → recipient → delivery; recovery commits separately before owner locks. Source, consent, opt-in, accounts, issuer permissions, privacy epoch, expiry, and capability verifier are rechecked immediately before committing `dispatching`. The process-local workspace dispatch gate spans physical send, while **no SQL transaction spans SMTP**. It is released before completion SQL to avoid privacy/completion lock inversion.

**Committed `dispatching` is the irrevocable external-send boundary.** Later opt-out, panel withdrawal, cancellation, or erasure cannot recall an in-flight message. The gate orders participating workspace privacy mutations with sends in this single application process; it is not distributed coordination and does not protect direct SQL writers. Run only the existing supported single embedded worker topology.

`sent` means SMTP DATA acceptance (or private local capture), not inbox delivery. Only known pre-dispatch `DELIVERY_UNAVAILABLE` retries, at most three attempts with 30/60-second backoff while the source remains valid. Rejection is terminal. Unknown exceptions, ambiguous SMTP outcomes, expired dispatch leases, and crashes after send but before completion are quarantined as uncertain, never automatically replayed. Explicit authorized recruitment resend can still duplicate an ambiguously accepted message; its stable code is intentional. Reminders have no explicit resend API.

## Privacy, restore, and retention

Workspace restriction cancels pending deliveries when the subject is recipient **or issuer**, scoped to that workspace. Account restriction applies globally. Public-panel withdrawal cancels pending recruitment email; subsequent opt-in cannot revive it. Reminder preference disable and booking cancellation/revision changes cancel pending reminder rows. Delivery source deletion cascades; account erasure uses existing tombstone restrictions and does not require deleting the referential user identity.

Restore replay quarantines **all** restored pending/dispatching optional mail before writing readiness, including snapshots taken before a later live send was accepted. Historical reminders stay quarantined. Only a fresh authorized invitation delivery request may enqueue again. Restored private spool files are removed by the existing auth-mail restore cleanup. No new manifest fields are needed.

Expired pending sources are cancelled, abandoned dispatches become uncertain, and terminal metadata older than source expiry plus seven days is pruned in bounded batches (100 each worker recovery turn). `collaboration.mail.aggregates(session)` offers internal PII-free state/outcome/count/oldest-age data; it is not exposed through an unauthenticated diagnostic route or ineffective message-only logs.

The development spool is separate from SQL retention: existing 0700 directory/0600 captures, 24-hour TTL, bounded file count, and startup/shutdown/send cleanup apply. Immediate invitation spool dispatch is allowed only in development/test local mode when the worker is disabled. Scheduled reminders require the embedded worker even in local mode. Production SMTP remains approval-gated, verified TLS only, and requires the enabled worker. Provider/domain approval, production credentials, live deliverability, and operational monitoring remain external gates; this implementation performs no live sends.

## Implementation and validation inventory

Changed implementation files for this increment:

- `app/auth/{delivery,outbox}.py`
- `app/collaboration/{mail,models,router}.py`
- `app/recruiting/{models,router,schemas,service}.py`
- `app/longitudinal/{models,service}.py`
- `app/jobs/runner.py`
- `app/privacy_ops/{account,service,restore}.py`
- `migrations/versions/028_notification_delivery.py`

Added `tests/test_notification_{delivery,reminders,runner,restore}.py`; extended `tests/test_auth_mail_runner.py` and `tests/test_mail_delivery.py`. Existing SMTP settings and main shutdown hooks already provide the required configuration and physical-task drain, so neither needs another change for this increment.

Validation from the repository root: **262 passed, 1 deselected** in a fresh isolated PostgreSQL instance, with external network blocked by the test fixture. The parent-owned full migration graph test was then run separately: **1 passed**. It discovers descendants dynamically, so no migration-list edit is required. The new migration's real downgrade/upgrade test is included in the 262-test run. Real snapshot replay, concurrent claim/enqueue, account/scoped erasure, physical-send privacy fencing, SMTP timeout/stop non-overlap, bounded retry, private-contact refusal, stable resend, consent/authority changes, explicit reminder opt-in, booking reschedule, and diary completion/expiry are covered. Scoped Ruff check/format and `git diff --check` also passed.

```sh
mkdir -p .test-runtime
TMPDIR="$PWD/.test-runtime" backend/.venv/bin/python scripts/test_fresh.py -q \
  tests/test_notification_delivery.py tests/test_notification_reminders.py \
  tests/test_notification_runner.py tests/test_notification_restore.py \
  tests/test_auth_outbox.py tests/test_auth_mail_runner.py tests/test_auth_mail_privacy.py \
  tests/test_mail_delivery.py tests/test_recruiting.py tests/test_longitudinal.py \
  tests/test_longitudinal_db.py tests/test_longitudinal_rewards_db.py \
  tests/test_collaboration.py tests/test_collaboration_db.py tests/test_account_erasure.py \
  tests/test_privacy_ops_db.py tests/test_privacy_ops_restore_db.py \
  tests/test_restore_guards.py tests/test_jobs.py \
  -k 'not test_jobs_migration_downgrade_upgrade' \
  -m 'not cache and not live_llm and not load' --tb=short
TMPDIR="$PWD/.test-runtime" backend/.venv/bin/python scripts/test_fresh.py -q \
  tests/test_jobs.py::test_jobs_migration_downgrade_upgrade \
  -m 'not cache and not live_llm and not load' --tb=short
rmdir .test-runtime
```

The application schema revision in `app/db.py` is now `028_notification_delivery`; `tests/test_db.py` rejects `027_diary_recovery` as stale. Fresh isolated validation of the entire database test module passed (14 tests), including current-head readiness and the complete migration down/up cycle. Integration owner must regenerate OpenAPI/request types for the routes above and run the overall suite. No frontend, shared completion-plan/status, or deployment files were changed by this increment.
