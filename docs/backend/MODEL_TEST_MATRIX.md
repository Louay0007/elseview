# Elseview — Model and test acceptance matrix

**Brand:** Elseview — See what you’re missing.

**Status:** planned coverage, not executed backend tests. This inventory accompanies `/Users/user/Workspace/startup-act/BACKEND_IMPLEMENTATION_PLAN.md`.

## 1. Universal tests for every implemented model

- **D01:** valid creation and round-trip, defaults, nullability and schema.
- **D02:** invalid boundary values, negative/overflow counts, invalid enum and unknown JSON fields.
- **D03:** uniqueness, including NULL and partial-index behavior, tested directly against PostgreSQL.
- **D04:** parent/FK consistency, wrong workspace and wrong study/version references.
- **D05:** permitted/forbidden updates, terminal states and immutable publication.
- **D06:** deletion, consent withdrawal, retained financial minima and derivative cleanup.
- **D07:** concurrent writes and retries relevant to the model, using independent DB sessions.
- **D08:** authorization and safe API projection for every reader/writer role.
- **D09:** migration from clean and preceding schema, populated fixtures, rollback/recovery safety.
- **D10:** audit/log redaction and absence of secrets/PII in nonpermitted payloads.

Apply D01–D10 to each physical model where applicable. For a combined JSON model apply equivalent schema, parent-version, mutation and service tests rather than pretending a nonexistent SQL FK exists. Mark a case not applicable with a reason; never simply omit it. Every named implemented test belongs in the phase evidence log.

## 2. Mapping of all 70 extended dictionary models

The canonical implementation column wins over older names. Combined rows do not create duplicate SQL tables. Phase ranges mean the same component is extended progressively. Default stack remains four containers with cloud AI.

