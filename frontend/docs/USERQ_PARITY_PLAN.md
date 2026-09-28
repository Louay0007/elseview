# UserQ Parity — Backend Fix Plan (implement in this order)

Flow target (all 15 types): Welcome → Task → Follow-ups → Thanks → Summary → Preview → Publish → Collect → Report.
Wizard steps map 1:1 to endpoints below. Additive migrations only (`040_`+).

## F1. Study pages: welcome + thanks (P0)
- New `study_pages` table: `(workspace_id, version_id, slot welcome|thanks, title, body, image_asset_id|NULL, enabled bool)`.
- `PUT version` accepts `pages`; `validate` requires welcome enabled; frozen into `content_hash`.
- Runner + preview: `welcome` first step, `thanks` terminal (no answers stored on either).
- Files: `studies/models.py`, `methods.py` (PageBlock), `service.py` validate/publish/preview_step, migration `040_study_pages`.

## F2. Follow-up questions for every tool (P0)
- Today only `five_second.recall_block_ids` (must be later `survey.text`, exposure can't branch).
- Generalize: `followup_block_ids: list[Key]` (max 10) on ALL block configs; rule = referenced blocks come later + are `survey.*`; exposure keeps "no branch" rule.
- Runner: after main block, auto-queue follow-ups. Preview same.
- Files: `methods.py` all Configs + validate, `service.py` next_key/preview_step, migration not needed (JSONB) — bump version note.

## F3. Survey logic: per-option jump + End Survey + cycle check (P0)
- Today: block-level `branches` (eq/contains/gte), validated acyclic. Missing: per-option `jumpTo`, terminal node.
- Add `jump_to: Key | "end" | NULL` on `Option`; keep block branches. Validate: full cycle check incl. jumps (reuse positions map), dangling target, "end" allowed anywhere.
- Runner `next_key` resolves option jump first, then branches. Preview same.
- Files: `methods.py` Option + validate_structure, `service.py` next_key, tests.

## F4. Question + option media (P1)
- Add `image_asset_id|NULL` on `Option`, `prompt_image_asset_id|NULL` on Block. Reuse `asset_refs()` + preview-asset auth. No remote media (rule stays).
- Files: `methods.py`, `exports.py` allowlist, migration not needed (JSONB).

## F5. Saved audiences (P1)
- New `audiences` table: `(workspace_id, name, age_min 18-90, age_max, gender any|female|male, owner)`.
- `RecruitmentConfig.audience_id|NULL`; estimate filters by audience; screener unchanged.
- Endpoints: CRUD `/audiences`, `POST estimate {audience_id}`.
- Files: `recruiting/models.py`, `service.py`, `router.py`, migration `041_audiences`.

## F6. Panel vs own + quote approval (P1)
- `RecruitmentConfig.source: panel|own`, `quote_state: none|quoted|approved`, `quote_millimes|NULL`.
- Panel source requires quote approved before invite; own-testers link free (existing manual delivery).
- Files: `recruiting/models.py` + check constraint, `service.py` issue_invitation guard, migration `042_recruit_quote`.

## F7. Password-gated share links (P1)
- `ReportShare.password_hash|NULL` (bcrypt, 60ch); `POST shares {password?}`; read_share verifies (generic 404 on mismatch).
- Files: `analytics/models.py`, `service.py` create_share/read_share, migration `043_share_password`.

## F8. Per-method publishing fee (P1)
- `billing` price key per method: `publishing_fee_{survey,five_second,preference,prototype,tree_test,card_sort,first_click}` (millimes, default 0 = FREE row in summary).
- Summary endpoint returns fee lines; publish checks credit >= fee.
- Files: `billing/service.py`, new `GET .../publish-quote {version_id}` (reuse estimate pattern).

## F9. Summary modal data (P0, read-only)
- New `GET .../studies/{id}/versions/{v}/summary`: welcome enabled, follow-up count, screener count, quota/capacity, fee lines, design (block types). Frontend renders UserQ-style summary before Publish.
- Files: `studies/router.py` + `service.py` summary().

## F10. Plan tier-gating per method (P2)
- `plans` table or config: method -> min tier; `validate`/publish returns `METHOD_NOT_IN_PLAN` (402-style 409). Keep default all-open.
- Files: `billing/service.py`, `studies/service.py` publish guard.

## Per-type data/settings checklist (backend truth today)
| Type | Config keys | Answer | Fix |
|---|---|---|---|
| survey.single | options[2-100], randomize | option_id | F3 jump, F4 images |
| survey.multi | + min/max_selected | ids[] | F3 contains-branch ok, F4 |
| survey.rating | min/max/step, low/high labels | number | F3 gte-branch ok |
| survey.text | min/max_length | text | F2 as follow-up target |
| preference | variants[2-10]+asset, tie/none | variant/tie | F1 pages, F2 follow-ups |
| five_second | asset, 5000ms, recall_ids | recall texts | F2 generalize |
| prototype.task | flow/steps, target link+auth | steps | F2 follow-ups |
| survey.ranking | options, rank_count | ordered ids | F3 |
| survey.constant_sum | options, total_points | allocations | F3 |
| first_click | asset w/h, input_modes, AOIs? | x,y,ms | F1+F2 |
| card_sort | mode, cards[1-100], categories, unplaced | groups | F1+F2 |
| tree_test | nodes[1-100], root_id, targets? | visited/selected/gave_up | F1+F2 |
| accessibility.issue | task_block_id, context, criteria | issues[] | F2 |
| language.review | source text/langs, rubric, dimensions | ratings/issues/rewrite | F2 |
| media.review | wav/mp4, duration, replay 1-10, seek policy, alt text | playback events | F1+F2 |

## Build order
`040_study_pages` → F2+F3+F4 (no migration) → `041_audiences` → `042_recruit_quote` → `043_share_password` → F8+F9 → F10.
