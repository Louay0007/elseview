# P17 producer inventory (workspace scope)

Registry is dependency ordered, errors propagate; request completion is after all handlers.

* Identity: global User/password/refresh tokens and public ParticipantProfile,
  PanelConsent, Qualification retained: a workspace request has no authority to
  destroy another workspace's account. Global panel withdrawal is separate.
* Recruitment: Candidate attributes/source references, PrivateContact attributes,
  screener results erased, invitations revoked, reservations released. Contact
  lookup hashes remain suppression metadata, not plaintext identity.
* Collection: AnswerRevision, ResponseEvent, InteractionAttempt, Answer removed;
  assignments/submitted snapshots/quality summary cleared. Session shells remain.
* Longitudinal: linked recording files resolved BEFORE Recording deletion,
  transcripts cascaded, bookings/notifications deleted. Schedule shells remain.
* Analytics: collection purge invalidates linked ReportVersions, Exports, shares,
  source snapshots. Owned study purge covers researcher-origin snapshots.
* AI: whole-workspace conservative invalidation clears instructions/output/evidence;
  hold only changes states, retaining raw material offline. Cost counters retained.
* Evaluation: assignment-dependent items/outcomes, export reviews, datasets sourced
  from owned assets and researcher-owned datasets deleted before study deletion.
* Reviews/billing: raw review source deleted; minimal journal/reward settlement and
  reviewed financial retention metadata retained, not fabricated legal deadlines.
* Studies/templates: owned study deletion cascades versions/blocks/template input
  snapshots. Immutable built-in recipes contain no participant input.
* Jobs/idempotency: idempotency responses cleared; job payload/result contract is
  UUIDs/status only and epoch fences pending work. No Job mutations under workspace
  lock, avoiding reverse lock-order deadlocks. Attempts hold codes/UUIDs only.
* Audit: all workspace details cleared (another actor can mention the subject);
  action/time/UUID attribution retained. No reason, answer or manifest body is
  copied into P17 audit events; reasons live only in restricted review records.
* Collaboration P16: keys/grants/preferences/integrations and deliveries purged;
  raw comments conservatively removed workspace-wide during physical purge.
* Cache: existing Redis Cache has NO production get_json/set_json consumers
  (source audit). AI cache is AIRun in PostgreSQL, invalidated transactionally.
  Epoch protects stale asynchronous results. No cloud object backend is configured;
  private storage deletion is idempotent on missing files and propagates IO failure.

## Executable ownership / callbacks

| Registry key | Owning callback | Physical coverage |
| --- | --- | --- |
| linked_assets | common.privacy._linked_assets | recording links resolved before cascade |
| longitudinal | longitudinal.service.purge_subject | recordings/transcripts, bookings/notifications |
| collection_analytics_ai_reviews | collection.privacy.purge_subject | revisions/events/answers; analytics and review callbacks |
| evaluation | evaluation.privacy.purge_subject | source-dependent evaluation data |
| financial | reviews.privacy.minimize_financial | settled beneficiary unlink under financial policy; journal retained |
| recruiting | recruiting.service.erase_subject | candidates, linked private contacts, screener results |
| assets_consent | common.privacy._assets_receipts | asset metadata lifecycle, links/intents, receipts |
| studies_templates | studies.service.purge_owned_studies | owned study/template graph |
| operational_collaboration | privacy_ops.producers.purge_subject | audit JSON, invite contact, idempotency, collaboration callback |

The separate common.privacy.erase_files phase owns filesystem deletion; registry
completion alone is not evidence that files were deleted. Tests resolve the actual
registry callbacks, not just a synthetic registry ordering example.

## Reviewed retention coverage and deliberate boundaries

POST privacy-ops/retention/sweep holds the workspace lock and selects at most100
old rows per producer, oldest first. Raw collection revisions/events/answers and
dependent review/analytics facts are erased locally, not by calling a subject-wide
handler that could destroy newer sessions. Derived AI output/evidence and analysis
snapshots with their report versions/exports/shares are removed. Export rows are
removed and expired sharing capabilities revoked. Epoch advances fence pending
publication. Existing storage sweep owns raw/media files. Latest overdue policy
does not revive an earlier version. Any active workspace hold defers shared-derived
and raw sweeps because attribution may overlap; missed review is never release.

Migration021 adds bounded lifecycle retention for recruitment/private contacts,
evaluation datasets, closed/archived study/template text, recording/transcript
content, raw comments and operational payloads. Study financial reservation shells
remain while raw content is minimized. Financial retention uses the settlement
policy/minimal immutable ledger, never the generic raw-policy deadline. Global
identity deletion is outside workspace authority; migration022 adds a separately
authenticated, password-confirmed self-service workflow with durable status receipt.

Private-contact lookup hashes remain linkable suppression metadata until explicit
contact erasure replaces them with a resource-only marker. Unlinked private contacts
have their own contact-ID-scoped holds/erasure, not inferred user identity. HMAC only authenticates
manifests/cache keys; it neither encrypts content nor makes identifiers anonymous.
Redis aggregate keys are hashed; there are no production aggregate consumers or
subject-indexed deletion API. The synthetic failed-cache callback test proves
registry retry propagation only, NOT production Redis deletion. An AST regression
test requires this audit to be revisited if aggregate consumers are introduced.

