# Elseview — Frontend Audit: done vs remaining (with build prompts)

UX writing rule for every page: short title (≤6 words) → 1 plain sentence → 1 primary action.
Plain words, no jargon. EN + FR via `useAuthLocale`. Errors say what happened + the one fix.
Backend base: `/api/v1`. Auth: bearer in memory, refresh cookie, `Origin` + `X-CSRF-Token`.

Legend: DONE = UI complete · MOCK = UI complete, fake data · WIRED = calls real backend · MISSING = not built.

## 1. Landing `/` — `src/pages/Index.tsx` — DONE (static)

Done: hero, logos, testimonials, FAQ, footer, SEO.
Remaining: role dialog routes to real auth; pricing CTA → `/workspace/credits/buy`; remove Mediterra leftovers if any.
Prompt: `Audit src/pages/Index.tsx CTAs. Keep design. Point researcher CTA to /auth/signup?role=researcher, tester CTA to /auth/signup?role=tester, pricing CTA to /workspace/credits/buy. Verify pnpm build.`

## 2. Auth — `src/pages/auth/AuthFlow.tsx` — MOCK (preview-only, no fetch)

Done: 6 modes, validation, offline/rate-limit states, plain copy.
Remaining — wire `backend/app/auth/router.py`:
- signup → `POST /auth/register` → go verify; verify → `POST /auth/verify-email`; resend → `POST /auth/verification/request`
- login → `POST /auth/login` (store access token via `src/lib/api.ts setAccessToken`, refresh stays cookie); logout → `POST /auth/logout`
- recover → `POST /auth/password-reset/request` (generic message always); reset → `POST /auth/password-reset/confirm`
- invitation → login first, then `POST /workspace-invitations/accept`; Google buttons → hide until OAuth exists (backend has none)
Prompt: `Wire AuthFlow modes to real endpoints using src/lib/api.ts apiFetch. Bearer in memory only, credentials:include. Keep validation + plain EN/FR copy. Generic recovery message. Remove preview-done fake path. Run tsc + pnpm test.`

## 3. Complete profile — `src/pages/auth/CompleteProfile.tsx` — MOCK

Done: full form, phone validation, tips carousel.
Remaining: after verify, `GET /me`, then `POST /workspaces` (creates workspace); keep extra fields local (no BE profile API). Redirect `/dashboard?role=&welcome=1&firstName=`.
Prompt: `After validation call GET /me then POST /workspaces with first workspace name. Keep phone/company/role local. Preserve tips UX. tsc + test.`

## 4. Dashboard `/dashboard` — `Dashboard.tsx` — MOCK (wired nav only)

Done: 8 test-type cards remapped to backend keys, hero, New study/Find people/Analytics/History buttons route correctly.
Remaining: live counts (studies live/draft, replies, to-check) from new `GET /analytics/overview` (see §5 of SYNC file); study list preview from `GET /workspaces/{id}/studies`.
Prompt: `Add useEffect loading overview + study list with loading/empty/error states in plain language. Keep cards + hero design. tsc + test.`

## 5. New study `/studies/new` — `NewStudy.tsx` + `src/lib/api.ts` + `src/lib/methods.ts` — PARTIAL (catalog live, create needs workspaceId)

Done: 3 steps, `GET /research-methods`, `GET /templates`, `POST /studies` / template instantiate with idempotency.
Remaining: pass real `workspaceId` (from workspace context, not URL); then version editor (`PUT .../versions/{id}` + `expected_revision`), `POST validate`, `POST publish`, `POST preview` → `/#preview=` capability with `X-Preview-Token`.
Prompt: `Add workspace context provider (GET /workspaces, selected id). Build StudyEditor page: blocks list per method key, PUT version with expected_revision, Validate button showing errors plainly, Publish button, Preview button opening /#preview= token stripped from URL.`

## 6. Analytics `/analytics` — `Analytics.tsx` — MOCK (spec for backend)

Done: full layout (KPIs, trend, split, method share, leaderboard, launches, review queue, reports, AI ops).
Remaining — backend must add (`app/analytics/router.py`): `GET overview`, `GET replies-trend`, `GET check-split`, `GET method-share`, `GET leaderboard`, `GET launches`, `GET review-queue`. Then swap `workspaceData.ts` for fetch.
Prompt (backend): `Add 7 read-only aggregation endpoints under /workspaces/{id}/analytics returning exactly the shapes Analytics.tsx renders. Deterministic SQL/Python counts, small-group suppression, no AI numbers.`
Prompt (frontend): `Replace workspaceData imports with apiFetch hooks + loading/empty/error states. Delete mock file when done.`

## 7. History `/history` — `History.tsx` — MOCK (spec for backend)

