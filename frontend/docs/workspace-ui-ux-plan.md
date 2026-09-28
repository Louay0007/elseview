# Mediterra. — Workspace UI/UX Plan (UI ONLY, no API)

> **Scope:** static workspace UI built on the CURRENT frontend design system.
> No API calls, no real auth, no backend, no PHI. All data = typed mocks in `src/mocks/`.
> Backend reference: `Mediterra-Backend-Implementation-Prompts.md` — Phase A (Prompts 00–03) + Phase B (Prompts 04–10).
> Frontend source of truth: `src/components/ui/*` (shadcn), `tailwind.config.ts`, `src/globals.css`, `AI_RULES.md`.

---

## 0. What this document is

1. The full **route map** for the authenticated workspace.
2. **Page-by-page breakdown**: layout grid, sections, components, mock states.
3. **Mock data types** mirroring backend Prompts 02–10 field-for-field (names kept identical so API wiring later is 1:1).
4. **Build phases** ordered so each phase is independently viewable in the browser.
5. Exact **file tree** to create + acceptance criteria.

### Non-goals (explicitly OUT)

- No `fetch`, no react-query queries, no OIDC, no Keycloak, no Prisma.
- No real patient data — mocks use obviously fake names (`Amira Ben Salah (mock)`).
- No writes that pretend to persist — every mutating button shows a mock `toast` ("Mock only — no API").
- `MediterraHeader` (marketing) untouched. Workspace uses its own `WorkspaceShell`.

---

## 1. Design system — what MUST be reused (no new visual language)

### 1.1 Tokens (`src/globals.css` + `tailwind.config.ts`)

| Token | Value | Usage in workspace |
|---|---|---|
| `signal-blue` | `#0a84ff` | primary actions, active nav, links, focus ring |
| `deep-dusk` | `#001b45` | sidebar dark variant, auth accents |
| `carbon` | `#1d1d1f` | headings, body text |
| `steel` / `fog` | `#6e6e73` / `#8e8e93` | secondary / muted text |
| `frost` | `#f5f9ff` | page tinted sections, hover bg |
| `vapor` | `#f2f2f7` | page canvas alt, skeleton base |
| `neon` | `#30d158` | "active / healthy / verified" dots only |
| destructive | `hsl(3 100% 59%)` | break-glass, revocations, destructive confirm |
| font | SF Pro Display stack, `letter-spacing: -0.015em` | everything |
| headings | `tracking-[-0.045em]`, semibold/bold | page title 28–40px, section 21px, body 15–17px |
| radius | cards `22px`, inputs `14px`, buttons/sections pills `9999px` | `rounded-card`, `rounded-[14px]`, `rounded-full` |
| container | `bluecrest-container` (max 1200px) | all workspace content |
| focus | `bluecrest-focus` | every interactive element |
| glass | `.liquid-glass` | topbar + stat cards over tinted bg only |

### 1.2 Component allowlist (import from `@/components/ui/*`, NEVER rebuild)

`button`, `card`, `badge`, `avatar`, `tabs`, `table`, `dialog`, `alert-dialog`, `sheet`, `dropdown-menu`, `select`, `input`, `textarea`, `label`, `checkbox`, `radio-group`, `switch`, `calendar`, `popover`, `command`, `breadcrumb`, `pagination`, `progress`, `separator`, `accordion`, `collapsible`, `scroll-area`, `resizable`, `sidebar` (primitives), `skeleton`, `sonner` (toasts), `tooltip`, `form` (with react-hook-form+zod for validation visuals only).

### 1.3 Workspace-specific primitives to create (in `src/components/workspace/`)

| Primitive | Built from | Purpose |
|---|---|---|
| `WorkspaceShell` | `sidebar` primitives + divs | app frame: sidebar + topbar + `<Outlet/>` |
| `WorkspaceSidebar` | sidebar primitives, `badge` | nav grouped per §3, role-filtered (mock) |
| `WorkspaceTopbar` | `input` (command-k visual), `avatar`, `dropdown-menu` | search, tenant switcher, role switcher, session |
| `PageHeader` | divs + `breadcrumb` + `button` | title + description + actions, same on every page |
| `StatCard` | `card` | KPI number + delta + sparkline slot |
| `StatusBadge` | `badge` | ONE mapping per domain, see §5 |
| `DataTable` | `table` + `pagination` + `skeleton` | all lists, identical toolbar pattern |
| `DetailDrawer` | `sheet` | read-only detail for any row (patient, task, doc…) |
| `EmptyState` | divs + lucide icon | identical empty pattern everywhere |
| `MockBanner` | `alert` | top of every workspace page: "UI preview — mock data, no API" |

