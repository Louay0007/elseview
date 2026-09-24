# P18 local reliability probe

## Safe invocation

Requires exclusive ownership of the dedicated disposable `_test` database: the shared
fixture **downgrades to base then migrates to head**. Never run alongside another DB
suite or against development/product data. `app.test_runner` continues to exclude
`load` by default; this separate entry point accepts no arbitrary pytest arguments.

From `/Users/user/Workspace/startup-act/backend`, with the existing guarded test
environment loaded (do not paste credentials in reports):

```sh
TEST_ALLOW_LOAD=1 \
P18_METRICS_PATH=/Users/user/Workspace/startup-act/.tools/p18-load-metrics.json \
.venv/bin/python -m app.reliability_probe
```

`DATABASE_URL`, `TEST_DATABASE_URL`, and `TEST_ALLOW_RESET` must pass the existing
exact-name `_test` guard. A container invocation uses its own absolute output path
(e.g. `/tmp/p18-load-metrics.json`); copy that artifact out afterward. The entry point
forces mock AI, test environment, and disables the automatic runner. The test starts
exactly one runner on the same application event loop as TestClient requests. No
provider, new dependency, socket HTTP server, or fifth Compose service is involved.

## Workload and interpretation

Four independently authenticated collection sessions, each with twelve sequential
canonical answer autosaves, run simultaneously behind a start barrier. Each submits
and retries the submission with the same version/revision. Study fixtures, invitation,
consent, publishing, and authentication use existing helpers; setup is excluded from
measured duration. A real durable AI job performs prepare/finish transactions, but its
mock adapter is held behind an explicit release barrier until all writes/submissions
finish. The runner shares the API's actual database pool and application event loop.

Assertions verify 48 accepted answer revisions remain durable, all four accepted
submission snapshots remain present, and exactly one quality job per submitted
session exists. This is **not** a reward race proof: P19/review/longitudinal reward tests
cover ledger uniqueness. Rate limiting is the fixture's local no-op limiter, not
Valkey. There is no network/proxy latency or production capacity claim.

Aggregate JSON records nearest-rank p50/p95 autosave wall latency, exact request body
sizes, concurrency, measured duration, mock blocking duration, sampled pool usage,
AI job created-age while running, process lifetime peak RSS before/after, OS,
architecture, Python version, logical CPUs, and physical memory. Created-age includes
execution and is not exclusively pending queue delay. RSS includes client and setup
and excludes PostgreSQL. There are no actor/job/session identifiers, prompts,
credentials, exception strings, or payload bodies in the artifact. Failures do not
produce a success artifact; remove old artifacts before rerunning. The bounded fixed
48-write workload measures this host, not an invented requests/second target.

## Resilience evidence and remaining operational drills

- `test_low_disk_guard_recovers_without_partial_file`: monkeypatches free-space
  reporting, verifies preflight rejects with STORAGE_FULL and leaves no partial
  file, restores free space and verifies write/read/delete recovery. Existing
  `test_privacy_assets::test_disk_full_and_symlink_boundaries` separately checks
  HTTP 507 with sanitized I/O error. Neither physically fills a filesystem.
- `test_job_poll_exception_is_sanitized_and_recovers`: injects one polling exception,
  verifies backoff, generic-only logging and the next poll succeeds. Existing
  `test_jobs` checks durable lease expiry, fencing, timeout/retry, shutdown and
  cancellation-resistant handlers with real DB where marked.
- Actual PostgreSQL/container restart, cache restart/flush, and backend reload are
  **lead-owned operational drills**, requiring a safety snapshot, durable row counts
  before/after and readiness recovery. `engine.dispose()` is not a database restart
  and this probe does not claim otherwise. Do not run disruptive drills concurrently
  with this suite. Cache eviction tests are not proof of container restart.

Pure checks (no DB):

```sh
cd /Users/user/Workspace/startup-act/backend
.venv/bin/python -m pytest tests/test_reliability.py -m 'not db and not load' -q
```

Executed locally: **3 passed, 1 deselected**. The subsequent guarded load result is below.

## Executed load result (2026-09-24)

The exclusive guarded container run passed: **1 passed, 3 deselected in 3.64s**.
Artifact: `/Users/user/Workspace/startup-act/.tools/p18-load-metrics.json` (copied from
container `/tmp/p18-load-metrics.json`). Linux aarch64, Python 3.12.14, 8 logical CPUs,
8,319,770,624 visible physical memory bytes; this is container-visible hardware,
not a statement of dedicated production resources.

| Metric | Observed |
|---|---:|
| Concurrent sessions / accepted autosaves / accepted submissions | 4 / 48 / 4 |
| Autosave payload | 147–148 bytes |
| Autosave p50 / p95 | 63.24 / 123.02 ms |
| Measured workload window / mock blocking | 1.048 / 1.033 s |
| Maximum sampled AI created-age (running, not pending-only) | 1.061 s |
| Maximum sampled pool checkouts | 4 |
| Process lifetime peak RSS before / after | 151,314,432 / 151,314,432 bytes |

This short fixed-workload smoke benchmark is deliberately not a soak test, a
throughput guarantee, or evidence of production SLOs. No thresholds were invented
from this single run. The DB window was released to the lead for separate disruptive
operational drills.
