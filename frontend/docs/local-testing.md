# Landing and authentication acceptance guide

## Start

Follow [the frontend README](../README.md), then open `/`. Use fictional information only. No backend is required; all authentication is simulated.

## Browser checks

Check the retained pages at desktop and mobile widths.

| Area | Test | Expected result |
| --- | --- | --- |
| Landing | Open `/`; follow both Sign in links | Both open `/auth/login`; section links have valid targets |
| Sign-in | Submit empty fields, then a fictional email and nonempty password | First invalid input receives focus; valid values show demo success and account-preview navigation, without MFA |
| Signup | Open `/auth/signup` without a token; submit optional display name, email and a 12-256-character password | Demo success links to verification; no account or email is created |
| Verification | Enter six digits, then a fictional 20-256-character code | Short code fails; complete code shows demo success; resend requests validate email |
| Recovery/reset | Follow `/auth/recover` to `/auth/reset-password`; try mismatched passwords | Confirmation mismatch fails; valid preview returns to login; no email sent |
| Legacy MFA | Open `/mfa`, `/auth/mfa`, `/auth/enroll-mfa` | Redirects to login; no fabricated authenticators or recovery codes |
| Invitation | Open `/auth/invitation`; validate a long fictional code | Separate from signup; success links to workspace preview |
| Account | Open `/auth/account` | Synthetic read-only identity; navigation to workspace, sessions, recovery, invitations and deletion |
| Workspace | Create/cancel/select a workspace; reload | Changes exist only in the current preview; no dashboard or persistence |
| Sessions | Cancel then confirm revocation | Only the local list changes; no device/location data is fabricated |
| Deletion | Enter current password and `ERASE MY ACCOUNT`; cancel then confirm | Second confirmation required; outcome explicitly says no real account was deleted |
| Session status | Open `/auth/session?state=restoring`, `offline`, or `expired` | Loading ends; a working sign-in recovery link remains |
| Language | Switch between English, French and Arabic | Existing localized auth controls and text direction remain usable |
| Home | Follow Home from each auth screen | Returns to `/` |

## Removed routes

Confirm `/app`, `/app/overview`, `/bridge/inbox`, `/bridge/cases/demo`, `/care/schedule`, `/pulse/reports`, `/gov/audit`, and `/administration/profile` show not-found. `/auth/workspaces` is only an auth-adjacent preview, not the former healthcare workspace.

Form fixtures: `?state=invalid`, `expired`, `server`, `rate-limited`, `offline`. Lists: `?state=empty`. Deletion blockers: `?state=held`, `last-owner`, `financial`. These are UI scenarios only. Watch Network: no `/api/` traffic or form POSTs. Passwords/codes must not enter URLs or browser storage.

## Validation

Run `pnpm exec tsc -p tsconfig.app.json --noEmit`, `pnpm lint`, `pnpm test`, and `pnpm build`.

Tab through links/forms and confirmation dialogs; check focus, Escape/cancellation and no overflow at 390px and 1440px. Switch EN/FR/AR; email/code inputs remain LTR. Tests cover auth field bounds, route boundaries, no API/persistence in active previews, landing copy and SEO.

These checks are not production authentication or accessibility certification. The active UI uses no authenticated session flag, and all account values are synthetic. Use fictional information only.