### 1.4 Status → badge color contract (apply WITHOUT exception)

| Status family | Badge variant | Examples |
|---|---|---|
| healthy / active / verified / ready / completed | `default` (blue) + neon dot | tenant active, device current, doc ready, task completed |
| pending / in-review / processing / scheduled | `secondary` | readiness item pending, duplicate candidate, OCR processing |
| paused / snoozed / deferred / expired-soon | `outline` | SLA paused, delegation expiring |
| blocked / breached / infected / revoked / denied | `destructive` | SLA breached, malware infected, grant revoked |
| restricted / break-glass / legal-hold | destructive `outline` + lock icon | restricted patient, emergency session, legal hold |

---

## 2. Global IA — workspaces (matches existing `/bridge /care /pulse /gov /administration`)

```
MARKETING (existing, untouched)
  /                     → Index (marketing)
/login /signup /mfa …   → existing auth pages (untouched)

WORKSPACE (new — all inside <WorkspaceShell>, all <ProtectedRoute>)
  /app                              → redirect to role home (mock): clinician→/care, ops→/bridge…
  /app/overview                     → cross-workspace home (tasks, SLAs, alerts, activity)

  /bridge                           → Bridge layout (case review domain — shell only in this plan)
  /bridge/inbox                     → review queue
  /bridge/cases/:id                 → case detail (drawer-based, read-only)

  /care                             → Care layout
  /care/schedule                    → Care schedule board  (Prompt 10 care.schedule/delivery)
  /care/monitoring                  → monitoring list (uses Patient + ConsentGrant read-only chips)

  /pulse                            → Pulse layout (reports/forecast surface, Prompt 03 reports.generate/ai.forecast)
  /pulse/reports                    → report list + run detail (mock)

  /gov                              → Gov layout (oversight)
  /gov/access-reviews               → periodic access review queue (Prompt 06)
  /gov/emergency-access             → break-glass sessions + reviews (Prompt 06)
  /gov/privacy-requests             → PrivacyRequest pipeline (Prompt 08)
  /gov/retention                    → RetentionClock + LegalHold + DestructionJob (Prompt 08)
  /gov/audit                        → audit.outbox_event + processed_event explorer (Prompt 02, read-only)

  /administration                   → Administration layout (platform admin)
  /administration/tenants           → Tenant + TenantPolicy list + detail tabs
  /administration/organizations     → Organization tree + relationships
  /administration/facilities        → Facility + Department hierarchy
  /administration/readiness         → ReadinessChecklist go-live gates
  /administration/roles             → RoleDefinition + PermissionDefinition matrix
  /administration/memberships       → memberships + invitations + delegations
  /administration/patients          → Patient directory + duplicates queue + merge review
  /administration/consents          → Consent templates + grants + withdrawals
  /administration/documents         → Document pipeline board (quarantine→ready)
  /administration/tasks             → Task queues + SLA instances + escalations
  /administration/notifications     → Notification center + templates + quiet hours
  /administration/messaging         → MessageThread list + thread view (read-only)
  /administration/integration       → imports/exports + dead-letter replay (mock)
  /administration/health            → liveness/readiness, queues, scheduler, metrics (Prompt 03)
  /administration/profile           → UserProfile + ContactPoint + devices + sessions
```

**Routing rules:**
- Keep ALL routes in `src/App.tsx` (per `AI_RULES.md`).
- Workspace routes nest under `path="/app"`, `"/bridge"`, `"/care"`, `"/pulse"`, `"/gov"`, `"/administration"` elements that render `<WorkspaceShell area=…>` + `<Outlet/>`.
- `WorkspaceLanding` (current placeholder) is REPLACED by real layout pages; delete after Phase 1.
- `NotFound` stays catch-all.
- Auth pages untouched.

---

## 3. WorkspaceShell — the frame every workspace page lives in

