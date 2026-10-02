# Elseview frontend

React 19, TypeScript, Vite, Tailwind CSS and shadcn/ui. Holds the landing page, the authentication flow, and two separate product spaces: the **researcher** workspace and the **tester** space.

See the [repository README](../README.md) for what Elseview is and where the product stands.

> **Status:** this is an interactive preview. The landing page and auth flow are complete; workspace and tester screens render demonstration data, and the auth flow does not establish identity. Use fictional information only.

Every path lives in [`src/lib/routes.ts`](src/lib/routes.ts). No component writes a path literal — they import the table and use `withQuery`/`authRoute` to attach query parameters. Adding or renaming a route is a one-line change there, and `src/lib/auth.test.ts` fails if a route stops being served or a link loses its destination.

## Run locally

```sh
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host localhost --port 8080 --strictPort
```

Use Node.js 24 and pnpm. Open the URL printed by Vite and visit `/` for the landing page.

Workspace and tester screens call the backend through `apiFetch` (`src/lib/api.ts`) against `/api/v1`. Without a reachable backend those pages render their empty state; the landing page, the auth flow and the legal pages work standalone.

## Routes

**Landing and legal**

| Path | Screen |
| --- | --- |
| `/` | Landing page |
| `/legal/terms`, `/legal/privacy` | Legal copy (placeholders — the policies are not published yet) |

**Authentication** — each mode mounts `AuthFlow` under its own key, so a refresh or a shared link lands on the right step. `?role=researcher|tester` selects the space the account belongs to.

| Path | Screen |
| --- | --- |
| `/auth/login` | Sign in |
| `/auth/signup` | Register; no invitation required |
| `/auth/verify-email` | Enter the email code; `?resend=1` opens the resend form |
| `/auth/recover`, `/auth/reset-password` | Request instructions, then set a new password |
| `/auth/invitation` | Workspace invitation code, separate from registration |
| `/auth/complete-profile` | Profile completion; includes Log out |

**Researcher workspace**

| Path | Screen |
| --- | --- |
| `/dashboard` | Home: test templates, results at a glance |
| `/studies/new`, `/studies/:studyId/edit` | Study builder |
| `/recruit`, `/publish` | Recruitment and publishing steps |
| `/reviews`, `/reports/:reportId` | Report queue and one report |
| `/preview` | Participant-facing runner preview |
| `/analytics`, `/history` | Results and past work |
| `/account`, `/account/notifications`, `/account/refer` | Profile, notifications, referral |
| `/settings`, `/workspace/billing`, `/workspace/credits`, `/workspace/credits/buy` | Settings, billing, credits |

The builder passes a study between steps as a query string. `studyQuery` returns params, not a pre-built string, so `withQuery` owns encoding and an unnamed study travels without an empty `name=`.

**Tester space** — a tester must never reach a researcher page that manages studies, credits, reports or billing. All `/tester/*` pages currently render fixture data.

`/tester`, `/tester/onboarding`, `/tester/studies`, `/tester/runner`, `/tester/sessions`, `/tester/history`, `/tester/notifications`, `/tester/earnings`, `/tester/profile`

**Legacy aliases** — an old bookmark or shared link redirects instead of hitting the not-found page: `/login`, `/signup`, `/mfa`, `/auth/mfa`, `/auth/enroll-mfa`, `/studies/create`, `/study-preview`, `/terms`, `/privacy`.

Anything else renders `NotFound`.

## Verify

```sh
pnpm exec tsc -p tsconfig.app.json --noEmit
pnpm lint
pnpm test
pnpm build
pnpm preview --host localhost
```

The tests cover authentication validation, the route table and its invariants, an audit that every link in `src` resolves to a real route, landing copy and SEO. See [the local testing guide](docs/local-testing.md) for browser checks.

## Preview boundaries

The authentication flow is a UI simulation: it does not establish identity, verify codes, send email, or call an API. Use fictional information and demo passwords only. Actual authorization, token transport, email delivery and durable account lifecycle remain integration work.