# P18 React contract fixtures

Run unit tests from `frontend`: `npm test`. No extra dependencies.

Run the browser fixture against Vite's **development** server (the default production build does not include test HTML):

```sh
cd frontend
npm run dev -- --port 8080
# In another terminal:
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless --disable-gpu --no-first-run \
  --user-data-dir="$(mktemp -d /tmp/elseview-contracts.XXXXXX)" \
  --virtual-time-budget=15000 --dump-dom \
  http://localhost:8080/tests/contracts.html > /tmp/elseview-contracts.html
# Require PASS, not merely Chrome exit status:
grep 'id="fixture-result"' /tmp/elseview-contracts.html
```

Expected `#fixture-result` begins `PASS:`. `FAIL:` and `RUNNING` both mean the fixture did not pass. The lead runs Chrome; unit tests alone do not execute these React interactions.

The fixture mounts the actual ContractWorkbench and CollectionRunner (which uses StudyPreview.Question). It drives native forms through DOM events and replaces fetch before mounting. Requests outside its explicit allowlist fail; no real network fallback occurs. Assertions cover registration, authenticated study creation with identical retry payload/idempotency key, review decision, report GET/reload, asynchronous AI queued/draft states with a failed status read and retry, canonical collection answer envelope, identical retry after a simulated lost acknowledgement, explicit completion submission, and server-state recovery after remount. Native labels and alert/status regions are present; the fixture's small label assertion is not an accessibility audit.

Workbench credentials are props held in memory. Account/workspace changes remount command controls. Failed mutations retain their original payload and key for explicit retry; they are not automatically replayed. Review/report offer explicit authoritative reload. Participant close/open recovers server state without silently replaying pending answers. AI refresh reads the existing run instead of creating another; no unbounded polling occurs. No login/refresh-cookie persistence or full-page AI run recovery is implemented: callers must supply authenticated context and use backend IDs to resume outside this narrow workbench.

This is deliberately **not database E2E evidence**. Mock responses do not establish consent, access control, idempotency guarantees, revision conflict behavior, email delivery, payment, production proxy/CORS/CSRF, or cloud execution. Setup (workspace, retention policy, published study, consented participant session, review assignment, report) must already exist when using real APIs. The workbench only creates human-only studies; AI requests target a separately eligible assisted study. Report metrics and AI findings are displayed as escaped server data; no business metrics are reconstructed. Review exposes acceptance only, not the entire adjudication workflow. Manual keyboard and screen-reader checks remain required. The landing page and src.jsx are unchanged by this implementation.

## Preferred reliable Chrome runner

The lead's built-in Node/CDP runner supersedes `--dump-dom` where Chrome hangs:

```sh
# From repository root, with Vite serving the current sources:
CONTRACT_BASE_URL=http://127.0.0.1:8080 node scripts/browser_contracts.mjs /tests/contracts.html
```

The original fixture passed under this runner (16 mocked requests). The updated
fixture additionally rejects the first registration with canonical HTTP 422,
checks that fields unlock, edits the name using a real input event and submits
successfully (17 requests expected). Re-run it after copying/rebuilding updated
sources if the frontend container has no bind mount.

HTTP 422 now releases a rejected command for editing and a fresh command key.
Ambiguous network/server failures retain the original payload/key. Request/error
interfaces in `frontend/contracts.d.ts` mirror the checked-in OpenAPI subset;
there is no TypeScript compiler installed, and these declarations are documentation,
not runtime validation or invented response guarantees. Backend validation remains
authoritative. The canonical error envelope includes `request_id` alongside
`error.code`/`error.message`.