```
┌────────────────────────────────────────────────────────┐
│ Topbar: [☰] [⌕ Search ⌘K]  [Tenant▾] [Role▾] [🔔3] [Avatar▾] │
├──────────┬─────────────────────────────────────────────┤
│ Sidebar  │ Breadcrumb: Workspace / Section / Detail    │
│          │ PageHeader: Title + description + actions   │
│  OVERVIEW│ ┌─────────────────────────────────────────┐ │
│  - Home  │ │            PAGE CONTENT                 │ │
│  CARE    │ │                                         │ │
│  - Sched │ └─────────────────────────────────────────┘ │
│  - Monit │                                             │
│  GOVERN  │  MockBanner sits under PageHeader on every  │
│  …       │  page until API wiring phase.               │
│  ──────  │                                             │
│  Session │                                             │
└──────────┴─────────────────────────────────────────────┘
```

- **Sidebar groups** (collapsible, lucide icons): Overview · Review (Bridge) · Care · Pulse · Governance · Administration · Platform (health, integration) · Session (profile, workspaces, sign out).
- **Role switcher (mock):** dropdown lists the 13 backend roles (clinician, diaspora specialist, nurse, coordinator, pharmacist, operations manager, credential reviewer, program administrator, auditor, privacy officer, security officer, analyst, tenant admin). Switching ONLY hides/shows nav items + action buttons per the visibility matrix in §6 — purely visual, stored in `localStorage`.
- **Tenant switcher (mock):** 3 tenants (Academic Medical Center / Regional Clinic Network / Sandbox). Switching swaps ALL mock tables (each mock row carries `tenantId`).
- **Topbar search:** `command` palette visual over mock index (patients by initials only, tasks, documents by filename). `⌘K` opens, `esc` closes. No real search logic beyond `includes()` filter.
- **Responsive:** `<1024px` sidebar → `sheet` drawer; tables → card lists (same data, `block md:table` pattern); PageHeader actions collapse into `dropdown-menu`.

---

## 4. Mock data layer — mirrors backend Prompts 02–10 EXACTLY

> Location: `src/mocks/` — one file per prompt. Types use backend names verbatim.
> Every list returns `{ data, total }` with cursor-style pagination visuals. No fetch, no axios.

### 4.1 Prompt 02 — kernel (`src/mocks/kernel.ts`)

```ts
type TenantStatus = "active" | "suspended" | "sandbox";
interface Tenant { id: string; code: string; name: string; status: TenantStatus; region: string; defaultLanguage: "en"|"fr"|"ar"; timezone: string; residencyPolicy: string; createdAt: string; updatedAt: string; }
interface FeatureFlag { scope: "platform"|"tenant"|"user"; key: string; value: string; owner: string; reason: string; expiresAt: string | null; }
type OutboxState = "pending"|"dispatched"|"failed"|"dead-letter";
interface OutboxEvent { id: string; version: number; aggregate: string; aggregateId: string; tenantId: string; actorId: string; correlationId: string; causationId: string | null; payloadRef: string; classification: "public"|"internal"|"restricted"; state: OutboxState; attempts: number; createdAt: string; }
interface ProcessedEvent { consumer: string; eventId: string; processedAt: string; }
interface IdempotencyRecord { tenantId: string; actorId: string; route: string; key: string; requestHash: string; resultRef: string; expiresAt: string; }
```

UI surfaces: `/gov/audit` (outbox explorer), `/administration/health` (consumer lag), idempotency shown as a read-only chip on task/document detail drawers ("Idempotency-Key: …").

### 4.2 Prompt 04 — identity (`src/mocks/identity.ts`)

```ts
type UserStatus = "invited"|"active"|"suspended"|"deactivated";
interface User { id: string; externalSubject: string; status: UserStatus; activatedAt: string | null; deactivatedAt: string | null; }
interface UserProfile { userId: string; legalName: string; displayName: string; timezone: string; preferredLanguage: "en"|"fr"|"ar"; accessibility: { reducedMotion: boolean; largeText: boolean; screenReader: boolean }; }
interface ContactPoint { id: string; userId: string; kind: "email"|"phone"; valueMasked: string; verified: boolean; verifiedAt: string | null; primary: boolean; }
interface UserDevice { id: string; userId: string; label: string; firstSeenAt: string; lastSeenAt: string; revokedAt: string | null; current: boolean; }
type AuthEventType = "login"|"logout"|"mfa-challenge"|"step-up"|"session-revoked"|"suspended-blocked";
interface AuthenticationEvent { id: string; userId: string; type: AuthEventType; outcome: "success"|"failure"; risk: "low"|"medium"|"high"; createdAt: string; }
```

