# Passive capture v2 — offline engineering only

This version repairs evidence-collection gaps without changing the worker,
model client, SQL guard, scorer, task/reference files or approved runtime
configuration. It is based on `644a68d75cf6743d3daaace51f42a0571747417c` and
does not activate a scope-observation remedy or execute Treatment A.

The [library](../scripts/passive_capture.py) imports no benchmark, model or
database runtime. Its CLI performs source/configuration preflight only and
refuses `--run`. A reviewed activation adapter and recorded owner scope approval
are still required. There is intentionally no automatic real-A command here.

## Why a separate version is needed

The original external collectors and failed evidence remain historical records.
Read-only inspection found these concrete gaps:

| Original location | Gap | v2 behavior |
|---|---|---|
| `work/execute_once.py:22–35` | Marker reserved before resource preflight; a snapshot failure could consume it without a recorded worker entry | Source/config preflight is separate; snapshots cannot mask treatment outcomes; reservation occurs at the executor wrapper boundary |
| `work/execute_once.py:51–55` | Invocation count and setup/spend statements were literal labels | Count comes from durable worker-entry events; no invented setup, human-time or spend measurements |
| `work/pinned_capture.py:44–82` | Started manifest existed in memory until the final block | Prepared and started manifests persist before worker entry |
| `work/pinned_capture.py:61–64` | Execution observations saved only after the worker returned | Public model/tool starts, returns and errors are appended and synced individually, including SQL before execution |
| `work/execute_once.py:38–60` | Monitor errors could go unnoticed and final snapshots could replace the primary error | Separate collector errors and source postflight; original delegate returns and exceptions preserved |

These observations justify this collection utility, not a new benchmark attempt
or a change to inference/evaluation criteria.

## Authorization and pin checks

`CaptureRequest` requires the exact execution commit, configuration file and
SHA-256. `capture_once` additionally requires `run=True`, a nonempty approval
reference and `runtime_offline_validity_gate == "passed"` in that pinned
configuration. The current base configuration says
`blocked_missing_scope_observation`; it cannot pass this execution guard.
A reference is recorded authorization evidence supplied by the caller, not an
automatic verification that an owner approved it.

Read-only preflight requires a clean worktree and recomputes the declared
contract fingerprint. It includes the versioned `scope_observation_v1.py` when
present, so a reviewed fingerprint containing that module detects its later
removal or modification. It also hashes the literal model-facing query tool
without importing the runtime. The same source/config checks run immediately
before reservation and after the attempt; postflight drift is a separate
capture blocker and never changes the worker's returned result or score.

The pinned configuration must match the fixed client contract: local
`hermes-local:qwen3.5-9b`, digest
`0df9cd2e3545377d86ebce465f455b69424224f59fb7ffd948d47efbeabe851c`,
temperature 0, `num_predict=512`, `num_ctx=65536`, timeout 120 seconds,
six model steps, two evidence calls and no retries/reprompts. The client source
fingerprint retains its 30-minute keep-alive. These are configuration/source
assertions. A fresh service preflight must separately verify the actual Ollama
model digest and environment before a future authorized run; this library makes
no service identity request.

## Capture and integration contract

The future adapter must inject the approved model, query and policy delegates,
wrap each with `wrap_model`/`wrap_tool`, and pass the approved worker through
`wrap_executor` exactly once. It must retain the existing worker constructor,
task loading and deterministic runner/scorer contract. The library supplies no
live adapter and no alternate model, tool, query, prompt or retry path.

Each wrapper calls its delegate once using the original argument objects and
returns the identical result object or rethrows the identical exception. SQL is
recorded before the query delegate executes. Normalization applies only to
copies written into evidence, never model/tool/scorer inputs or returned
objects. Model returns retain public response/tool-call fields and usage
metrics; private thinking/reasoning fields are excluded. Internal reasoning is
neither requested nor recorded. Worker dataclasses and string enums normalize
to inspectable public JSON.

The evidence folder must be new and outside the source checkout. Existing
folders and reservations are never overwritten or cleared. A prepared manifest
and the event log are created only after authorization/preflight. The started
manifest is persisted before an exclusive `INVOCATION_STARTED.json` reservation
and a durable `worker_enter` record immediately before the delegate call. A
second entry is refused. Calls through wrapped model/tools are refused outside
that worker entry. A worker error caught by an adapter cannot become a reported
completion.

This enforces **at most one recorded worker entry per evidence folder**. It does
not prove exactly-once execution across a process/power failure or across
different folders. A crash between reservation and entry/completion is
unresolved; the marker/folder remain consumed and no automatic replay occurs.
The invocation count describes the durable wrapper-entry boundary, not the
number of provider requests completed. Missing measurements remain unknown.

Evidence consists of:

- `manifest.json`: source/config pins and fingerprints, approval reference,
  attempt state, observed entry count, partial metrics, postflight and collector
  errors. Atomic replacement and file syncing preserve ordinary interruption
  boundaries; abrupt OS/storage failure still requires evidence review.
- `INVOCATION_STARTED.json`: exclusive reservation, never removed by the utility.
- `events.jsonl`: ordered UTC/monotonic starts, public returns/errors and resource
  snapshots. Each record is flushed and file-synced. Completed-call metrics
  remain available even if a later call fails. Missing/error-call tokens and
  durations are not estimated.

Before-call evidence-write failure prevents that delegate call. After-call
normalization/write failures mark collection incomplete and preserve the actual
return/exception. Failed finalization may leave a visibly unfinished started
manifest; it must never be read as a successful capture. Inspect both attempt
state and collector completeness before qualification. No phase is accepted or
advanced by this utility.

## Resource and timing limits

Default observations use before/after OS snapshots only: PID/PPID, OS-reported
CPU percent and RSS for the process hosting the worker, plus shared Ollama
process rows. CPU usage and process-lifetime peak RSS from `getrusage` include
the collector and other activity in that process. When a reviewed adapter is
launched as a child process, these describe that child host. They are not
per-request Ollama CPU, GPU/VRAM, busy-period peak model memory or evidence of
resource isolation. RSS is recorded in bytes; shared Ollama rows are not summed
into a model-memory claim. A sampler failure is retained separately.

Synchronous evidence writes add overhead to a worker's wall clock. Capture wall
time and wrapper timing are observable measurements, not an estimate of an
unobserved uninstrumented run. Do not compare instrumented timing to historical
timing as if the collection contracts were identical.

## Offline verification

Only injected offline delegates and synthetic temporary Git repositories are
used by the new tests. One integration check runs the existing bounded executor
against scripted model/query/policy doubles with HTTP forbidden. It confirms
three scripted model calls and the two expected tool calls; it produces no
model-performance evidence and invokes no live benchmark.

```sh
python3 -m unittest tests.test_passive_capture -v
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts/passive_capture.py tests/test_passive_capture.py
python3 scripts/check_project_context.py
git diff --check
```

Tests cover the authorization, scope gate, configuration/source/fingerprint
drift (including scope-module removal/change), one-shot entry, failure/return
identity, partial metrics, pre-query SQL persistence, public normalization,
sampler/finalization failures, preflight-only CLI and runtime import isolation.
Hosted CI/CodeQL and a future reviewed live adapter remain separate checks.

Local verification passed **25 focused tests and all 322 repository tests**,
compilation, context protocol and whitespace checks. The
[verification record](../experiments/passive-capture-v2-offline-20261017/verification.json)
preserves exact commands, exit codes and log digests. `src/`, `evals/` and
`configurations/` are unchanged from the base commit. All 20 files in the
historical failed-evidence checksum manifest still agree with their original
digests. Old collector digests are separately recorded; neither was modified.
