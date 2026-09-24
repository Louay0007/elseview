# Elseview — Cloud LLM specification

**Brand:** Elseview — See what you’re missing.

## Decision

Call an OpenAI-compatible cloud provider from the Python backend. No local inference, GPU, model container or dedicated AI worker. The actual provider/model is not yet specified; compatibility, pricing and privacy cannot be inferred from the word compatible.

## Configuration

| Setting | Meaning |
|---|---|
| LLM_BASE_URL | Operator-approved HTTPS API root; include /v1 only when required |
| LLM_API_KEY | Backend-only secret |
| LLM_MODEL | Exact provider model identifier |
| LLM_TIMEOUT_SECONDS | Proposed initial 60-second total deadline |
| LLM_MAX_OUTPUT_TOKENS | Proposed 1500 initial cap; use the provider's supported field |
| LLM_CONTEXT_LIMIT | Verified model limit |
| LLM_CONCURRENCY | Initially 1 |
| LLM_MAX_ATTEMPTS | At most 2 including initial call, subject to uncertain-charge policy |
| LLM_SUPPORTS_JSON_SCHEMA | Explicit tested capability |
| LLM_INPUT_PRICE_PER_MILLION | Configured Decimal price in provider currency |
| LLM_OUTPUT_PRICE_PER_MILLION | Configured Decimal price; other charges recorded separately |
| LLM_STUDY_BUDGET | Per-study ceiling with currency |
| LLM_WORKSPACE_DAILY_BUDGET | Daily aggregate ceiling with timezone |

One model/client is enough initially. Do not introduce an agent framework, vector database or fallback chain without evidence of need.

## Client contract

Use the OpenAI Python SDK with custom base_url, async client, explicit timeout and max_retries=0. The database job layer owns retries. Start with Chat Completions. Verify model ID, authentication, roles, output-limit parameter, JSON mode/schema, errors and usage reporting.

Some providers use max_tokens, others max_completion_tokens. Select supported options in an operator-approved capability profile. Do not assume Responses, tools, streaming, provider batch discounts or request idempotency exist. No silent fallback to another provider.

## Features

| Function | Input | Output |
|---|---|---|
| Study helper | Goal and template | Draft questions for researcher approval |
| Themes | Permitted redacted answers | Groups with exact supporting sources |
| Failure clustering | Reviewed failure descriptions | Proposed labels; code calculates counts |
| Translation | Original permitted text | Separate draft translation |
| Report writer | Verified metrics and quotes | Draft narrative with limitations |
| Research Q&A | Authorized snapshot context | Source-linked answer or insufficient evidence |
| Quality suggestion | Limited text and safe signals | Human-review flag, not a payout decision |
| Campaign clarity | Consented copy | Suggestions, not sales prediction |

Chat models do not necessarily transcribe audio. Start with uploaded transcripts. Cloud audio is a separately approved capability with its own consent, API support and price. Do not install a local transcription model by default.

## Job lifecycle

Persist job plus reserved budget in PostgreSQL. The embedded backend runner claims it, checks consent, redacts inputs, releases DB locks, calls the provider and validates output. Final persistence checks current lease, source snapshot and privacy epoch. All outputs are drafts until approved.

A provider may charge a request even if the connection fails. Record unknown outcomes, reserve conservatively and reconcile rather than treating them as free. Retry bounded rate limits according to Retry-After and policy; do not retry authentication/configuration failures. Never promise exactly-once external execution.

## Evidence and safe output

Treat source answers as untrusted data, not system instructions. Provide no shell, unrestricted database tools, credentials or arbitrary browsing. JSON-schema support is helpful when available; application validation remains mandatory. A malformed answer gets a bounded repair attempt or explicit failure.

```json
{"themes":[{"label":"Delivery instructions unclear","evidence":[{"source_id":"answer-17","quote":"I could not find the delivery date."}]}],"limitations":["Only supplied answers were reviewed."]}
```

This is illustrative, not real research. Check source ownership, approved snapshot membership and quote equality. Valid citations do not prove interpretation: humans still review. Counts/rates come from SQL/Python. Never synthesize participant feedback, diagnose emotion or let AI automatically deny compensation.

## Cost accounting

For simple token pricing:

`estimated cost = input_tokens / 1000000 * input_rate + maximum_output_tokens / 1000000 * output_rate`

Add reasoning, cached-token, minimum-call and other charges where applicable. Use Decimal arithmetic and explicit currency. Provider/model tokenizer estimates are preferred; where unavailable use conservative bounds and compare actual returned usage. Hard input-size/output limits apply.

Reserve under a budget lock before calls. Save usage/request IDs per attempt. Cache by workspace, snapshot hash, privacy epoch, provider/model/config, prompt and schema. Reopening a stored report needs no new call, but hosting/storage are not free. Changed evidence invalidates results. Context subsets must be identified as subsets, not exhaustive whole-study findings.

## Privacy

The app is Tunisian-operated by design; cloud AI is external processing. Record provider location/subprocessors, retention, training terms and deletion capability. Confirm Tunisian transfer requirements before real-data use. Consent alone is not automatic compliance.

Send minimum permitted redacted content. Keys stay backend-only. Operator-approved HTTPS hosts only; never participant-supplied endpoints. Sensitive projects can block all AI processing. Withdrawal stops future use and invalidates derivatives; provider-side deletion follows actual capabilities, not an invented guarantee. Log usage metadata, not source text.

## Tests and references

Mock tests: valid/malformed JSON, wrong source, 401/429, timeout, unknown charge, exhausted budget, concurrent reservations, consent change and provider outage. Live tests are opt-in, synthetic and budgeted. Test Arabic/French/Arabizi quality with humans before claiming expertise.

- https://github.com/openai/openai-python
- https://fastapi.tiangolo.com/advanced/events/
- https://www.postgresql.org/docs/16/sql-select.html

Status: P10 development implementation is available under
`/Users/user/Workspace/startup-act/backend/app/ai/`, with mocked-provider tests,
explicit live gates and conservative charge handling. No cloud account, real key
or paid API request was created. See `/Users/user/Workspace/startup-act/docs/backend/P10_P11_API.md`
for the implemented subset and `/Users/user/Workspace/startup-act/docs/backend/IMPLEMENTATION_STATUS.md`
for executed evidence and external compatibility/quality gates.