UI surfaces: `/administration/profile`, `/administration/memberships` (invite/approve/suspend/terminate as mock dialogs), session list with revoke buttons, MFA policy card per role, step-up banner on `/gov/emergency-access` + export buttons.

### 4.3 Prompt 05 — org hierarchy (`src/mocks/organization.ts`)

```ts
interface TenantPolicy { tenantId: string; rule: string; value: string; }
type OrgType = "hospital"|"clinic"|"network"|"ministry"|"insurer"|"donor"|"diaspora-association"|"research";
interface Organization { id: string; tenantId: string; parentId: string | null; type: OrgType; name: string; status: "active"|"suspended"; }
interface OrganizationRelationship { id: string; fromOrgId: string; toOrgId: string; agreement: string; purpose: string; effectiveFrom: string; effectiveTo: string | null; capabilities: string[]; }
interface Facility { id: string; orgId: string; name: string; kind: string; region: string; address: string; timezone: string; status: "active"|"inactive"; emergencyInstructions: string; }
interface Department { id: string; facilityId: string; parentId: string | null; code: string; specialty: string; status: "active"|"inactive"; }
interface ServiceCapability { id: string; facilityId: string; capability: string; verified: boolean; availability: string; verifiedAt: string | null; }
interface ReadinessItem { id: string; checklistId: string; owner: string; label: string; status: "pending"|"approved"|"blocked"; evidenceRef: string | null; }
interface ReadinessChecklist { id: string; tenantId: string; gate: "clinical"|"security"|"legal"|"integration"; status: "pending"|"ready"|"blocked"; items: ReadinessItem[]; }
```

UI surfaces: `/administration/tenants`, `/organizations`, `/facilities` (tree + tabs), `/readiness` (gate cards with progress).

### 4.4 Prompt 06 — access (`src/mocks/access.ts`)

```ts
interface Membership { id: string; userId: string; scope: "tenant"|"organization"|"facility"|"department"; scopeId: string; status: "invited"|"active"|"suspended"|"terminated"; }
interface RoleDefinition { id: string; key: string; label: string; }
interface PermissionDefinition { id: string; key: string; label: string; sensitivity: "standard"|"sensitive"|"restricted"; }
interface RoleAssignment { id: string; membershipId: string; roleId: string; scope: string; expiresAt: string | null; }
interface TemporaryAccessGrant { id: string; userId: string; roleId: string; reason: string; startsAt: string; endsAt: string; status: "active"|"expired"|"revoked"; }
interface CoverageDelegation { id: string; fromUserId: string; toUserId: string; scope: string; startsAt: string; endsAt: string; status: "active"|"ended"; }
interface EmergencyAccessSession { id: string; userId: string; reason: string; startedAt: string; endsAt: string; status: "active"|"closed"; stepUp: boolean; }
interface EmergencyAccessReview { id: string; sessionId: string; reviewerId: string; decision: "approved"|"rejected"|"pending"; note: string; }
```

The 13 roles from the prompt are the mock `RoleDefinition` rows. UI surfaces: `/administration/roles` (permission matrix table, roles × permissions with dots), `/administration/memberships`, `/gov/access-reviews`, `/gov/emergency-access` (break-glass dialog: reason + duration + step-up checkbox → mock audit toast).

### 4.5 Prompt 07 — patients (`src/mocks/patients.ts`)

```ts
type PatientStatus = "active"|"temporary"|"unknown"|"archived";
interface Patient { id: string; tenantId: string; status: PatientStatus; restricted: boolean; source: string; initials: string; language: string; }
interface PatientIdentifier { id: string; patientId: string; system: string; kind: "local"|"national"|"temporary"; valueMasked: string; issuer: string; activeFrom: string; activeTo: string | null; }
interface DuplicateCandidate { id: string; patientAId: string; patientBId: string; score: number; reasons: string[]; status: "pending"|"linked"|"rejected"|"deferred"|"merged"; }
interface MergeOperation { id: string; candidateId: string; action: "link"|"reject"|"defer"|"merge"|"reverse"; actorId: string; createdAt: string; reversible: boolean; }
interface CaregiverAuthorization { id: string; patientId: string; caregiverName: string; actions: string[]; dataCategories: string[]; startsAt: string; expiresAt: string | null; status: "active"|"revoked"|"expired"; }
```

