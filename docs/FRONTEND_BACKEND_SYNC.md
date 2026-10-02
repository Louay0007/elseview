# Elseview — Frontend ↔ Backend Sync Plan

Source of truth per domain. `FE → BE` = backend must change to match frontend.
`BE → FE` = frontend must change to match backend. All routes under `/api/v1`.

## 0. Global rules (incl. UX writing)

- Frontend copy: clear, simple, easy. Short titles, one idea per sentence, plain words.
  No jargon, no long paragraphs. Every page: what it is + what to do next.
  Errors tell the user what happened + the one fix. EN + FR for every string via `useAuthLocale`.
- Auth: bearer in memory, refresh cookie `HttpOnly SameSite=Strict` on `/api/v1/auth`, `Origin: http://localhost:8080` + `X-CSRF-Token` on refresh/logout.

- Auth: bearer in memory, refresh cookie `HttpOnly SameSite=Strict` on `/api/v1/auth`, `Origin: http://localhost:8080` + `X-CSRF-Token` on refresh/logout.
- Idempotency: `Idempotency-Key` on study create/clone, billing writes, credit purchase, managed intake.
- Money is manual records only. No auto-charge, no bank automation.
- AI is mock by default; live LLM needs operator capability/privacy/host/pricing approval.
- Never reset prod DB; additive Alembic migrations only (`038_interview_drafts` current head).

## 1. Auth + onboarding — BE → FE (frontend follows backend)

Backend: `backend/app/auth/router.py` — register, verify-email, login, refresh, logout,
password-reset request/confirm, `GET /me`, login-sessions, workspaces, members, invitations, audit.

| Frontend | Must change to |
|---|---|
| `src/pages/auth/AuthFlow.tsx` (login/signup/verify/recover/reset/invitation, currently preview-only) | Call real endpoints in order; store access token in memory only; refresh via cookie; generic recovery messages; accept invitation with invited email |
| `src/pages/auth/CompleteProfile.tsx` | After verify, `GET /me` then `POST /workspaces`; keep phone/WhatsApp/company as local profile until BE profile API exists |
| `src/pages/workspace/Account.tsx` | `GET /me` for identity; sessions revoke via `DELETE /me/login-sessions/{id}`; change-password modal → `POST /auth/password-reset/confirm` (or new change-password endpoint P1); delete account → privacy-ops erasure |
| `src/pages/workspace/Settings.tsx` | Workspace rename is local only today — needs BE `PATCH /workspaces/{id}` (new); members/invite/audit map 1:1 already |

## 2. Study builder + test types — BE → FE (frontend follows backend)

Backend: `app/studies/router.py` — `GET /research-methods`, studies CRUD, versions `PUT` (`expected_revision`),
`validate`, `publish`, `new-draft`, `clone`, `PATCH state`, grants, `preview`, `/study-preview`.
7 core (`survey.single/multi/rating/text`, `preference`, `five_second`, `prototype.task`) + 7 advanced AI-era methods.

| Frontend | Must change to |
|---|---|
| `src/pages/workspace/Dashboard.tsx` 8 cards (prototype, card, preference, tree, survey, five, click, recruit) | Remap to BE registry: prototype→`prototype.task`, preference→`preference`, five→`five_second`, survey→`survey.*`, card/tree/click/recruit → advanced methods or templates; fetch `GET /research-methods`, never hardcode |
| New study flow (missing — `New study` button dead) | New pages: method picker → template (see §7) → `POST /studies` → version editor (`PUT` + `expected_revision`) → `validate` → `publish` → `preview` capability (`X-Preview-Token`, `/#preview=` fragment, strip from URL) |
| `src/pages/workspace/History.tsx` study-lifecycle table (mock) | `GET /studies`, versions, `PATCH state` (pause/resume/close/archive) — FE copy updated 2026-09-27; live wiring still pending workspace-scoped API client |

## 3. Recruit + collect (participant side) — BE → FE

Backend: `app/recruiting/router.py` (panel profile, contacts import/suppress, estimate, orders,
invitation, screen, reserve, qualifications) + `app/collection/router.py` (consent, sessions, answers
append-only, events, one-shot exposure, atomic submit, withdraw).

| Frontend | Must change to |
|---|---|
| Dashboard `Find people` (dead) | Recruit flow: estimate → order → invitation → screen → reserve → quota progress |
| No runner UI today | New participant runner: `GET /collection/consent` → `POST /sessions` → `PUT answers/{block}` (revisions, never overwrite) → `POST events` batches → `POST submit` (atomic) / `withdraw` |

## 4. Reviews + rewards — BE → FE

Backend: `app/reviews/router.py` — assignments/decision, appeal, my-rewards, cases, payments, journal.

Frontend: no review UI today. Build reviewer workbench (queue → decision → adjudication → appeal),
reward ledger view (immutable journal, manual payout records) inside Billing/Credits.

## 5. Analytics — FE → BE (backend follows frontend)

Frontend (`src/pages/workspace/Analytics.tsx` + `workspaceData.ts`, all mock) is the spec.
Backend (`app/analytics/router.py`, `BASE=/workspaces/{id}/analytics`) has snapshots/sources/comparisons/
reports/exports/shares but no aggregated dashboard endpoint.