| Extended reference model | Phase | Canonical implementation | Required specific cases in addition to D01–D10 |
|---|---|---|---|
| `users` | P02 | users | Unique normalized identity; disabled login; identity erasure does not reveal private panels |
| `auth_credentials` | P02 | users password fields; separate credentials only for added MFA | Password hash not plaintext; recovery; MFA isolation when enabled |
| `refresh_tokens` | P02 | refresh_tokens | Expiry; family replay; rotation race; user revocation |
| `api_keys` | P16 | api_keys | Scope; expiry; secret returned once; revoked access |
| `workspaces` | P02 | workspaces | Unique slug; private defaults; privacy epoch update |
| `workspace_memberships` | P02 | memberships | Unique workspace/user; last owner race; revoked role |
| `workspace_invites` | P02 | workspace_invites | Expiry; repeated acceptance; role escalation |
| `platform_panel_profiles` | P06 | participant_profiles | Separate opt-in; no implicit private contact merge |
| `platform_panel_consents` | P06 | panel_consents | Purpose/version; latest withdrawal stops recruitment |
| `panel_qualifications` | P06 | qualifications | Versioned skill; expiry; cannot self-assert verified score |
| `private_panel_contacts` | P06 | private_contacts | Workspace-only lookup; same email in two clients stays separate |
| `private_panel_consents` | P06 | private_contact_consents | Client purpose; suppression; no global opt-in effect |
| `studies` | P05 | studies | Owner and grant; status transitions; tenant isolation |
| `study_versions` | P05 | study_versions | Unique version; frozen public blocks/private rules; publication validation |
| `blocks` | P05 | study_versions.blocks_json, not a table initially | Unique block key; closed type registry; correct version; strict JSON |
| `block_secrets` | P05 | study_versions.rules_json, not a table initially | No safe serializer leakage; immutable hidden keys |
| `study_launches` | P05–P06 | launches | Fixed published version; capacity/offer snapshot; pause race |
| `experiments` | P05–P07 | published assignment config JSON | Approved algorithm; no hidden model identity leak |
| `experiment_variants` | P05–P07 | typed variant config JSON | Known keys; immutable stimuli; valid weights and ties |
| `recruitment_campaigns` | P06 | launch targeting config; split only when needed | Versioned audience; all sources obey launch-wide cap |
| `recruitment_candidates` | P06 | candidates | Minimal frozen attributes; source XOR; duplicate identity per launch |
| `recruitment_invites` | P06 | invitations | Hashed token; replay; expiration; subject binding |
| `quota_cells` | P06 | quota_cells when segmented quotas enabled | Capacity; intersecting cells; no count-then-insert race |
| `quota_reservations` | P06 | reservations and reservation_cells for segment holds | Atomic consume/release; expiry vs submission; reward commitment |
| `screener_results` | P06 | candidate screener decision JSON initially | Server-only eligibility; no answer key leak; attempt rule |
| `sessions` | P07 | sessions | Pinned version; reservation; correct occurrence; terminal state |
| `answers` | P07 | answers | Append revision; status/value rules; branch invalidation; one final response |
| `response_events` | P07 | response_events | Duplicate event; order; source attribution; no secret payload |
| `experiment_assignments` | P07 | immutable session assignment JSON initially | Stable permutation across retries; no client reshuffle |
| `diary_occurrences` | P12 | diary_occurrences | Unique date/participant; timezone; grace boundary; separate sessions |
| `idempotency_records` | P03 | idempotency_records | Scope; request hash conflict; race; persistent business uniqueness |
| `schedule_slots` | P12 | schedule_slots | Host overlap; time ambiguity; capacity; cancellation |
| `bookings` | P12 | bookings | Last-seat race; reschedule; attendance evidence; stale reminder |
| `quality_rules` | P05/P08 | published version rules JSON initially | Frozen rules; correct locale; supported checks |
| `quality_flags` | P08 | quality_flags | Unique rule/source key; flag is not rejection or nonpayment |
| `quality_reviews` | P08 | review_decisions | Assigned reviewer; no self-review; independent rounds; appeal history |
| `dataset_snapshots` | P09 | analysis_snapshots | Stable membership; exclusions; consent epoch; no drifting reads |
| `dataset_items` | P09 | snapshot_sources | Correct revision FK; digest; tenant; withdrawal lineage |
| `analysis_results` | P09/P10 | report_versions typed metrics/insights JSON initially | Deterministic counts; null denominator; draft/approved separation |
| `source_evidence` | P10 | ai_evidence with report source references | Source ownership; exact quote/span; source revocation |
| `ai_budgets` | P10 | usage_budgets | Workspace and study lock; Decimal currency; concurrent reservation |
| `ai_runs` | P10 | ai_runs | Approved cloud model/config; snapshot; state; human-only denial |
| `ai_chunks` | P10 | bounded work plan JSON in ai_runs, attempt rows separately | Input coverage; overlap dedupe; retry cap; no source double count |
| `ai_chunk_items` | P10 | source ID membership in validated work plan | All IDs resolve snapshot_sources; no other workspace input |
| `ai_usage_events` | P10 | ai_attempts usage fields | Actual vs estimated; unknown outcome; provider ID; retry costs |
| `ai_cache_entries` | P10 | Valkey key to authorized immutable ai_run | Privacy/version/model invalidation; no cross-client cache hit |
| `assets` | P04 | assets | Private path; immutable checksum/dimensions; limits; purge |
| `asset_links` | P04 | asset_links | Exactly one allowed owner; same workspace; permitted purpose |
| `upload_intents` | P04 | upload_intents | Token expiry; bytes/hash; repeated complete; abandoned cleanup |
| `reports` | P09 | reports and report_versions | Approval snapshot; no mutable published narrative |
| `export_jobs` | P09 | jobs export kind + exports artifact metadata | Permission recheck; formula-safe output; restart; stale consent |
| `report_shares` | P09 | report_shares | Token scope; expiry/revoke; summary only; no raw identity |
| `billing_subscriptions` | P15 | subscriptions with frozen plan JSON | Plan effective date; limits; no retroactive repricing |
| `ledger_accounts` | P08/P15 | ledger_accounts | Unit/currency isolation; no cash/credit mixing |
| `ledger_transactions` | P08/P15 | ledger_transactions | Permanent event key; reversal; complete atomic posting |
| `ledger_entries` | P08/P15 | ledger_entries | Balanced lines; integer amounts; account/transaction same unit |
| `usage_events` | P15 | usage_events | Unique billable source; correct price snapshot; refund/reversal |
| `reward_records` | P08 | reward_records | Earned once; partial work policy; compensation survives withdrawal |
| `payout_records` | P08 | payout_records | Manual full settlement; unique reference; wrong amount rejected |
| `notifications` | P12/P16 | notifications | Recipient scope; due/retry; suppression; no real sends in tests |
| `consent_documents` | P04 | consent_documents | Immutable text/version/language; exact receipt reference |
| `consent_records` | P04 | consent_receipts | Purpose/subject; withdrawal history; optional recording/AI |
| `retention_policies` | P04/P17 | retention_policies | Reviewed duration; legal hold; no indefinite defaults |
| `privacy_requests` | P04/P17 | privacy_requests | Own-subject verification; immediate restriction; resumable erasure |
| `integrations` | P16 | integrations; cloud config operator-owned from P10 | Secret storage; approval; destination allowlist; revoke |
| `webhook_deliveries` | P16 | webhook_deliveries driven by jobs | HMAC timestamp; delivery dedupe; retry; redirect SSRF |
| `audit_events` | P02 | audit_events | Actor attribution; safe metadata; append-only permissions |
| `outbox_events` | P03 | combined into transactional jobs; no extra table | Domain change and job commit together; rollback creates neither |
| `background_jobs` | P03 | jobs plus job_attempts | SKIP LOCKED claim; leases; crash/reload; no broker dependence |
| `platform_audit_events` | P02 | audit_events with restricted global scope | Global vs workspace visibility; no cross-tenant personal data |

