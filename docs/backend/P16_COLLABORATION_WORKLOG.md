# P16 implementation worklog

Initial implementation (2026-09-23): owned collaboration models, routes, privacy hooks,
webhook transport and calendar codec are present, along with self-contained migration
016 (parent 015_billing). Shared application registry/config/worker integration is
owned by the lead and tracked separately.

## Security contract

- API credentials are random, SHA-256 stored, expire within 90 days, and work ONLY
  on dedicated `collaboration/api` report/template routes via `X-API-Key`.
  Every read rechecks active user/workspace membership, privacy and scope.
- Comments are untrusted raw data, require study `raw` permission to write/read,
  never appear in granted reports. Subject restriction marks all workspace comments
  restricted (quotes cannot be reliably attributed); physical purge waits for policy.
- Report grants require explicit same-workspace recipient and current issuer publish
  authority, exact current approved revision, live source validation, and return only
  existing analytics safe summary with suppression.
- Template grants explicitly authorize issuer study edit and same-workspace recipient.
  Shared output is the public versioned catalogue recipe, NOT customized origin inputs.
- Calendar exports are local, authenticated participant booking reads with mandatory
  exact revision; cancellation emits CANCELLED, UTF-8 lines fold at 75 octets.
  No join URL or custom title is exported.
- Webhooks default disabled; mock uses actual httpx.MockTransport. Explicit live mode
  requires exact operator-approved URL/secret. Every attempt resolves DNS, rejects any
  nonglobal address, connects only vetted literal IP with original TLS SNI and Host,
  never follows redirects or environment proxies. Response bodies are not read.
- Delivery body is allowlisted generic event metadata only. Stable delivery UUID,
  timestamped HMAC and bounded retry metadata allow receiver replay deduplication.
  Receiver MUST persist its replay ledger (helper's in-memory set is illustrative).
- No vendor connector, SMTP, paid provider, or automatic integration activation.

## Evidence so far

- `pytest tests/test_collaboration.py -q`: **14 passed**.
- `ruff check app/collaboration tests/test_collaboration*.py`: clean.
- Eight DB tests exercise actual scopes, raw/granted reads, mock delivery jobs,
  private template grants, participant preferences and calendar revisions.
  Final integrated execution evidence is in `IMPLEMENTATION_STATUS.md`.

Not a production live endpoint certification. Tests use MockTransport only.

## HTTP endpoints

All IDs are UUIDs. `W=/api/v1/workspaces/{workspace_id}/collaboration`.
All routes use normal bearer authentication except the two explicitly named API
key read routes. JSON bodies reject unknown properties.

| Method/path | Body / behavior |
|---|---|
| POST `W/api-keys` | `{scopes: ["reports:read" or "templates:read"], days: 1..90}`; returns raw key once |
| DELETE `W/api-keys/{id}` | Owner revokes credential |
| POST/GET `W/reports/{id}/comments` | POST `{text}` up to 4000 characters; both require raw study authority |
| POST `W/reports/{id}/grants` | `{recipient_id}`; current approved revision only |
| GET `W/reports/{id}/granted` | Explicit recipient, redacted aggregate only |
| GET `W/api/reports/{id}` | `X-API-Key` with reports:read AND explicit report grant |
| POST `W/templates/{instance_id}/grants` | `{recipient_id}`; same-workspace only |
| GET `W/templates/{instance_id}/shared` | Explicit recipient; public catalogue recipe only |
| GET `W/api/templates/{instance_id}` | `X-API-Key` with templates:read AND explicit template grant |
| DELETE `W/{reports or templates}/grants/{id}` | Issuer revokes |
| PUT/GET `W/notification-preferences` | `{reminders: boolean}`; participants supported |
| POST `W/integrations` | `{destination}` exact operator-approved URL; workspace admins only |
| DELETE `W/integrations/{id}` | Disable and advance revision; queued deliveries reauthorize |
| POST `W/integrations/{id}/deliveries` | `{command_key: UUID}`; metadata-only test event, stable delivery/job IDs |
| GET `/api/v1/participant/bookings/{id}/calendar.ics?revision=N` | Own booking; stale revision 409 |

`collaboration.test` delivery schema is deliberately metadata-only:
`{"id":"delivery-uuid","schema_version":1,"type":"collaboration.test"}`.
P16 does not silently attach arbitrary research state to a webhook.

Signing key is `HMAC-SHA256(operator_secret, integration_uuid)` (binary digest).
Signature hex is `HMAC-SHA256(signing_key, timestamp + '.' + delivery_uuid + '.' + body)`.
Headers: `Webhook-Id`, `Webhook-Timestamp` (Unix seconds), `Webhook-Signature`.
The operator provisions the derived per-integration key to the receiver outside the
application API. Verify signature, reject timestamps outside 300 seconds, then
atomically reserve delivery UUID in a durable receiver replay table before effects.
Retries preserve delivery UUID and exact body, not necessarily timestamp/signature.
429/5xx/network failures retry at most three job attempts; numeric Retry-After is
clamped to 1..60 seconds. Redirects and other non-2xx results fail terminally.

Settings supplied by lead: `COLLABORATION_INTEGRATION_MODE=disabled|mock|live`
(default disabled), `COLLABORATION_WEBHOOK_DESTINATIONS` exact URL JSON list,
`COLLABORATION_WEBHOOK_SECRET` >=32 chars when enabled,
`COLLABORATION_WEBHOOK_TIMEOUT_SECONDS` less than worker timeout.
