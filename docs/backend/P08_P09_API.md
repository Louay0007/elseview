# P08/P09 — Review, compensation, analytics and reports

Development implementation for the existing four-service application. All endpoints
below start with `/api/v1`. Use verified-account bearer authentication except for
explicit report-share capabilities. No provider calls or financial transfers occur.

## P08: human review

Research review is separate from deterministic quality evidence. A completed
`collection.quality` job materializes a review case and deduplicated quality flags.
Pinned private study rules support `expected_option`, `min_text_length` for text,
and `min_elapsed_ms` for prototype tasks. Short/fast responses are evidence, not
automatic proof of dishonesty or grounds for automatic compensation denial.

The workspace route prefix is `/workspaces/{workspace_id}/reviews`.

1. A study administrator discovers submitted cases through
   `GET /studies/{study_id}/cases` and assigns two **different** reviewers through
   `POST /sessions/{session_id}/assignments`, passing `reviewer_id` and
   `kind: "independent"`. Each reviewer needs the study's `review` capability;
   participants cannot review their own responses.
2. Reviewers use `GET /my-assignments` and `GET /assignments/{assignment_id}`.
   Assigned evidence is scoped to that response. Independent reviewers do not see
   each other's votes, rationale, or participant identity.
3. `POST /assignments/{assignment_id}/decision` requires:

   ```json
   {
     "command_key": "a-client-generated-uuid",
     "verdict": "accepted",
     "rationale": "The submitted responses satisfy the study requirements.",
     "evidence": []
   }
   ```

   Runtime UUIDs must replace the descriptive identifier above. Reuse the exact
   command after a network failure. A changed command conflicts. Rejection requires
   nonempty evidence referencing actual submitted block keys, for example
   `single: the response conflicts with the stated attention instruction`.
4. Two matching decisions finalize the case. Disagreement requires a fresh reviewer
   with `kind: "adjudication"`; adjudicators may see prior decision evidence.
5. The participant may appeal a rejection using
   `POST /sessions/{session_id}/appeal` with `command_key` and `reason`. One appeal
   is supported; it requires a fresh `kind: "appeal"` reviewer and preserves prior
   decision history. A denied appeal cannot be reopened through repeated commands.
6. `GET /sessions/{session_id}/status` serves the participant or authorized study
   administrator, including outcome, disagreement count and appeal history.

## Earning, manual payment and journal

- Acceptance creates at most one reward for a nonzero pinned reservation offer.
  Unpaid participation does not create a zero-value journal transaction.
- A workspace owner/admin must first create an explicit reviewed financial policy
  via `POST /financial-retention`, with `settled_days` and `rationale`. The configured
  duration is an operator policy, **not a claim about legally required retention**.
- Owner/admin financial routes include `GET /rewards`,
  `GET /rewards/{reward_id}/payments` and `GET /journal`. A participant can read
  only their own minimal obligations through `GET /my-rewards`, independently of
  withdrawn research consent.
- `POST /rewards/{reward_id}/payments` records `command_key`, full
  `amount_millimes`, `currency: "TND"`, unique `external_reference`, non-sensitive
  reconciliation `evidence`, and `failed`. Failed attempts create no journal posting
  and do not mark the reward paid. Partial settlement is explicitly unsupported.
- `POST /payments/{payout_id}/reverse` appends the exact opposite posting and reopens
  the obligation; it does not edit the original journal. Repeated reversal is safe.
  Reversal is denied after beneficiary identity has been lawfully minimized rather
  than reopening an obligation whose beneficiary cannot be identified.
- Journal entries use integer millimes and one currency. Database constraints enforce
  balanced postings, full settlement, append-only history and scope. Software credits
  and participant cash are never implicitly interchangeable.
- Withdrawal/erasure removes research evidence and derivatives, **not an earned
  obligation**. Outstanding obligations retain the minimum beneficiary identifier.
  Settled records may unlink identity only after their explicit reviewed interval.
  An owner/admin can run the bounded `POST /financial-retention/sweep` operation
  to apply due minimization without changing the stored policy or server clock.
  Never put bank credentials, identity documents or sensitive contacts in evidence.

## P09: deterministic snapshots

The workspace route prefix is `/workspaces/{workspace_id}/analytics`.

- `POST /snapshots` takes `study_id` and published `version_id`. It freezes a bounded
  manifest (maximum 1,000 sessions) under the workspace transaction lock. Exceeding
  the bound is an error, not a silently truncated report.
- The population is **nonwithdrawn, nonerased sessions at capture**, not an all-time
  participation count. Each session is included only with exact live study consent
  and a final P08 acceptance. Pending/not-submitted/consent exclusions remain pinned;
  later acceptance does not silently change an existing snapshot.
- Sources bind final answer revision IDs, digests, consent context and review decision
  generation. Autosave revisions are not counted as additional people. Source unit
  is explicitly `session`; the system does not claim unique people across studies.
- Selection distributions, ratings/medians, preferences/ties, completion, completed
  task time, exposure timing and missingness carry denominators, exclusions,
  provenance and metric version. Empty denominators produce null, not fabricated zero.
- `GET /snapshots/{snapshot_id}` returns privacy-filtered metrics. The `/sources`
  route requires raw-data permission. Comparisons use compatible measurement
  definitions and are descriptive, not causal; small and complementary groups are
  suppressed. Raw access remains an explicitly privileged operation.
- Nonraw metric releases also compare included populations against stored compatible
  snapshot history, including invalidated snapshots. An overlapping difference of
  fewer than five sessions suppresses the entire summary on individual snapshot,
  report, summary-export and share routes—not merely the comparison endpoint.
  This is conservative suppression, not a differential-privacy guarantee.

## Reports, exports and sharing

1. `POST /reports` takes `snapshot_id` and creates a draft.
2. `POST /reports/{report_id}/approve` requires publication permission and
   `expected_revision`. Approved membership is immutable.
3. `POST /reports/{report_id}/revise` creates a new revision from `snapshot_id` and
   `expected_revision`, rather than overwriting an approved report.
4. `POST /reports/{report_id}/exports` takes `format: "json" | "csv"` and
   `scope: "summary" | "raw"`. Export permission is required; raw exports additionally
   require raw-data permission. `GET /exports/{export_id}` checks permissions and
   source privacy again at download time. CSV escapes formula-leading values and
   retains Unicode. XLSX/PDF are not enabled without suitable confirmed dependencies.
5. `POST /reports/{report_id}/shares` requires an approved report and a bounded
   `ttl_seconds`. The returned secret is stored only as a hash. Public
   `GET /report-shares/{token}` returns an allowlisted redacted numeric summary—not
   raw answers, identities, labels, free text or source identifiers.
6. `DELETE /shares/{share_id}` revokes a share. Expiry, issuer permission changes,
   source withdrawal/erasure and changed review authority deny subsequent access.

Reports/exports/shares revalidate live source authority; cached or already-created
metadata does not authorize access. Erasure purges overlapping derived snapshots and
reports before source rows. Owner-study erasure also removes empty snapshots.
Already-downloaded files cannot be recalled by the server.

## Validation and limits

See `/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md` for
executed tests and limitations. No new frontend, public deployment, payment processor,
professional qualification certification, production privacy certification, or
browser Arabic-layout verification is implied by backend tests. The implementation
does not claim differential privacy or immunity to external auxiliary information.