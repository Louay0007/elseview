# Elseview — Full Product Plan: Researcher + Tester (with implementation plan)

Companion to `docs/FRONTEND_AUDIT.md` (frontend state) and `docs/FRONTEND_BACKEND_SYNC.md`
(sync rules). This file is the product truth: who does what, which backend exists,
what is missing, and the ordered build plan. UX rule everywhere: short title (≤6 words)
→ 1 plain sentence → 1 primary action. EN + FR. No jargon.

## 1. Product map

### Researcher journey

Signup → verify email → complete profile → workspace created → dashboard (empty state)
→ New study (method → template → name) → version editor (blocks) → validate → preview
(`/#preview=` capability) → publish → recruit (estimate → order → screen → reserve)
→ collect (replies arrive) → review (assign → decision → appeal) → analyze (overview,
trends, splits) → AI drafts (estimate → run → approve) → report (approve → export/share)
→ pay rewards (manual record) → billing/credits.

### Tester journey (NEW — does not exist in frontend today)

Signup → verify → complete profile (demographics: age, city, language, device, experience)
→ panel consent → language qualifications (optional, FR/AR) → tester dashboard:
available studies → apply/screen → booked sessions → take test (runner) → rewards track
→ attendance history → qualifications → notifications → account.
Testers never see workspaces, builder, reports, billing, or other testers' data.

## 2. Backend inspection verdict (per RESEARCH_PLATFORM.md idea)

Researcher APIs present (`backend/app/`): auth, privacy/files, studies (15 methods),
templates (23), recruiting (estimate/orders/screen/reserve/quotas/contacts), collection
(sessions/answers/events/submit/withdraw), reviews (assign/decision/appeal/rewards/journal),
analytics (snapshots/reports/exports/shares), AI (estimate/runs/approve), longitudinal
(slots/bookings/diary/recordings/drafts), evaluation (datasets/assignments/outcomes),
billing (plans/invoices/payments/credits/managed), collaboration (keys/comments/webhooks/
preferences), jobs, connected. Migration head `039_connected_workflows`.

Tester APIs present: `PUT/GET /panel/profile`, panel consent, language assessments +
qualifications + appeal (`assessment_router.py`), invitation/screen/reserve, collection
sessions, longitudinal bookings/diary, `GET /participant/history*` (workspaces, responses,
rewards, payments, attendance).

