# Acceptance guide

## Start

Follow [the frontend README](../README.md), then open `/`. Use fictional information only.

The landing page, the authentication flow and the legal pages work with no backend. Workspace and tester screens call `/api/v1` through `apiFetch`, so without a reachable backend they render their empty state rather than a dashboard — check them against a running backend, or accept the empty state as the current result.

## Links and routes

The route table in [`src/lib/routes.ts`](../src/lib/routes.ts) is the single source of truth, and `src/lib/auth.test.ts` audits that every link under `src` resolves. Check it by hand after any navigation change.

| Area | Test | Expected result |
| --- | --- | --- |
| Legal | Follow Terms and Privacy from both the landing footer and the workspace shell | Both open `/legal/terms` and `/legal/privacy`, not the not-found page |
| Support | Follow the Support entry in the study order sidebar | It does not 404; the floating Help button opens the support centre |
| Legacy | Open `/login`, `/signup`, `/mfa`, `/auth/mfa`, `/auth/enroll-mfa`, `/studies/create`, `/study-preview`, `/terms`, `/privacy` | Each redirects to its canonical path |
| Unknown | Open a path not in the table | Not-found page, with a working route back into the app |
| Studio handoff | Walk builder → recruit → publish → preview | The study survives each step; an unnamed study travels without an empty `name=` |
| Share link | Copy a preview link from the study editor | The URL uses `/preview#preview=<token>` |

## Authentication

Each mode mounts `AuthFlow` under its own key, so a refresh or a shared link lands on the right step. `?role=researcher|tester` selects the space.

| Area | Test | Expected result |
| --- | --- | --- |
| Landing | Open `/`; follow the Sign in links | They open `/auth/login`, carrying the space's role |
| Sign-in | Submit empty fields, then a fictional email and nonempty password | First invalid input receives focus; valid values show demo success, without MFA |
| Signup | Open `/auth/signup`; submit optional display name, email and a 12-256-character password | Demo success links to verification; no account or email is created |
| Verification | Enter six digits, then a fictional 20-256-character code | Short code fails; complete code shows demo success; `?resend=1` opens the resend form |
| Recovery/reset | Follow `/auth/recover` to `/auth/reset-password`; try mismatched passwords | Confirmation mismatch fails; valid preview returns to login; no email sent |
| Legacy MFA | Open `/mfa`, `/auth/mfa`, `/auth/enroll-mfa` | Redirects to login; no fabricated authenticators or recovery codes |
| Invitation | Open `/auth/invitation`; validate a long fictional code | Separate from signup; success links onward |
| Role | Complete signup with `?role=tester` | The tester onboarding space opens, not the researcher dashboard |

Form fixtures: `?state=invalid`, `expired`, `server`, `rate-limited`, `offline`. These are UI scenarios only.

## Accessibility and language

Tab through links, forms and confirmation dialogs; check focus, Escape/cancellation and no overflow at 390px and 1440px. Switch EN/FR/AR; email and code inputs remain LTR.

## Validation

```sh
pnpm exec tsc -p tsconfig.app.json --noEmit
pnpm lint
pnpm test
pnpm build
```

The tests cover authentication validation, the route table's invariants, the link audit, landing copy and SEO. On the auth screens, confirm in the Network panel that no `/api/` request is made and no password or code enters a URL or browser storage.

These checks are not production authentication or accessibility certification. The auth flow is a simulation and all account values are synthetic. Use fictional information only.