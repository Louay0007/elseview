# P06/P07 development API

This document describes the backend implementation, not a public-production release.
All routes are prefixed `/api/v1`. Researcher operations require the existing
verified-account bearer token and workspace/study permissions. Participant
accounts do **not** need membership in the researcher's workspace.

## Recruitment

- `GET /panel/consent` returns the exact panel opt-in document and digest.
- `PUT /panel/profile` records digest-bound opt-in/withdrawal and typed profile
  attributes; `GET /panel/profile` returns only the caller's profile.
- Language assessment routes expose versioned questions, never qualifying answer
  keys. Assessment results are server-calculated, expiring basic development
  qualifications, not a certification of professional expertise.
- `POST /workspaces/{workspace_id}/recruiting/contacts/import` accepts bounded
  JSON rows, explicit column mapping, source/consent provenance, retention,
  duplicate policy and a preview flag. Preview does not write contacts. Suppressed
  contacts are not silently reactivated by reimport.
- Private addresses are normalized into **workspace-keyed HMAC lookups**, not
  retained as plaintext or recoverable email. Invitation delivery is manual in
  development; this API is not an email-campaign delivery service.
- Eligibility estimates expose aggregate counts and a non-guarantee, not the
  private panel directory. Public opt-in and client-private consent stay separate.
- `POST /workspaces/{workspace_id}/recruiting/launches/{launch_id}/recruit-public`
  selects matching opted-in candidates server-side using bounded `count`, `filters`
  and invitation expiry. It returns issued invitation/candidate capabilities, not
  public profile IDs or a browsable directory. Existing participants are skipped.
- Launch recruitment configuration pins filters, screeners, quota cells, capacity,
  integer-millime reward commitments and budget before invitations are issued.
  Screening is explicitly uncompensated and disclosed. These are development
  commitments, not real payment obligations or transfers; P08 owns settlement.
- Invitation capabilities expire and are stored only as hashes. Private invitation
  redemption requires a verified account whose normalized email matches the
  workspace-private lookup. Public invitations bind their intended account.
- `X-Invitation-Token` authorizes invitation presentation, screening and reserve
  operations. Screening/reservation also require verified account authentication.
  A new invitation cannot create a second participant slot for the same launch.
- Reservations serialize workspace, launch and quota-cell checks; overlapping
  cells all count the hold. Expired holds do not consume capacity. Submission
  consumes the same hold transactionally. No cookie/device uniqueness claim is made.

## Collection

1. Obtain the invitation presentation and exact study consent document.
2. Complete the server-validated screener and reserve capacity.
3. Generate a cryptographically random URL-safe capability (at least 32 random
   bytes encoded without padding). Keep it private and reuse it for start retries.
4. `POST /collection/sessions` with the verified-account bearer token and:

   ```json
   {
     "invitation_token": "the-issued-invitation-capability",
     "capability": "the-client-generated-random-session-capability",
     "locale": "fr",
     "document_id": "the-presented-consent-document-uuid",
     "presented_digest": "the-presented-document-sha256",
     "consent": "granted"
   }
   ```

   The identifier strings above describe runtime values, not seed records.

5. Use `X-Session-Token` on subsequent session operations. The token is scoped to
   one session; it does not grant workspace access or access to other participants.
6. `GET /collection/sessions/{session_id}` resumes saved state and returns the
   server-selected next block. Do not generate a new assignment on refresh.
7. Save using the canonical command:

   ```json
   {
     "schema_version": 1,
     "expected_revision": 0,
     "status": "responded",
     "value": {"option_id": "yes"},
     "client_event_id": "a-new-command-uuid"
   }
   ```

   Send to `PUT /collection/sessions/{session_id}/answers/{block_key}`.
   Reuse the **same complete command** after an uncertain network failure.
   An identical command returns its original saved receipt; a changed command with
   the same event ID conflicts. A revision conflict requires resume/reconciliation,
   not a blind overwrite. A local edit is not saved until a successful receipt.
   `unable` and `skipped` use null values; inability requires a supported reason,
   and required blocks cannot be skipped.
8. Event batches go to `POST /collection/sessions/{session_id}/events` with the
   pinned `version_id` and `events` containing `block_key` and typed `event` data.
   Client sequences begin at zero and must remain contiguous; resend the original
   batch after disconnection. Client-observed events remain distinct from
   server-created lifecycle facts.
9. Start one-shot exposure through
   `POST /collection/sessions/{session_id}/attempts/{block_key}`. Refresh cannot
   obtain a clean second attempt. Private asset content uses the session-scoped
   asset route; exposure access is time/attempt bounded. Browser-reported visibility
   is not proof of human attention and cannot prevent a participant retaining bytes.
10. Submit through `POST /collection/sessions/{session_id}/submit` with
    `version_id` and the latest session `expected_revision`. Finalization verifies
    the reachable path, freezes final answer pointers, consumes the reservation and
    queues exactly one `collection.quality` job in the same transaction. Quality
    output is deterministic evidence pending human review, not reward acceptance.

## Privacy and storage

Session-capability withdrawal affects only that session and denies further collection
immediately. Authenticated participants can
use the existing workspace-scoped privacy request endpoints for their own linked
participation without gaining workspace membership. Access exports include scoped
recruitment/session data; erasure removes response revisions, events and owned
derivatives while retaining minimal withdrawal/capacity accounting where required.
Owner-study erasure removes dependent collection/recruitment rows before studies.
Use `limit`/`offset` for session pages and `detail_offset` for response/event detail
pages; each session's detail page is bounded to 1,000 records per collection.

Published versions, candidate snapshots, consent receipts, answer revisions,
assignments and final response pointers have database constraints/guards in addition
to API checks. Never perform raw-table mutations as an application integration.

## Operational boundaries

- Exactly the existing four Compose services; no worker or broker is added.
- Apply Alembic explicitly. App startup does not mutate schema.
- Invitations are required for this implementation; anonymous/open-link recruitment
  is not enabled.
- No new participant frontend, real email delivery, professional qualification
  certification, P08 review/payment workflow or production browser timing guarantee
  is implied by these backend endpoints.
- Executed test results and remaining limitations belong in
  `/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md`.