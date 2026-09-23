# Elseview — Research feature contracts

**Brand:** Elseview — See what you’re missing.

Detailed optional feature contracts retained from the broader design. The four-container architecture in `/Users/user/Workspace/startup-act/BACKEND_BLUEPRINT.md` takes precedence. These are planned features, not a requirement to implement every endpoint or table at launch. Background work runs inside the backend; AI calls the configured cloud provider.

## 1. Private files

Uploads use generated private storage keys, bounded size, verified media type and quarantine before processing. Published stimuli are immutable. Every download checks workspace/session/share permission; a checksum is not authorization. Recordings need separate consent. Browser cross-origin restrictions mean a prototype link alone does not provide internal click tracking.

## 2. Permissions

Roles are owner/admin, researcher, assigned reviewer and viewer; participant access is separate. Explicit study grants control raw-data visibility, publication, AI dispatch and export. Never permit another workspace's IDs to bypass object checks. Reviewers cannot assess their own participation. API credentials and cloud keys never enter client payloads.

## 3. Compensation and usage

Software credits, customer invoices and participant rewards are distinct. Use integer monetary units, currency, unique event keys and append-only corrections. Real compensated studies need a reward record and manual payout reconciliation before launch. Automated AI flags cannot deny compensation. Transfers, escrow and tax reporting are not performed by the backend merely because it stores a payment record.

## 4. Quality review

Versioned rules flag duplicate submissions, implausible timing, attention checks and off-topic text. Distinguish a network retry from dishonest participation. Record reviewer reasons, evidence and appeal outcomes. No model-produced confidence score is accepted as proof of fraud.

## 5. Reports

Freeze source/version/consent snapshots. Compute counts in SQL/Python, show numerator/denominator/missing values and describe panel sampling limits. AI writes drafts linked to verified source quotes. Approval creates a report revision. Revocation invalidates derived copies and shares. Spreadsheet exports escape formula-like values; private recordings and raw identities require separate permission.

## 6. API families

Use /api/v1 and schema-validated JSON. All work is inside the same backend container.

| Family | Planned operations | Rule |
|---|---|---|
| Auth | Register, login, refresh, logout, recovery | Hashed secrets, rate limits and revoked-session checks |
| Workspaces | Membership and study grants | No broad default raw-data visibility |
| Studies | Draft, versions, blocks, preview, publish, pause, close | Published definitions immutable |
| Recruitment | Invitation, screener, reservation | Atomic capacity and compensation commitment |
| Collection | Resume, answer revision, events, submit, withdraw | Session-bound token, safe block projection, idempotency |
| Reviews | Flags, assignment, decisions, appeals | Human evidence and conflict checks |
| Storage | Upload intent, content, complete, authorized download | Quarantine and retention |
| Analysis | Snapshot, metrics, comparisons | Reproducible source population |
| AI | Estimate, run, status, cancel, review | Cloud cost reservation and provider/consent policy |
| Reports | Draft, approve, export, share, revoke | Source permissions and export scope |
| Jobs | Status and controlled retry | PostgreSQL leases and persisted results |
| Privacy | Consent, access, withdrawal, deletion | Propagate to permitted derivatives |
| Billing | Usage, rewards, manual payment records | No automatic financial transfer |

This catalogue describes features rather than a requirement to implement all routes immediately. The detailed normalized dictionary is a later reference; the lightweight main blueprint defines launch scope.

## 7. Feature coverage and acceptance

The detailed method registry is `/Users/user/Workspace/startup-act/docs/backend/RESEARCH_METHODS.md`. The table below traces every requested feature family to an implementation owner and testable outcome; a template reuses blocks instead of creating a parallel backend.

| Requested feature | Module/method | Acceptance evidence |
|---|---|---|
| Prototype and usability tasks | Studies/collection, `prototype_task` | Published owned task, safe asset, saved outcome with measurement provenance |
| Five-second impressions | Timed exposure + follow-up | Frontend visibility timing, hidden asset after exposure, timing anomaly flag |
| Preference comparison | Variant block, experiment assignment | Stable randomized order, tie handling, denominator shown |
| First-click and heatmap data | Geometry-aware block/events | Normalized coordinates tied to immutable image dimensions |
| Surveys and branching | Typed questions + safe graph | All allowed paths validated; hidden/rejected question answers cannot be forged |
| Card sorting | Card/group response | Each required card appears once; open/closed modes checked |
| Tree testing | Tree/path response | Valid path, target outcome and backtracking count |
| Interviews | Scheduling + assets | Conflict-free booking, consent, attendance, approved recording access |
| Diary studies | Occurrences + entries | Time-zone-safe due windows, dedupe and missing-day reporting |
| Accessibility research | Task/issue template | Assistive-tech context and evidence; no unsupported certification |
| Content/language testing | Text comprehension template | Original dialect recorded and reviewed translations separated |
| Product concept and pricing tests | Survey/preference templates | Choice evidence distinct from real buying behavior |
| Onboarding, journey and forms | Ordered tasks/events | Step-specific attempts and missingness, no inflated full-journey claim |
| Competitor and feature prioritisation | Comparison/ranking/constant sum | Compatible tasks, valid ranking/totals and fair interpretation |
| Marketing ads, brand, landing/video pages | Exposure/survey/task templates | Recall/clarity results not claimed as measured conversion lift |
| Audience and market-entry analysis | Recruitment segments + snapshots | Disclosed panel coverage and suppressed tiny segments |
| Business offer, instructions and support | Survey/task templates | Policy-grounded questions and observed comprehension outcomes |
| AI customer chatbot tasks | Authorized sandbox scenarios | Versioned model/policy and reproducible failures; no unrestricted live transactions |
| AI safety, response quality and preference | Specialist rubric + blind comparison | Human adjudication, criteria version and uncertainty |
| Voice and translation evaluation | Assets/transcripts + language review | Consent, imported or explicitly approved cloud transcript metrics and dialect-specific findings |
| Dataset labelling | Annotation tasks/reviews | Label schema, agreement and provenance/rights |
| AI thematic summaries/clustering | AI jobs + source evidence | No invented citation; counts from validated respondent membership |
| AI sentiment, ad critique and Q&A | AI draft tools | Labeled tentative output; human interpretation, not emotion/sales oracle |
| AI reports and comparisons | Fixed metrics + approved evidence | Draft/approval/version separation and revocation |
| Panel targeting, screeners and private panels | Panel/recruitment | Opt-in boundaries and no cross-client private contact discovery |
| Quality controls and appeals | Quality module | Supported reasons and review; no automatic AI payout denial |
| Team roles, workspaces and API | Identity/workspaces/integrations | Deny-by-default object access tests including workers |
| Pricing, usage and compensation | Billing/rewards | Replay-safe balanced records; no automatic financial transfer claim |
| Exports/sharing/locales | Reports/storage/localization | Arabic-readable output, formula-safe spreadsheet and revocable shares |
| Privacy and self-hosting | Privacy/ops | Mock-provider/offline core tests, cloud outage handling, derivative purge and successful isolated restore |