UI surfaces: `/administration/patients` — directory table (initials only, NEVER full names in lists), detail drawer tabs (Identifiers / Relationships / Caregivers / Consent chips), duplicates queue with score bars + human-action buttons (Link / Reject / Defer / Merge / Reverse — each opens confirm dialog → mock toast).

### 4.6 Prompt 08 — consent & privacy (`src/mocks/consent.ts`)

```ts
type Purpose = "bridge-review"|"cross-border-sharing"|"care-monitoring"|"caregiver-access"|"outcome-followup"|"quality"|"research";
interface ConsentTemplate { id: string; title: string; status: "draft"|"published"|"retired"; version: number; languages: string[]; }
interface ConsentGrant { id: string; patientId: string; templateId: string; version: number; purposes: Purpose[]; categories: string[]; recipients: string[]; territories: string[]; method: "written"|"electronic"|"spoken-approved"; startsAt: string; expiresAt: string | null; status: "active"|"expired"|"withdrawn"; }
interface ConsentWithdrawal { id: string; grantId: string; scope: "full"|"partial"; purposes: Purpose[]; createdAt: string; }
interface PrivacyRequest { id: string; kind: "access"|"correction"|"restriction"|"export"|"deletion"; status: "received"|"verifying"|"decided"|"fulfilled"|"rejected"; createdAt: string; }
interface RetentionClock { id: string; policy: string; scopeRef: string; expiresAt: string; onHold: boolean; }
interface LegalHold { id: string; scopeRef: string; reason: string; active: boolean; }
interface DestructionJob { id: string; scopeRef: string; status: "pending"|"approved"|"executed"; evidenceRef: string | null; }
```

UI surfaces: `/administration/consents` (template list + grant table with purpose chips + withdrawal dialog), `/gov/privacy-requests` (kanban: received→verifying→decided→fulfilled), `/gov/retention` (clocks table + holds + destruction approvals).

### 4.7 Prompt 09 — documents (`src/mocks/documents.ts`)

```ts
type DocState = "quarantine"|"scanning"|"safe"|"classifying"|"ocr"|"ready"|"infected"|"unreadable"|"unsupported"|"failed";
interface Document { id: string; tenantId: string; patientId: string | null; category: string; classification: "public"|"internal"|"restricted"; state: DocState; mime: string; sizeKb: number; checksum: string; retention: string; createdAt: string; }
interface ProcessingAttempt { id: string; documentId: string; stage: string; outcome: string; createdAt: string; }
interface AccessGrant { id: string; documentId: string; recipient: string; purpose: string; startsAt: string; expiresAt: string | null; revokedAt: string | null; }
```

UI surfaces: `/administration/documents` — pipeline board columns = DocState groups (Quarantine / Scanning / Processing / Ready / Failed) with cards; detail drawer tabs (Versions / Scan results / OCR text mock / Grants / Audit). Upload button opens dialog → drops file into "quarantine" column (mock). Failed column shows infected/unsupported with retry mocks.

### 4.8 Prompt 10 — work (`src/mocks/work.ts`)

```ts
type TaskState = "open"|"acknowledged"|"in-progress"|"deferred"|"completed"|"cancelled"|"reopened";
interface Task { id: string; tenantId: string; title: string; state: TaskState; urgency: "routine"|"urgent"|"critical"; assignee: string; queue: string; dueAt: string; sla: "on-track"|"warning"|"breached"|"paused"; }
interface SlaInstance { id: string; taskId: string; policy: string; deadline: string; state: "on-track"|"warning"|"breached"|"paused"; escalations: number; }
interface Notification { id: string; channel: "in-app"|"email"|"sms"|"push"|"voice"; title: string; state: "queued"|"sent"|"delivered"|"failed"; createdAt: string; }
interface MessageThread { id: string; ref: string; participants: string[]; updatedAt: string; unread: number; }
interface QuietHours { start: string; end: string; timezone: string; }
```

