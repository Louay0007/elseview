# Elseview frontend

React 19, TypeScript, Vite, Tailwind CSS and shadcn/ui. The frontend contains the landing page and backend-aligned authentication/account previews. No authentication API is connected. Research dashboards and administrative product pages are not implemented.

## Run locally

From the repository root:

```sh
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host localhost --port 8080 --strictPort
```

Use Node.js 24 and pnpm. Open the URL printed by Vite. Visit `/` for the landing page or `/auth/login` for sign-in.

No frontend environment file, database, Docker service, backend process, or credentials are required. Use only fictional information and demo passwords.

## Available routes

- `/`: landing page.
- `/auth/login` and `/login`: email/password sign-in preview.
- `/auth/signup` and `/signup`: optional display name, email and password; no invitation required.
- `/auth/verify-email`: full email code; `?resend=1` opens the resend form. Completion continues to `/auth/complete-profile`.
- `/auth/complete-profile`: profile completion preview (memory-only, `?role=researcher|tester`); includes Log out.
- `/auth/recover`, `/auth/reset-password`: request instructions and enter a reset code/new password.
- `/auth/invitation`: workspace invitation code, separate from registration.
- `/auth/account`: synthetic read-only identity and account navigation.
- `/auth/workspaces`: choose/create a local workspace preview; `?state=empty` shows first use.
- `/auth/sessions`: synthetic session references/expiry dates and confirmed local revocation; `?state=empty` shows the empty state.
- `/auth/delete-account`: current password, exact confirmation phrase and confirmation dialog. `?state=held`, `last-owner` or `financial` preview blockers.
- `/auth/session`: expired by default; `?state=restoring` shows bounded loading, `?state=offline` shows recovery.
- Legacy `/mfa`, `/auth/mfa` and `/auth/enroll-mfa` redirect to login; the backend does not implement authenticator enrollment.

Sign-in completion leads to an explicit account preview, never a production session. Forms/list mutations are memory-only and reset after reload/navigation. `/app/*` remains unavailable. EN/FR/AR and RTL are supported; only language preference is stored locally. Auth forms support `?state=invalid`, `expired`, `server`, `rate-limited` and `offline` for design review after submission; these are presentation fixtures, not backend decisions.

## Verify

```sh
pnpm exec tsc -p tsconfig.app.json --noEmit
pnpm lint
pnpm test
pnpm build
pnpm preview --host localhost
```

The tests cover authentication validation, route boundaries, landing copy and SEO. See [the local testing guide](docs/local-testing.md) for browser checks. The old workspace design plan is historical, not the current frontend specification.

## Preview boundaries

Authentication, invitations, recovery, profile completion, workspace creation, revocation and deletion are UI simulations. They do not establish identity, verify codes, send email, mutate server records or call APIs. The active routes no longer use the legacy browser-local authenticated flag. Use fictional information only. Actual authorization, token transport, email delivery and durable account lifecycle remain integration work.
