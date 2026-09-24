# Participant profile contract fixture

`profile.html` mounts the default export from `../ParticipantProfile.jsx` inside one existing `main`. It uses a synthetic parsed-JSON request adapter only. No authentication providers, database, real participant records or outbound sends are used.

Parent integration:

```jsx
<ParticipantProfile request={session.request} sessionKey={session.familyId} />
```

The parent owns `#/participant/profile`, authentication and navigation. The component root is a `section`. Changing either prop clears the prior panel state; it does not store credentials, drafts or request receipts in browser storage.

## Authoritative API calls

- `GET /panel/profile`: an authenticated `404` is first-use/no-profile, not `{}` or `{items: []}`. Successful responses are `{id,status,attributes,targeting_provenance}`. The UI projects only editable attributes and does not render or resend receipt provenance.
- `GET /panel/consent?version=1` and `?version=2`: `{version,body,digest}`. Basic grants use v1; country, city or experience requires v2. A changed selected document resets agreement.
- `GET /recruiting/targeting-vocabulary`: uses server country identifiers and experience categories/levels, not a bundled geography dataset. No city lookup is supplied.
- `PUT /panel/profile`: `{decision,attributes,document_version,presented_digest,receipt_key}`. Decisions remain `granted` or `withdrawn`. All bodies are JSON objects; the request adapter supplies authentication and the `/api/v1` prefix.

Withdrawal requires a separate confirmation, uses the document appropriate to the saved profile, and sends `attributes: {}`. The successful withdrawn profile has `attributes: {}` and `targeting_provenance: null`; rejoining starts with empty optional inputs. This is not account erasure or assessment-consent withdrawal.

An uncertain mutation locks competing changes and retains its exact body in memory. It is never replayed automatically. `Check server profile` first reads the profile and documents. If the requested state is present, no mutation is repeated. Otherwise an explicit original-body/original-receipt retry is offered only after successful reconciliation and only while the same document digest is current. That comparison confirms current state, not delivery history. A page/session change drops pending requests.

## Current product limits

The backend model can contain `paused`, but its public profile API has **no pause command**; granting consent can resume an already-paused profile. The UI explicitly marks pause unavailable and never substitutes withdrawal. Interests and other demographics beyond age are not accepted attributes. Experience is self-reported familiarity, never interests, employment history or a professional credential. This slice does not close all C03 work.

## Validation

From the repository root, with the existing Vite server on `127.0.0.1:8091`:

```sh
mkdir -p .profile-validation
TMPDIR="$PWD/.profile-validation" \
  CONTRACT_BASE_URL=http://127.0.0.1:8091 \
  CONTRACT_VIEWPORT=1440x900 \
  CONTRACT_KEYBOARD_SUBMIT='Save profile and consent' \
  CONTRACT_KEYBOARD_RESULT='Public-panel profile and consent saved' \
  node scripts/browser_contracts.mjs /tests/profile.html
```

Repeat with `CONTRACT_VIEWPORT=390x844`. `TMPDIR` deliberately points into the repository: the existing runner owns and removes its uniquely named Chrome profile. Remove the empty `.profile-validation` afterward. Optional `CONTRACT_SCREENSHOT_DIR="$PWD/.profile-validation"` captures local screenshots; remove only those owned artifacts when finished.

The fixture covers first-use and withdrawn shapes, bounded fields, v1/v2 agreement and digest changes, country/city dependency, versioned experience, update/rejoin/resume, withdrawal confirmation/cancellation, committed and uncommitted uncertain writes, explicit same-body retry after read reconciliation, malformed successes, validation/rate-limit/conflict recovery, draft preservation across failed reads, revoked access, stale session reads/writes, partial metadata failures, native labels and nested-landmark avoidance. The shared runner adds desktop/mobile layout, 44px targets, contrast, native Enter and accessibility-tree checks. Results are synthetic browser evidence, not real participant or human-review validation.

Also run `curl --fail http://127.0.0.1:8091/ParticipantProfile.jsx` for the standalone transform, and the existing `npm test` / `npm run build` in `frontend`. A production build includes this component only after parent navigation integration imports it.
