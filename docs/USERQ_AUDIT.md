# UserQ Researcher Workflow — Audit Report (source: https://app.userq.com, JS bundle `main.394d2d94.js`)

Goal: what UserQ's researcher flow has that Elseview's backend lacks. SPA (React) behind login; findings from static bundle + route map.

## 1. Researcher routes
- `/researcher/` dashboard, `/researcher/tests/` test list, `/researcher/project/` projects
- `/researcher/study/introduction`, `/researcher/study/conclusions`
- `/researcher/target_group/` + `/target_group/add/:project_id` — saved audiences
- `/researcher/team` — seats / roles, `/researcher/settings`, `/researcher/billing/plans`, `/billing/plan/change`, `/billing/subscribe`
- `/researcher/support/`, `/support/contact` (topics: Interface & Navigation, Test creation, Technical, Pricing & Billing, Testers recruitment, Other)
- Tester side: `/tester/tests`, `/tester/wallet`, `/tester/profile/step`, `/tester/support`

## 2. Test types (7 = same as Elseview core)
`publishing_credits_*`: survey, five_seconds_test, preference_test, prototype_test, tree_test, card_sorting, first_click.
Plan matrix marks surveys / five-second / first-click `coming_soon` on some tiers — tier-gating per method (Elseview: no gating).

## 3. Test-creation wizard (per tool) — MISSING in Elseview
Each tool has its own builder page (`create-tree-test-page-wrap`, `create-prefer-text-wrap`, `create-test-data-wrap`):
1. **Welcome page** (`test-welcome-form-wrap`): custom text + image per test.
2. **Task/design setup**: tree = nodes editor; preference = text variants; prototype = task + follow-ups; survey = question list.
3. **Follow-up / debrief questions** (`test-followup-questions-wrap`, `test-debriefingquestion-page-wrap`): post-task questions per test — Elseview has `recall_block_ids` only on five_second.
4. **Thanks page** (`test-thanks-page-wrap`): custom thank-you text per test.
5. **Summary modal** (`test-summary-modal-wrap`): sections = Welcome page data, screening questions, participants, publishing fees, design; then publish.
6. **Preview** (`test-preview-wrap`, `preview_test_link`, 320 preview mentions): shareable preview link per test.
7. **Password access** (`test-password-access-wrap`): password-gate a study link — Elseview has nothing.

## 4. Survey question types (6) — Elseview covers 4 shapes, lacks logic
`singlechoice, multiplechoice, rankingscale, likertscale, likertscale_single, ratingscale`.
Logic engine: `is_logic` per question, per-option `jumpTo` / `jump_to_question`, "End Survey" terminal, validators (`BF` cycle check, `question_error`). Elseview: `branches` eq/contains/gte exist but no per-option jump UI, no cycle check, no End Survey.
Also: question images (`question-input-img-thum`), option images.

## 5. Recruiting / target groups — biggest gap
- Saved target groups: name + age-range slider + gender tab (`accordians_recruitment_test`: min_age/max_age/gender).
- Summary: "Total participants from UserQ panel", screening questions in summary.
- Panel is priced separately; own-testers link free. Custom recruitment = quoted, client-approved before start.
- Elseview: filters_json/screener/quotas exist, but NO saved audiences, NO age/gender builder, NO panel-vs-own cost split, NO quote-approval step.

## 6. Publishing & credits
- Per-tool publishing fee keys (`Test publishing fee | FREE` row in summary) — Elseview: one generic credit model.
- Plans matrix: live-study count, study duration, pre/post questions, per-method flags, respondents count, report availability, CSV export, archive, welcome-page image, seats/roles, shared credits.

## 7. Reports
Result nav (`test-result-nav-wrap`): per-question results incl. `likertscale_single_results_question`, issues overview, CSV export, online report, archive.

## 8. Backend fix list (prioritized)
1. P0: per-test welcome/thanks text+image (add to StudyVersion or new table); preview links already exist — expose per study.
2. P0: post-task follow-up questions for ALL tools (generalize `recall_block_ids` → `followup_block_ids`, or document pattern).
3. P0: survey logic — per-option jump targets + cycle validation + "End survey" terminal (extend `branches`).
4. P1: saved audiences table (name, age_min/max, gender, owner) + link to RecruitmentConfig; panel-vs-own source + quote-approval state on Reservation/Config.
5. P1: password-gated share links (extend ReportShare with optional password hash).
6. P1: per-method pricing key on credits/billing (`publishing_credits_*` equivalent).
7. P2: plan feature matrix per method (tier-gating), question/option images, CSV export check, archive state (backend has archived for studies only).