Holds do not expire automatically at a missed review deadline. Access/export is
restricted immediately; job may succeed metadata-only while request remains open.
Release then existing privacy retry endpoint resumes deletion. Reviewed retention
records are explicit operator decisions; no legal compliance is asserted.

Physical user erasure is conservatively deferred while ANY workspace hold is
active: owned-study cascades and shared comments/AI cannot safely separate other
held participants. Requests remain incomplete even if the metadata-only worker
job succeeds. After release, POST privacy-requests/{id}/retry creates a fresh
durable job when no pending/running job exists; completed erasures are no-ops.
Direct collection withdrawal preserves held quality summaries; all AI invalidation
entrypoints preserve output/evidence under any workspace hold while invalidating
access. Recording withdrawal blocks asset/link access but preserves held transcripts.
Financial minimization takes the workspace lock and skips held beneficiaries,
including calls through the older reviews route. Generic reviewed-retention input
rejects financial purpose: the dedicated settlement policy remains authoritative.

Restore: full pg_dump/pg_restore is performed with external PostgreSQL tools. Python
copies only directories without symlinks and replays latest authenticated UUID/purpose
manifest before readiness marker. Snapshots/manifests require external encrypted storage;
HMAC is authentication, NOT encryption. Latest digest must come from current live
export through a trusted channel (a signature alone cannot prevent rollback).

## Restore operator sequence

1. Quiesce writes for a consistent database/files snapshot; snapshot creation does
   not itself pause application writers. Use existing PostgreSQL client container
   if application image lacks pg_dump. Never install or activate a cloud connector.
2. Save custom-format pg_dump without owner/ACL and private files on an encrypted,
   operator-managed volume, directory0700/files0600. Record the trusted snapshot
   manifest SHA256 binding both the dump and complete private-file inventory.
3. Provision a separate database ending `_restore`, owned by a dedicated operator
   role, with PUBLIC grants revoked. Never point restore at application/test DB.
4. Copy physical snapshot into empty isolated database and a separate `_restore`
   files directory; exclude `.privacy-ready`. Never enable serving yet.
5. Export CURRENT live tombstones and active-hold UUID scopes (manifest version2),
   not the tombstones inside the old snapshot,
   using `export_tombstones`. Distribute latest digest separately through a trusted
   channel; signing key is operator supplied (at least32bytes), never a default.
6. Run `python -m app.privacy_ops.restore` with URL environment-variable NAMES,
   files paths, manifest path, key-file path and current digest. No passwords in
   process arguments. Replay checks isolated database identity and files paths.
7. Verify `restore_ready` against the nonce/digest receipt in the restored DB and
   marker in restored files. On any error readiness remains false; retry replay.
8. The routine `tests/test_privacy_ops_restore_db.py` uses the guarded test database
   as a source and a newly created physical PostgreSQL TEMPLATE clone as target.
   It never migrates/resets the target; no optional RESTORE_* inputs or skip remain.
   Current holds missing from the snapshot refuse readiness before destructive
   replay until an authorized operator reconciles the reviewed decisions.

Full CLI sequence and prerequisites: docs/backend/P16_P17_API.md. The clone test
does not certify the operator's actual pg_dump archive or encryption setup.

No automatic encryption or retention law is implied by these tools. Backups and
UUID manifests remain sensitive; physical restore is an offline operator action.

## Scoped restore decisions (migration 019)

Manifest v3 additionally signs identifier-only resource decisions for session
withdrawal, raw-session retention deletion, asset/AI/snapshot/export deletion,
share revocation, and prior granted consent-receipt revocation. Replay never
promotes a resource decision to a subject erasure. Older manifests cannot certify
readiness. Active hold subject/workspace sets must match in both directions;
operators must reconcile changed legal decisions before any destructive replay.
Source resource decisions are committed with DB mutation; storage deletion events
commit before filesystem side effects. Missing resource shells replay as no-ops.
Asset sweeps select expiry and owner/recording-subject hold exclusions in SQL
before deterministic bounded limits. Invalidated AI output/instructions/coverage
or evidence remain eligible after a hold is released.

V3 also requires `contact_holds` identifier scopes for private contacts that have
no linked account. Both current/restored account-subject holds and contact holds
must have equal active sets before any event, erasure, or readiness marker.
A newer hold or an old snapshot's subsequently released hold both quarantine the
restore until reviewed operator reconciliation; replay does not manufacture hold
review attribution. Lifecycle resource actions remain delegated to their scoped
producer callbacks and never implicitly authorize whole-account erasure.

V3 `accounts` contains only subject/workspace UUIDs from all pending or completed
self-service account erasures. Account restriction replays after scoped decisions,
including users with zero workspaces; credentials/profile data are not exported.
It does not synthesize a completed account receipt. A pre-transfer snapshot may
retain a revoked sole-owner membership after restriction: operators must reconcile
workspace ownership through offline recovery; never reactivate erased credentials
to recover administrative access.

Account replay additionally rejects any active hold in the union of manifest
account scopes and snapshot-discovered scopes, plus direct subject holds. This
check precedes all destructive replay so a later hold cannot minimize held global
profile data merely because both copies agree that the hold exists. Rejection
leaves the snapshot transaction unchanged and the serving marker absent.