UI surfaces: `/administration/tasks` (queue tabs + SLA chips + task drawer with state-transition buttons), `/administration/notifications` (center + preferences + quiet-hours card + template list), `/administration/messaging` (thread list + read-only thread view with addendum composer mock), `/care/schedule` (day/queue board from same Task mocks filtered `queue=care.*`).

---

## 5. Page-by-page breakdown (layout + sections + components)

### 5.1 `/app/overview` — home

- `PageHeader`: "Good morning, {displayName}." + date + actions [New task (mock)] [Upload document (mock)].
- Row 1: 4× `StatCard` — Open tasks (mine), SLA warnings, Pending reviews, Unread notifications. Each links to its page.
- Row 2 (2-col): `card` "My queue" (top 6 tasks table mini) + `card` "Attention" (SLA breached/warning list).
- Row 3 (2-col): `card` "Schedule today" (care visits mini) + `card` "Activity" (mock audit feed, no PHI).
- All cards: `skeleton` first paint pattern documented (mock `setTimeout` not needed — render directly, skeletons shown via `?skeleton` story only if time permits).

### 5.2 Bridge — `/bridge/inbox`, `/bridge/cases/:id`

- Inbox: toolbar (`search input` + `select` urgency + `select` state + `button` filters) → `DataTable` columns: Case ref / Patient initials / Urgency badge / State / SLA chip / Updated / →. Row click → drawer with summary tabs (Summary / Documents chips / Messages / Activity). NO clinical editing — buttons are "Assign (mock)", "Request info (mock)".
- Case detail route renders same drawer content full-page for deep-linkability.

### 5.3 Care — `/care/schedule`, `/care/monitoring`

- Schedule: day strip (`button` group Today/Tomorrow/Week) + queue `tabs` (Visits / Deliveries / Follow-ups) → board of `card` rows with time, assignee avatar, state badge, SLA chip. State buttons: Acknowledge / Start / Complete / Handoff (each → confirm → mock toast).
- Monitoring: patient-chip list (initials + consent-status chip green/grey) + per-row "monitoring active/paused/withdrawn" badge. Withdrawn rows show banner "Consent withdrawn — read-only" (Prompt 08 rule made visible).

### 5.4 Pulse — `/pulse/reports`

- `StatCard` row (reports generated, forecast jobs, delivery rate) + `DataTable` (name / type summarize|translate|forecast / state / created) + detail drawer showing mock chart (`chart.tsx` with static data) + "Download (mock, step-up banner)".

### 5.5 Gov — `/gov/*` (5 pages, dense but uniform)

- `access-reviews`: table of RoleAssignments due for review + Approve/Revoke mock buttons + progress bar.
- `emergency-access`: active sessions table + "Request break-glass" button → `alert-dialog` (reason textarea + duration select + step-up checkbox + acknowledgement) → mock session row appears. Reviews table below.
- `privacy-requests`: kanban 5 columns (received/verifying/decided/fulfilled/rejected) with draggable-look cards (no dnd lib — buttons "Advance →" move columns in mock state).
- `retention`: clocks table (policy/scope/expires/hold toggle visual) + holds list + destruction approvals (two-step confirm).
- `audit`: outbox explorer — filters (state, aggregate) + table (event/version/aggregate/tenant/actor/correlation/attempts) + row drawer showing payloadRef + consumer receipts (ProcessedEvent chips). Read-only, `mono` font for IDs.

### 5.6 Administration — `/administration/*` (10 pages, the bulk)

1. **tenants**: cards grid per tenant (status badge, region, language, timezone) → detail `tabs` (Policy / Feature flags / Activity).
2. **organizations**: tree view (custom divs + `collapsible`) + relationship table (from→to, purpose, dates, capabilities chips).
3. **facilities**: hierarchy breadcrumb Org→Facility→Department + tabs (Details / Departments / Capabilities / Emergency instructions callout).
4. **readiness**: 4 gate cards (clinical/security/legal/integration) with progress + items checklist with owner avatar + evidence link mock.
5. **roles**: matrix `table` (13 roles × ~12 permissions, dot = granted) + TemporaryAccessGrant + CoverageDelegation tables.
6. **memberships**: invite dialog (email + role select + scope select → mock row), member table with suspend/terminate actions.
7. **patients**: §4.5 + duplicates queue section on same page (`tabs`: Directory / Duplicates (count badge) / Merges).
8. **consents**: templates table + grants table (purpose chips colored per purpose) + withdrawal `dialog` (full/partial + purpose checkboxes).
9. **documents**: pipeline board §4.7.
10. **tasks / notifications / messaging / integration / health / profile**: §4.8 + Prompt 03 health page (probe cards green, queue lag table, scheduler card, dead-letter table with "Replay (mock)" + metric tiles).