Backend to build (P1):
- `GET /analytics/overview` → `{ studies_live, studies_draft, replies_total, replies_good, to_check, checkers, wallet }` (KpiGrid).
- `GET /analytics/replies-trend?weeks=N` → `[{week, replies}]` (AreaChart).
- `GET /analytics/check-split` → `[{name, value}]` accepted/flagged/rejected (PieChart).
- `GET /analytics/method-share` → `[{method, replies}]` (BarChart).
- `GET /analytics/leaderboard` → studies ranked with share % (Top studies table).
- `GET /analytics/launches` → quota `{name, screener, delivery, quota, pct, label}` cards.
- `GET /analytics/review-queue` → `{session, flags, votes, next}` table (joins reviews API).
- Reports/AI-ops cards already covered by `GET reports` + `ai/runs`; add `cost_estimate` field for `See cost` badge.
- Deterministic reducers stay server-side; small-group suppression stays; JSON/CSV export + revocable shares unchanged.

Frontend to change (P2): replace `workspaceData.ts` mocks with the above; empty states, not zeros.

## 6. History — FE → BE

Frontend (`History.tsx`: KPI, activity trend, events-by-kind, lifecycle table, filterable log) is the spec.
Backend has no workspace event log (only per-domain tables + workspace audit).

Backend to build: `GET /workspaces/{id}/history?kind=&since=` projecting studies/collection/reviews/
reports/AI/billing events newest-first + `GET /history/summary` (totals, kinds, weeks, latest).
Frontend: swap mocks for these; filters map to `kind`.

## 7. Templates — BE → FE

Backend: `app/templates/router.py` — 23 versioned recipes. Frontend: no gallery.
Build template gallery → instantiate → enters §2 version flow.

## 8. Longitudinal + evaluation — BE → FE

Backend: `app/longitudinal/router.py` (slots, bookings, diary, recordings/transcripts, drafts) +
`app/evaluation/router.py` (datasets, blind assignments, outcomes, exports).
Frontend: nothing yet. Build schedule/calendar (.ics via collaboration), diary runner, eval workbench later (P3).

## 9. Billing / Credits / Refer — meet in middle

Backend: `app/billing/router.py` — plans, subscriptions, invoices, payments, credits, quotas,
managed quotes. Frontend: `Billing.tsx`, `Credits.tsx`, `BuyCredits.tsx`, `Refer.tsx` all mock/zeros.
- Keep FE layout; wire `GET plans/subscriptions/invoices/payments`, `GET/POST credits`, `GET quotas/usage`.
- Refer 200-credit grant → `POST /billing/grants` (no payment-method UI; deleted nav stays deleted).
- `BuyCredits` checkout → `POST /credits` + `POST /invoices/{id}/payments` (manual record).

## 10. Account-level pages — mostly FE-complete, wire prefs

- `Notifications.tsx` toggles → collaboration webhook `PUT preference` + `GET get_preference`; system row static (privacy/terms links).
- `Refer.tsx` send/copy/share → recruiting invitation + collaboration share; earnings → billing grants.
- Support row → `SupportCenter` panel (done, no API).

## 11. UX copy pass (applies to every page) — implemented 2026-09-27

Done in this pass: shortened titles, leads, buttons, and hints across
Dashboard, Analytics, History, Settings, Account, Notifications, Refer,
Credits, Billing. Pattern everywhere: title (<=6 words) -> 1-line
explanation -> 1 primary action. All strings stay EN+FR via `useAuthLocale`.
Verified: `tsc --noEmit` clean, `pnpm test` 22 passed.

- Rewrite titles/leads/buttons in plain language before wiring data.
- Pattern: title (≤6 words) → 1-line explanation → 1 primary action.
- Keep existing EN/FR keys, shorten values. Example: "Your numbers at a glance" + "424 replies · 64% full · 3 to check."
- Tables get plain column names; charts get one-line descriptions (already the Analytics pattern — extend everywhere).

## §2 implementation log (2026-09-27)

- `frontend/src/lib/api.ts` — bearer + `Idempotency-Key` + `X-Preview-Token` fetch helper (no token stored; caller holds it in memory).
- `frontend/src/lib/methods.ts` — 15 backend method keys with plain EN/FR copy (`prototype.task`, `preference`, `five_second`, `survey.*`, `survey.ranking`, `survey.constant_sum`, `first_click`, `card_sort`, `tree_test`, `accessibility.issue`, `language.review`, `media.review`).
- `frontend/src/pages/workspace/Dashboard.tsx` — cards remapped to backend keys (card→`card_sort`, tree→`tree_test`, click→`first_click`, survey→`survey.single`, recruit→recruit flow); `New study` + `Find people` + each card route to `/studies/new(?method=)`.
- `frontend/src/pages/workspace/NewStudy.tsx` — 3-step flow (Pick a test → template → name it) using `GET /research-methods`, `GET /templates`, `POST /studies` or template instantiate with idempotency; pre-selects `?method=`.
- `frontend/src/pages/workspace/History.tsx` + `workspaceData.ts` — lifecycle rows now show backend revision/state wording (draft/published/paused, locked shared work).
- Still missing (needs backend-authenticated workspace context + editor): version `PUT` editor (`expected_revision`), `validate`/`publish`/`new-draft`/`clone`, `PATCH state` actions, `preview` capability (`X-Preview-Token`, `/#preview=` fragment).

## Build order

1. Auth wiring (§1) — unblocks everything real.
2. Analytics overview endpoints (§5) — biggest visible win, FE already designed.
3. Study create→publish→preview (§2) + templates (§7).
4. Recruit + runner (§3), reviews (§4).
5. History API (§6), billing/credits wiring (§9), longitudinal/eval (§8).
