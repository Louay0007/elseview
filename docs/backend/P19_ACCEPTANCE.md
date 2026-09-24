# P19 — narrow backend acceptance evidence

## Executed scope

`backend/tests/test_product_acceptance.py` contains three PostgreSQL workflows.
Collection uses actual FastAPI TestClient requests; review, analytics and AI use
production services with committed transactions. This is not one browser test,
nor a claim that all ten full-product stories are complete.

1. `test_accepted_answer_review_reward_report_mock_ai`: HTTP answer/submission
   (via the reused reviewed fixture), two distinct independent reviewers, one
   earned 1,000-millime reward, included-answer metric, approved report and
   suppressed small-sample share, cross-workspace snapshot denial, idempotent
   researcher-assistance request, durable mock result and cross-workspace AI denial.
   The AI output remains a draft: this workflow does **not** claim a cloud-approved
   participant-derived report. Assistance is researcher-only `study_helper`.
2. `test_network_replay_preserves_one_answer_and_submission`: replay session
   creation, replay an acknowledged autosave as if its response was lost, reject
   a conflicting revision, replay submit, verify one answer revision and one job.
   This models retries at HTTP level, not a browser reload or network fault proxy.
3. `test_withdrawal_between_ai_prepare_and_final_write`: accepted/rewarded answer,
   frozen snapshot and exact optional AI consent, durable prepare, synthetic
   provider return, separately committed consent withdrawal, rejected final write,
   no persisted draft/approved output, earned reward retained. This calls `finish`
   directly, rather than merely testing pre-dispatch authorization. The job fence
   returns false on revocation; it does not raise a domain exception.

Fixtures are reused from `test_ai_db.collected` and `test_reviews_db.reviewed`;
the latter sends the answer and submit HTTP requests and seeds reviewer identities.
`test_reviews_db.decisions` applies the two human decisions. No new fixture estate,
application changes, dependencies or live providers were introduced.

## Reproduction and observed result

Run only with an exclusive disposable DB grant (runner resets test data):

```sh
scripts/dev exec -T -e TEST_ALLOW_RESET=elseview_test backend \
  python -m app.test_runner -q tests/test_product_acceptance.py
```

Observed: **3 passed in 3.57s** against the supplied migrated test database.
The initial single-workflow artifact passed in 2.68s. One intermediate privacy
assertion expected an exception; inspection and rerun established the intended
false-return fence contract. Both AI workflows assert `ai_mode == "mock"` before
dispatch. No cloud expenditure or external calls are needed.

## Ten-story map — existing explicit tests, not newly rerun evidence

Paths below are relative to `backend/tests/`. These references partition coverage;
they do not imply that every clause of a story is exercised in one scenario.

| Plan story | Exact existing references and boundaries |
| --- | --- |
| 1. French/Arabic preference → recruit → reward → report/AI | New accepted workflow above supplies the backend spine. `test_collection_db.py::test_preferences_exposure_and_private_assets`; `test_analytics_db.py::test_accepted_snapshot_revision_digest_exports_review_drift`; `test_ai_db.py::test_ai_http_worker_approval_and_access`. Bilingual browser and live cloud combined journey not asserted here. |
| 2. Private contacts and tenant isolation | `test_recruiting.py::test_private_import_binding_suppression_tenant_boundary`; `test_recruiting.py::test_server_selected_recruitment_no_directory_and_deduplication`; `test_recruiting.py::test_cross_source_identity_deduplication`. New snapshot/AI tenant denials complement these, not an exhaustive search/export/email attack matrix. |
| 3. Lost network and exactly-once reward | New replay workflow; `test_collection_db.py::test_real_nonmember_resume_revision_branch_submit_once`; `test_collection_db.py::test_concurrent_duplicate_submission_one_job`; `test_reviews_db.py::test_consensus_reward_retry_payment_failure_reversal`. Browser reload remains separate. |
| 4. Last slot race | `test_recruiting.py::test_last_slot_concurrent_and_overlap`; `test_longitudinal_db.py::test_capacity_booking_real_http_race`. |
| 5. Diary windows/missingness/withdrawal/pay | `test_longitudinal_db.py::test_multiday_diary_independent_sessions_and_grace`; `test_collection_db.py::test_nonmember_privacy_request_and_launch_purge`; new privacy workflow retains earned reward. These are complementary, not one multiday browser story. |
| 6. Design methods and keyboard alternatives | `test_advanced_db.py::test_all_seven_publish_preview_collect_reduce`; `test_advanced_methods.py::test_tree_detour_and_impossible_transition`; `test_advanced_methods.py::test_card_empty_categories_and_unplaced`; `test_advanced_methods.py::test_click_private_projection_and_overlap_boundary`. Keyboard/browser evidence belongs to the frontend release gate; no accessibility certification claimed. |
| 7. Invented AI sources/provider failure | `test_ai.py::test_bad_outputs_rejected`; `test_ai.py::test_quote_evidence_and_coverage`; `test_ai_db.py::test_ai_budget_failure_release_and_missing_usage`; `test_ai.py::test_sdk_error_single_dispatch`. No simultaneous collection/provider-failure load claim. |
| 8. Withdrawal during inference/export | New final-write workflow; `test_ai_db.py::test_snapshot_requires_exact_optional_consent_and_revocation_fence`; `test_analytics_db.py::test_live_withdrawal_without_epoch_invalidates_every_access`; `test_privacy_ops_db.py::test_erasure_io_failure_stays_retryable`. Provider-side forgetting is not guaranteed. |
| 9. Separate financial domains/retries | `test_billing_db.py::test_http_invoice_payment_credit`; `test_billing_db.py::test_actual_ai_sale_distinct_from_provider_cost`; `test_billing_db.py::test_http_payment_race_and_duplicate_reference`; `test_reviews_db.py::test_consensus_reward_retry_payment_failure_reversal`. |
| 10. Isolated restore | `test_privacy_ops_restore_db.py::test_actual_postgresql_snapshot_replays_latest_erasure`; `test_privacy_backup.py::test_snapshot_binds_private_bytes_and_refuses_tampering`; `test_privacy_ops.py::test_restore_requires_isolated_database_and_files`. No restore was run in this narrow window. |

OpenAPI approval, browser acceptance, security/release review, operational evidence
and unresolved vendor/legal gates remain owned by the lead. This document is a
bounded backend acceptance handoff, not final full-product release approval.