### 5.7 Detail pattern (used ≥15 times — build ONCE)

`DetailDrawer` (`sheet` right, 480px): header (title + status badge + ID mono), `tabs` (contextual), audit mini-feed at bottom ("Created … by …"), footer actions (mock buttons). Every table row in the workspace opens one.

---

## 6. RBAC visibility matrix (mock-only gating via Role switcher)

| Capability | clinician | nurse | coordinator | pharmacist | ops mgr | credential reviewer | program admin | auditor | privacy officer | security officer | analyst | diaspora specialist | tenant admin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| overview | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| bridge inbox | ✓ | · | ✓ | · | ✓ | · | · | · | · | · | · | ✓ | ✓ |
| care schedule | ✓ | ✓ | ✓ | · | · | · | · | · | · | · | · | · | ✓ |
| patients directory | ✓ | ✓ | ✓ | ✓ | · | · | · | · | ✓ | · | · | ✓ | ✓ |
| duplicates/merge | · | · | ✓ | · | · | · | · | · | ✓ | · | · | · | ✓ |
| consents | ✓ | ✓ | ✓ | · | · | · | · | ✓ | ✓ | · | · | · | ✓ |
| documents | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | ✓ | ✓ | ✓ | · | ✓ | ✓ |
| tasks | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | · | · | ✓ | ✓ |
| gov pages | · | · | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | · | ✓ |
| tenants/orgs/facilities | · | · | · | · | ✓ | · | ✓ | · | · | · | · | · | ✓ |
| roles/memberships | · | · | · | · | · | ✓ | ✓ | ✓ | ✓ | ✓ | · | · | ✓ |
| health/integration | · | · | · | · | ✓ | · | · | · | · | ✓ | · | · | ✓ |

`·` = nav item hidden + route shows `EmptyState` "Not permitted for role {x} (mock)". This demonstrates Prompt 06 scope logic visually without any real enforcement.

---

## 7. File tree to create (all under `src/`, per AI_RULES.md)

```
src/
  App.tsx                        # EDIT: add workspace routes (keep existing)
  mocks/
    kernel.ts                    # §4.1
    identity.ts                  # §4.2
    organization.ts              # §4.3
    access.ts                    # §4.4
    patients.ts                  # §4.5
    consent.ts                   # §4.6
    documents.ts                 # §4.7
    work.ts                      # §4.8
    index.ts                     # re-exports + tenant/role switcher helpers
  components/workspace/
    WorkspaceShell.tsx
    WorkspaceSidebar.tsx
    WorkspaceTopbar.tsx
    PageHeader.tsx
    StatCard.tsx
    StatusBadge.tsx
    DataTable.tsx
    DetailDrawer.tsx
    EmptyState.tsx
    MockBanner.tsx
    RoleTenantSwitcher.tsx       # mock switchers (localStorage)
  pages/app/
    Overview.tsx
  pages/bridge/
    Inbox.tsx
    CaseDetail.tsx
  pages/care/
    Schedule.tsx
    Monitoring.tsx
  pages/pulse/
    Reports.tsx
  pages/gov/
    AccessReviews.tsx
    EmergencyAccess.tsx
    PrivacyRequests.tsx
    Retention.tsx
    Audit.tsx
  pages/administration/
    Tenants.tsx
    Organizations.tsx
    Facilities.tsx
    Readiness.tsx
    Roles.tsx
    Memberships.tsx
    Patients.tsx
    Consents.tsx
    Documents.tsx
    Tasks.tsx
    Notifications.tsx
    Messaging.tsx
    Integration.tsx
    Health.tsx
    Profile.tsx
```

Shadcn/ui, marketing components, auth pages: DO NOT MODIFY (except `App.tsx` routes).

---

## 8. Build phases (each ends with a viewable page, `pnpm dev` green)