## 3. Additional models required by feature contracts

| Model | Phase | Purpose and acceptance |
|---|---|---|
| one_time_tokens | P02 | Email verification/recovery; single-use hashed expiry, generic responses |
| study_grants | P05, auth service P02 | Per-study capability; wrong-member reference, revocation during job/export |
| job_attempts | P03 | Lease ownership and execution history; stale result, uncertain external outcome |
| review_assignments | P08 | Least-privilege work allocation; no self-review or cross-study access |
| appeals | P08 | Participant challenge, status and adjudication; no historical decision overwrite |
| interaction_attempts | P07 | Server-bound one-shot exposure; restart/refresh cannot obtain clean extra attempt |
| report_versions | P09 | Immutable approved content and source population; changed sources invalidate access |
| transcript_segments | P12 | Imported/cloud-authorized text/time intervals; bounded offsets, source linkage, consent |
| invoices / invoice_lines | P15 | Frozen commercial records, integer TND units and reviewed tax metadata |
| customer_payments | P15 | Manual payment evidence separate from participant reward; reference dedupe |
| report_comments | P16 | Collaboration with artifact-specific permission; sensitive quotation restriction |

No new table is required for every metric, template, industry, prompt or block option. Keep bounded versioned structured configuration where adequate; normalize only when query integrity or actual scale justifies it.

## 4. Shared research-method tests

Each method must pass **M01 config validity**, **M02 response validity**, **M03 private-field projection**, **M04 version/assignment binding**, **M05 events/retry**, **M06 deterministic metrics/missingness**, **M07 consent/access**, and **M08 React renderer support** before publication is enabled.

| Method | Positive fixture | Invalid and boundary fixtures |
|---|---|---|
| single/multi survey | Valid selected keys | Unknown/duplicate key, min/max, omitted versus empty |
| rating/text | Valid stepped score; French/Arabic/Arabizi text | Nonfinite score, off-step value, Unicode limits, unsupported locale |
| ranking/constant sum | Unique ranks, exact total | Partial/duplicate rank, float points, wrong total |
| prototype task | Owned or authorized external link with outcome | Cross-origin false telemetry claim, timeout versus success |
| five second | One uninterrupted valid exposure | Hidden tab, refresh, over/undershoot, missing events, repeated reveal |
| preference | Stable assignment and allowed tie | Changed order, unknown variant, disallowed tie, fabricated assignment |
| first click | Valid normalized point and pinned asset | Outside image, wrong dimensions, overlap/edge polygon, keyboard input |
| card sort/tree | Valid groups/path | Duplicate/missing cards, impossible edge, cycle, give-up miscount |
| diary/interview | Due entry or authorized booking | Grace expiry, timezone mismatch, duplicate occurrence, double booking |
| accessibility/language | Task-linked issue or valid rubric | Unneeded sensitive data, fabricated quote, false certification |
| pairwise/annotation | Independent labels and tie outcome | Self-review, label leakage, invalid span/polygon, dataset split leakage |
| chatbot/media | Authorized test endpoint or consented evidence | SSRF, real production action, missing recording consent, fake transcript |

## 5. Feature-to-end-to-end evidence

A feature is complete only if its model tests, service tests and API contract pass together. For React-only behaviors such as visible exposure timing, focus order, RTL and keyboard sorting, report the browser acceptance status separately; backend validation alone cannot prove them.

Record test counts and actual failure/skip reasons. Default runs use mocked cloud AI and synthetic data. Provider integration, clinical/legal claims, representative sampling and real money movement are outside a generic passing-test assertion.
