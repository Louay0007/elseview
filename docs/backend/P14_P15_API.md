# P14/P15 — Versioned recipes and opt-in commercial billing

Development APIs in the existing four-service application. All paths start with
`/api/v1`; verified bearer authentication and tenant permissions are required.
Manual financial records do not move money or establish legal invoice compliance.

## P14 template catalogue

- `GET /templates` lists versioned recipes, required inputs, enabled shared methods
  and report caveats. `GET /templates/{key}?version=1` returns the pinned recipe.
- `POST /workspaces/{workspace_id}/templates/{key}/instantiate` requires
  `Idempotency-Key`, `template_version`, `title`, `retention_policy_id`, `locales`,
  exact `consent_documents` and typed `inputs`. Identical retries return the original
  draft; changing the request under the same key conflicts.
- Inputs contain a study-specific context, translation approval reference, localized
  prompts keyed by stable block IDs, rating endpoint labels, and real permitted
  stimulus references. Comparison recipes require stable options and authorized
  images. Localization recipes require pinned text source/rubric inputs and explicit
  reviewer-qualification references. No synthetic participant feedback is generated.
- Instantiation uses the existing study create/edit/validate services. It creates a
  draft, not an automatically published study. Normal publication permissions,
  consent, method gates and asset checks still apply.
- Immutable provenance records the recipe/version/hash and compiled inputs/config.
  Customer-industry response tables and duplicate method implementations are not added.

The 23 cases cover concept, pricing, competitor, feature ranking; onboarding,
checkout, registration, full journey; ad message, landing page, video, audience,
brand, prelaunch offer; forms, policies, support scripts, packages, market entry;
Tunisian Arabic, French, formal Arabic and Arabizi.

Templates reuse prototype tasks, preference, ranking, ratings, text and language
review as appropriate. Full journey separates four task stages. Marketing recall
is explicitly self-reported after review, not timed exposure. The video recipe is
a storyboard/key-frame content proxy, **not video playback/watch-through analysis**.
Pricing responses are stated willingness, not purchase commitments. Dialect
qualification and approved translations are operator attestations, not certification.
Locale changes never rename stable block/option identifiers.

## P15 activation and plans

Prefix: `/workspaces/{workspace_id}/billing`. Billing administration is owner/admin
only. A workspace that has never activated a subscription stays unbilled in development.
Once activated, new billable actions require a current subscription; cancelling a
plan does not silently return the workspace to free commercial use.

- `POST /plans` freezes a key/version and explicit reviewed rules. Repeating identical
  content is safe; a changed version snapshot conflicts.
- Rules require `currency: TND`, `exponent: 3`, rational tax numerator/denominator,
  `rounding: half_up`, supplier/customer/tax references, reviewed-rules reference,
  retention interval, committed budget, finite operational limit, full-payment policy,
  and a rate for each of `publication`, `response`, `ai_addon`, `specialist`.
- Each rate has `price`, finite `quota` and `included_units`. Allowances are distinct
  from quota grants and customer cash. “Unlimited” marketing cannot bypass the
  operational limit, storage constraints, or separate provider-cost budgets.
- `POST /subscriptions` supplies `plan_id`, timezone-aware `starts_at` and `ends_at`.
  Periods cannot overlap. Future purchases use new frozen plan versions; old usage
  is not repriced. `POST /subscriptions/{id}/cancel` records an immediate cutoff.
- `POST /grants` adds bounded product units against a subscription and unique source.
  Specialist purchases require an explicit specialist grant; a default rate does not
  silently enable them. `POST /specialist/{source_id}` is an authorized manual sale.
- `GET /plans`, `/subscriptions`, `/usage` and `/quotas` expose plan snapshots,
  reserved/consumed/released units, committed amounts and remaining finite capacity.

## Transactional usage

Publication reserves and consumes using the immutable study-version ID. Collection
and diary sessions reserve at start, then consume that same source at final submission.
Withdrawal releases only an unconsumed hold. AI add-ons reserve at run creation and
consume only a validated draft; failure releases the customer hold independently of
the provider's potentially uncertain charge. Provider costs, customer selling prices
and participant compensation are never summed as one currency/account.

Each source/kind is permanently unique. A different retry key cannot charge the same
response twice. Existing valid reservations retain their frozen terms across later
cancellation; pre-activation responses are not retroactively charged. Release does
not reverse consumed history or reprice other usage.

`POST /reconcile-reservations` performs a bounded operator sweep of expired/terminal
source holds. It releases no consumed usage and does not query an external provider.

## Invoices, payments and credits

- `POST /invoices` takes `subscription_id` and UUID `command_id`. It collects uninvoiced
  consumed usage, freezes rate/tax metadata and posts to the existing P08 journal.
  Zero-total invoices are rejected rather than creating meaningless postings.
- `GET /invoices` and `/invoices/{id}` expose totals, lines and source usage. Original
  invoices and lines are immutable; price changes apply only to future usage.
- `POST /invoices/{id}/payments` takes a UUID `command_id`, unique opaque `reference`,
  `evidence_digest`, full integer `amount`, `currency: TND`, and `exponent: 3`.
  Underpayment and overpayment are rejected. No card/bank details are collected.
- `POST /payments/{id}/reverse` takes `command_id`, records a separate reversal and
  appends the exact opposite journal posting. Historical payments are not rewritten.
- `POST /invoices/{id}/credit` takes `command_id` and creates a full credit/reversal.
  Any live customer payment must be reversed first. Partial credit/refund settlement
  is not supported. `GET /payments` provides reconciliation history.

The P08 ledger is reused with customer receivable, revenue and tax accounts. SQL
guards enforce frozen prices, source uniqueness, balanced postings, matching invoice
lines/totals, exact payment amounts and corresponding credit/reversal records.
Unpaid receivables are allowed only within the reviewed subscription's committed
budget. No overdraft wallet, FX conversion, automated collection or money transfer
is implied. Mixed currencies and a wrong exponent are explicitly rejected.

## Privacy and operational boundaries

Commercial records retain minimal opaque source/reference IDs and reviewed metadata,
not participant answers or contacts. Research erasure does not delete immutable
financial history. The recorded retention interval is an operator policy snapshot,
not an automatic legal-retention determination or a completed financial purge engine.

There is no new billing/template dashboard in this phase; these are API workflows.
No live payments, provider calls, jurisdiction-specific tax validation, or public
production release was performed. Existing frontend research renderers are reused.
Executed tests and limitations are recorded in
`/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md`.

Rollback preserves historical ledger rows, constraining new writes to the older
account vocabulary with a NOT VALID check. Dropping commercial schema data is a
destructive administrative migration; take a backup and make an explicit retention
decision before downgrading a populated deployment.