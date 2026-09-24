# P16/P17 — Collaboration and privacy operations

Development implementation, September 24, 2026. This is not an assertion of legal,
provider-deletion, encrypted-backup or production integration certification.

## P16

The complete collaboration route, scope, HMAC, retry and local ICS contract is in
`/Users/user/Workspace/startup-act/docs/backend/P16_COLLABORATION_WORKLOG.md`.
API keys are one-time-disclosed, hash-stored, expiring credentials for the two
dedicated read APIs only; they never substitute for normal authentication on other
routes. Report reads still need an explicit grant and current issuer authority.
Customized template inputs and comments are never included in shared views.

Set `COLLABORATION_INTEGRATION_MODE=disabled` (default) to prevent outbound calls.
Mock mode exercises the HTTP adapter without external traffic. Explicit live mode
requires `COLLABORATION_WEBHOOK_DESTINATIONS` (an exact HTTPS URL JSON list), an
operator-provisioned `COLLABORATION_WEBHOOK_SECRET` of at least 32 characters, and
`COLLABORATION_WEBHOOK_TIMEOUT_SECONDS` less than the worker timeout. Compose
forwards these settings; upgrades do not create or enable integrations.

The first delivery event is deliberately a metadata-only `collaboration.test`.
No arbitrary research payload or automatic event subscription is implied. Stable
delivery IDs require durable receiver-side deduplication. A revoked integration,
membership or privacy epoch prevents queued execution/publication, but an external
request already sent cannot be recalled. Local calendar exports include booking
revision and cancellation state; no external calendar account is synchronized.
Design links work without fetching; Figma, SMTP and calendar vendor connectors are
not enabled. Existing in-app notification records honor participant preferences.

## P17 authenticated endpoints

Prefix: `/api/v1/workspaces/{workspace_id}/privacy-ops`. Requires `privacy.manage`.
All dates below are timezone-aware. Unknown JSON properties are rejected.

| Method / suffix | Contract |
| --- | --- |
| POST `/holds` | `subject_id`, nonblank `reason` (1–2000 characters), future `review_deadline`; 201 |
| GET `/holds` | At most 100 records, including released/overdue review state |
| POST `/holds/{hold_id}/release` | Explicit, audited, idempotent release |
| POST `/retention` | `purpose` raw/media/derived/export, positive `version`, `days` 1–3650, reason, future review deadline |
| POST `/retention/sweep` | Bounded source-local raw/derived/export expiry; returns per-category counts |

An expired review deadline does not silently release a hold. Retention policy
versions are immutable through the API. Financial beneficiary minimization uses
the dedicated P08 settlement-retention policy, not the generic research policy.
Neither financial obligations nor their minimal journals justify retaining raw
answers. A hold preserves relevant source data but does not restore participant,
report, share, asset, API-key or AI access after restriction.

The existing `/privacy-requests` endpoints remain the participant entry point.
Restriction/tombstone/epoch changes commit before asynchronous deletion. File I/O
failure leaves erasure retryable, and missing files are idempotent success. Because
comments, shared snapshots and owner-study cascades cannot safely be separated by
subject, an active workspace hold conservatively defers destructive erasure.
After authorized release, use the existing request retry endpoint; a completed
worker attempt is not proof that the request finished while held.

The producer audit and ordered callback ownership are documented in
`/Users/user/Workspace/startup-act/backend/app/privacy_ops/AUDIT.md`. A workspace
request cannot erase another tenant's global login or public-panel identity.
Suppression hashes, financial minimum records and UUID audit attribution have
explicit purposes; raw JSON audit details and raw comments are conservatively
scrubbed. PostgreSQL AI results are invalidated transactionally. The generic Redis
aggregate helper currently has no production consumers; adding one requires
registered invalidation, not merely assuming a TTL satisfies deletion.

## Backup and restore runbook

1. Quiesce application writes and the worker for a consistent database/files
   backup. Snapshot helpers do not pause writers. Use encrypted, access-controlled
   operator storage; neither the archive nor HMAC provides encryption.
2. `app.privacy_ops.backup.snapshot(source_url, source_files, destination)` uses
   external `pg_dump`, writes owner-only files, and returns a trusted SHA-256 digest
   binding the database archive **and the full private-file inventory**. PostgreSQL
   client binaries are operator prerequisites, not extra application services.
3. Provision an empty, isolated database ending `_restore`, with PUBLIC access
   revoked, and a disjoint private-files directory also ending `_restore`.
   `restore_snapshot(...)` validates the trusted digest and rejects nonempty target
   data or symlinks. It uses `pg_restore`; it never produces a ready marker.
4. Export CURRENT source `export_tombstones(session, path, signing_key)` after the
   snapshot. Version 2 contains only UUID/purpose tombstones and active-hold UUID
   scopes, not answers, reviewer reasons or contact details. Transfer its current
   digest through a separate trusted channel. A signature alone cannot establish
   freshness. The operator key must contain at least 32 bytes.
5. Run the offline replay CLI, keeping passwords out of command arguments:

   ```sh
   python -m app.privacy_ops.restore \
     --source-url-env DATABASE_URL --restore-url-env RESTORE_DATABASE_URL \
     --source-files /operator/source-private \
     --restore-files /operator/private_restore \
     --manifest /operator/current-manifest.json \
     --key-file /operator/signing.key --latest-digest "$CURRENT_DIGEST"
   ```

6. If a current legal hold is missing from the old database, replay fails before
   destructive actions. An authorized operator must reconcile the actual reviewed
   hold first; the tool does not invent reviewer attribution or automatically
   release stale holds. Version-1 manifests cannot authorize replay.
7. Replay increments privacy epochs, blocks source access, revokes collaboration
   access, purges permitted data, commits a nonce/digest receipt and then writes
   `.privacy-ready`. Failed revalidation removes an earlier marker. Both the API
   and job runner refuse restored work until the receipt matches the files marker.
   Keep the source quiescent until final freshness verification and cutover.

The routine PostgreSQL regression test creates a unique physical TEMPLATE clone
of the guarded `_test` database, copies its actual private files and replays a
post-snapshot erasure. This tests restoration semantics, not pg_dump format. The
test-only role has CREATEDB solely for disposable clones; app/app_owner do not.
No test migration/reset fixture targets a restored database. A production backup
drill still requires the operator's actual encryption, access and archive tools.

## External deletion boundary

No provider-side erase API is configured. Local invalidation cannot unsend a cloud
request or prove that a provider deleted completed requests, logs or backups.
Before enabling a provider, record retention/training/deletion capabilities,
applicable agreement and deletion-request outcome independently. Unknown deletion
outcomes must remain unknown. No live provider or webhook endpoint was contacted
by the development tests.