- **Phase 1 — Shell + Overview + mocks skeleton.** `mocks/index.ts` (tenants, roles, 6 tasks), `workspace/*` primitives, `/app/overview` static, routes wired, `WorkspaceLanding` deleted. ✅ View: sidebar/topbar/overview render.
- **Phase 2 — Work coordination.** `mocks/work.ts` full, `/administration/tasks`, `/notifications`, `/messaging`, `/care/schedule`. ✅ View: task drawer + SLA chips + kanban visuals.
- **Phase 3 — Identity & org.** `mocks/identity|organization|access.ts`, `/administration/{profile,memberships,roles,tenants,organizations,facilities,readiness}`, `/gov/{access-reviews,emergency-access}`. ✅ View: role matrix + break-glass dialog.
- **Phase 4 — Clinical identity & privacy.** `mocks/patients|consent.ts`, `/administration/{patients,consents}`, `/gov/{privacy-requests,retention}`, `/care/monitoring`. ✅ View: duplicates queue + withdrawal flow.
- **Phase 5 — Documents, pulse, platform.** `mocks/documents|kernel.ts`, `/administration/{documents,integration,health}`, `/gov/audit`, `/bridge/*`, `/pulse/reports`. ✅ View: pipeline board + audit explorer. Final pass: MockBanner everywhere, role matrix enforced in sidebar, `pnpm build` green.

---

## 9. Acceptance criteria (check before calling it done)

- [ ] `pnpm dev` + `pnpm build` green, no new deps, no edits to `ui/*` or auth pages.
- [ ] Every route in §2 renders with `WorkspaceShell`, `PageHeader`, `MockBanner`.
- [ ] Every table uses `DataTable` + `pagination` visuals + `EmptyState` when filtered to zero.
- [ ] Every row opens a `DetailDrawer` (or navigates to a detail route that reuses it).
- [ ] Status colors follow §1.4 with zero exceptions.
- [ ] Role switcher hides/shows nav per §6; tenant switcher swaps mock rows.
- [ ] No `fetch`/axios/query; no tokens; no real names; "mock" appears in banner + all mutation toasts.
- [ ] `Mediterra.` spelling (capital M + dot) in all new visible copy.

---

## 10. Backend → UI traceability (which prompt feeds which page)

| Backend prompt | UI pages | Key mock file |
|---|---|---|
| 02 kernel | `/gov/audit`, `/administration/health` (consumers), idempotency chips | `mocks/kernel.ts` |
| 03 queues/observability | `/administration/health`, `/administration/integration` | `mocks/kernel.ts` + `mocks/work.ts` |
| 04 auth/identity | `/administration/profile`, `/administration/memberships`, session cards | `mocks/identity.ts` |
| 05 org/facility | `/administration/{tenants,organizations,facilities,readiness}` | `mocks/organization.ts` |
| 06 access | `/administration/{roles,memberships}`, `/gov/{access-reviews,emergency-access}` | `mocks/access.ts` |
| 07 patients | `/administration/patients` | `mocks/patients.ts` |
| 08 consent/privacy | `/administration/consents`, `/gov/{privacy-requests,retention}` | `mocks/consent.ts` |
| 09 documents | `/administration/documents` | `mocks/documents.ts` |
| 10 tasks/notify | `/administration/{tasks,notifications,messaging}`, `/care/schedule`, `/app/overview` | `mocks/work.ts` |

## 11. Current implementation status

Phases 1–5 now have mock-backed workspace screens; implementation is no longer waiting to start Phase 1. The completion pass adds functional shared pagination and optional sorting, responsive record cards, task creation/lifecycle actions, task/patient/document search deep links, integration run details, permission-aware navigation and accessible drawer behavior.

TypeScript, lint (warnings only), the 18 existing unit tests, and production build pass. The original acceptance checklist above remains the design baseline rather than a claim of exhaustive certification: specialized document boards, permission matrices and health tables intentionally retain their domain-specific layouts. Two shared UI type declarations and the Tailwind plugin import were corrected to unblock lint; no new dependencies were introduced in this completion pass.

For setup, route-by-route acceptance, role switching, mock limitations and commands, see [Local UI/UX testing](local-testing.md). Production API/auth integration, durable persistence and real delivery/file/security operations remain outside the mock UI milestone.