Done: KPIs, charts, lifecycle table (backend wording), filterable log.
Remaining — backend: `GET /workspaces/{id}/history?kind=&since=` + `GET /history/summary` projecting studies/collection/reviews/reports/AI/billing events. Frontend: swap mocks; lifecycle actions call `PATCH /studies/{id}/state`.
Prompt: `Build history projection endpoint newest-first; wire History.tsx filters to ?kind=. Add pause/resume/close buttons per study row with confirm copy.`

## 8. Billing `/workspace/billing` — `Billing.tsx` — MOCK

Done: layout, workspace info, billing info, invoice list UI.
Remaining — `app/billing/router.py`: `GET plans/subscriptions/invoices/payments/usage`, `POST subscriptions` (Team upgrade), invoice payments/credit/reverse (manual records). Team-plan button → subscribe flow.
Prompt: `Wire Billing.tsx to billing endpoints. Team button opens confirm modal then POST /subscriptions. Manual-payment copy: "Paid by hand — record only."`

## 9. Credits `/workspace/credits` + Buy `/workspace/credits/buy` — MOCK

Done: wallet card, tiers, FAQs (plain copy), calculator.
Remaining: `GET /credits`, `POST /credits/estimate`, `POST /credits` (idempotent), `GET quotas`; checkout → `POST /invoices/{id}/payments` manual record; history list → real transactions.
Prompt: `Wire estimate on input debounce, purchase on checkout with idempotency key, receipt state, transaction history table with empty state.`

## 10. Settings `/settings` — `Settings.tsx` — MOCK

Done: rename w/ validation, team upgrade upsell, delete-confirm modal.
Remaining: `GET /workspaces/{id}/members`, invite (`POST .../invitations`), role change, remove, `GET audit`; rename needs new BE `PATCH /workspaces/{id}`; delete workspace → confirm with backend delete/hold API (check privacy holds first).
Prompt: `Add members table + invite modal + audit list. Rename calls PATCH when backend lands (fallback: disabled with "coming soon" hint). Delete checks privacy holds.`

## 11. Account `/account` — `Account.tsx` — MOCK + local password modal

Done: personal-details form, workspaces table, change-password modal, delete section.
Remaining: `GET /me` prefill; save → profile endpoint (new, or local until then); sessions revoke `DELETE /me/login-sessions/{id}`; change password → reset-confirm or new endpoint; delete → privacy-ops erasure flow with plain consequences copy.
Prompt: `Prefill from GET /me. Add login-sessions list with Revoke buttons. Wire change-password + delete to backend with confirm modals.`

## 12. Notifications `/account/notifications` — `Notifications.tsx` — MOCK

Done: layout per screenshot, dark-blue toggles.
Remaining: collaboration `PUT /workspaces/{id}/collaboration/preference` + `GET preference`; marketing/account toggles persist; system row static.
Prompt: `Persist toggles via preference API with optimistic UI + rollback error "Could not save. Try again."`

## 13. Refer `/account/refer` — `Refer.tsx` — MOCK

Done: dark gradient hero + dots, earnings, workspace select, invite, personal link, share.
Remaining: send → recruiting invitation `POST`; earnings → `GET billing/grants`; link → real referral code from backend.
Prompt: `Wire Send to recruiting invitation endpoint; show "Invite sent" state. Earnings from grants API. Copy-link fallback kept.`

## 14. Support panel + menus + shell — DONE (functional, no API)

Done: `SupportCenter` side panel opens from help button + Support menu row; user menu (Account/Notifications/Refer/Support/Log out); logo → `/dashboard`.
Remaining: guides/FAQs links → real docs URLs; live chat/contact → backend or mailto fallback (already mailto in auth).
Prompt: `Point Guides/FAQ/Feature-request rows to real URLs. Keep panel behavior.`

## 15. Missing pages (backend exists, frontend does not)

- Participant runner (collection sessions/answers/events/submit/withdraw) — new `src/pages/participant/Runner.tsx`.
- Reviewer workbench (cases/assign/decision/appeal) — new `src/pages/workspace/Reviews.tsx`.
- Reports detail + share (analytics reports/exports/shares) — extend Analytics or new `Report.tsx`.
- Interview/diary schedule + eval workbench (longitudinal/evaluation) — P3.
- Template gallery — fold into NewStudy step 2 (done minimal) or dedicated page.
Prompt: `Build Runner first: consent → questions per block type → events batching → atomic submit/withdraw. Then Reviews queue. Then Report detail with export/share.`

## Coverage matrix

| Area | Backend | Frontend | Direction |
|---|---|---|---|
| Auth/workspaces | done | mock | BE→FE |
| Studies/methods/templates | done | partial (NewStudy, no editor) | BE→FE |
| Recruit/collect | done | missing | BE→FE |
| Reviews/rewards | done | missing | BE→FE |
| Analytics aggregations | missing | done (spec) | FE→BE |
| History log | missing | done (spec) | FE→BE |
| Billing/credits | done | mock | wire |
| Longitudinal/eval | done | missing | BE→FE (P3) |
| Collaboration prefs | done | mock toggles | wire |
| Jobs/connected | done | missing | P3 |