Tester gaps (backend): no browse/apply endpoint (researcher assigns; tester can't discover),
no tester dashboard aggregation, no tester-initiated booking cancel/reschedule for
recruiting orders (exists only for longitudinal), no reminder dispatch (bookings exist,
delivery doesn't), no quality-score/no-show visibility for the tester, no referral-code
source for Refer page, no `PATCH /workspaces/{id}` rename, no analytics overview/history
aggregation, no PDF export.

## 3. Implementation plan

### Phase A — Backend tester surface (new `app/tester/` module, prefix `/api/v1/tester`)

A1. `GET /tester/studies/available` — published studies with open quota the tester's
profile qualifies for (screeners not yet passed). Reuses recruiting TargetingVocabulary +
estimate logic. Response: `{ id, title, method, credits, minutes, languages }`.
A2. `POST /tester/studies/{id}/apply` — creates reservation via existing reserve service;
returns screener if required. Idempotent per tester+study.
A3. `GET /tester/sessions` — my collection sessions + longitudinal bookings merged,
newest first: `{ id, study_title, kind, status, scheduled_at, credits }`.
A4. `GET /tester/earnings` — my rewards + payouts from `recruiting/history.py` reshaped:
`{ total_credits, pending, paid, items[] }`.
A5. `GET /tester/profile` = existing `GET /panel/profile`; add `quality_score`,
`no_show_count`, `completed_count` (computed from attendance + responses).
A6. `POST /tester/bookings/{id}/cancel` — tester-initiated cancel (researcher flow exists
for longitudinal; extend to recruiting reservations).
A7. Referral code: `GET /tester/referral-code` → stable per-user code; Register accepts
`?ref=` and creates billing grant on first purchase (wires Refer page).
Migration `040_tester_surface` only if new columns needed (referral code, quality score);
else pure service/router layer, no schema change.

### Phase B — Backend researcher completions

B1. Analytics aggregation (`app/analytics/router.py`): `GET overview`, `GET replies-trend`,
`GET check-split`, `GET method-share`, `GET leaderboard`, `GET launches`, `GET review-queue`.
Read-only SQL/Python counts, small-group suppression, no AI numbers.
B2. History projection: `GET /workspaces/{id}/history?kind=&since=` + `GET /history/summary`
projecting studies/collection/reviews/reports/AI/billing events newest-first.
B3. `PATCH /workspaces/{workspace_id}` rename (owner/admin, name 1–100, audit logged).
B4. PDF export: `POST reports/{id}/exports` with `format=pdf` (server-rendered from approved
report; formula-escape rule already exists for CSV).
B5. Reminder dispatch: extend jobs runner with `longitudinal.reminder` + recruiting
booking reminders via existing notification preference + outbox pattern.
B6. Fix History PATCH misuse: frontend currently calls a lookup-shaped path; replace with
real `PATCH /workspaces/{id}/studies/{study_id}/state` once study ids are listed.

### Phase C — Frontend researcher (wire, keep layouts)

C1. Auth + profile + workspace context (DONE 2026-09-27, `lib/api.ts`, `WorkspaceContext`).
C2. StudyEditor page (MISSING): blocks editor per method key → `PUT version`
(`expected_revision`) → Validate (plain errors) → Publish → Preview capability
(`X-Preview-Token`, `/#preview=` stripped from URL).
C3. Dashboard/Analytics/History: swap mocks for B1/B2 endpoints (hooks + loading/empty/
error states). Delete `workspaceData.ts` when done.
C4. Recruit flow UI (MISSING): estimate → order → screen → reserve → quota progress
(`app/recruiting/router.py` already supports it).
C5. Runner preview for researcher (reuse tester Runner read-only).
C6. Reviews workbench (MISSING): queue → decision → adjudication → appeal.
C7. Report detail (MISSING): export (incl. PDF) + revocable shares.

### Phase D — Frontend tester (all NEW, separate shell)

D1. `src/components/tester/TesterShell.tsx` — own header (logo → `/tester`, no workspace
switcher), bottom help button, footer. Tester menu: Dashboard, My sessions, Earnings,
Profile, Notifications, Support, Log out. No researcher links anywhere.
D2. `src/pages/tester/Dashboard.tsx` — greeting + 3 cards (available studies, upcoming
session, earnings) + qualifications row. Empty states in plain language.
D3. `src/pages/tester/Studies.tsx` — available list (A1) → detail → Apply (A2) → screener
questions if required → booked confirmation.
D4. `src/pages/tester/Runner.tsx` — collection session UI: consent gate → per-block
renderer (survey/preference/five-second/prototype/media) → events batching → atomic
submit / withdraw. Same contract as researcher preview but writes real records.
D5. `src/pages/tester/Sessions.tsx` — upcoming + past (A3), cancel button (A6), join link
for interviews, diary occurrences with Start/Recover.
D6. `src/pages/tester/Earnings.tsx` — total/pending/paid + table (A4) + "Paid by hand"
copy + attendance history.
D7. `src/pages/tester/Profile.tsx` — demographics form (existing panel/profile API) +
qualifications list + quality score display (A5) + language assessment entry.
D8. Routes `/tester*` guarded: requires tester role + access token; researcher guard
redirects to `/dashboard`. Route-boundary test updated.
D9. AuthFlow: after signup with `role=tester`, redirect to `/tester` onboarding instead
of researcher dashboard.

### Phase E — Polish + acceptance

E1. UX copy pass on every new page (title → sentence → action, EN+FR).
E2. `pnpm test`, `tsc --noEmit`, `ruff check`, backend guarded suite
(`python -m app.test_runner`), `validate_blueprint.py`.
E3. Update `IMPLEMENTATION_STATUS.md`, `FRONTEND_AUDIT.md` (mark wired), this file
(mark phases done).

## 4. Order of work (do not skip)

A1–A4 (tester read APIs) → D1–D4 (tester shell + dashboard + apply + runner) →
B1 (analytics agg) → C3 (swap mocks) → A5–A7 → D5–D8 → B2–B5 → C2/C4/C6/C7 → E.

## 5. What stays out (explicit non-goals)

Auto money movement, cloud transcription, external sandbox connectors, live-provider
certification, public-production launch, OAuth/Google login, non-expiring-credit policy
(product decision, not code), design-tool integrations beyond webhooks/API keys.
