# Prospective scheduling control v1 — inactive

The preserved Phase 2 failure records runnable CPU scheduling delay. The exact
interferer and a sufficient remedy remain unknown. This proposal supplies a
concrete model-free observation protocol and a bounded collector, rather than
changing an experimental timeout or guessing a service to stop.

The protocol is `protocol.json`. `observer.py` defaults to printing that protocol
without contacting services or creating evidence. No new diagnostic or Treatment A
has been executed for this proposal. The collector is not imported by benchmark
execution and does not change its authorization configuration.

## Exact proposed check

One synthetic query computes the sum of squares of integers 0 through 499
(41,541,750), returning the effective fixed SQL settings in that same request.
It reads `numbers(500)`, with no benchmark table, task or reference. If it returns
the expected value and unchanged settings, exactly one immediately following
read of existing `system.query_log` targets its new query ID and execution window.
There is no force-flush, availability retry, expanded window or fallback query.
Missing asynchronous log metadata is an inconclusive terminal observation.

The collector retains readonly=1, 10 seconds/server request, 15 seconds/socket,
128 MiB/query, two threads, 10,000 rows/10 MiB read, 1,000 result rows/break, and
compile_expressions=0. Diagnostic-only outer limits are two requests, 40 seconds
for the worker plus at most one second to confirm its termination, and 32 KiB
collected output (28 KiB data plus 4 KiB reserved for receipt/seal). Each response
body and cumulative header capture are capped at 4 KiB. Reaching a cap is a
terminal failure; no partial response is accepted as success.

## Resource window and scope

Before any live launch, review the exact commit/protocol, independently verify a
prospective owner-coordination receipt, and attach bounded contemporaneous
host/VM observations with their provenance. A reference string in a JSON file is
not capacity authentication. Idle status, one memory reading or an unloaded
model is insufficient. No arbitrary load, PSI or free-memory threshold is adopted.
The current shared-resource handoff does not establish adequate headroom.

Resource actions are **none**: no service stop/restart, model loading, affinity,
priority, memory allocation, warm-up, configuration or permissions change. A
voluntary scheduling agreement avoids planned competing work without pretending
to remove unknown background load. Unresolved capacity means no launch.

This collector intentionally uses a separate fixed diagnostic read-only SQL path.
The benchmark SQL allowlist is unchanged; no table-function capability is added
to the benchmark tool. Neither this proposal nor its resource-window prerequisite
changes a consumed authorization or grants another Treatment A attempt.

## Evidence and interpretation

The private output directory is created exclusively (0700), with separate
exclusive parent/worker consumption markers. Files use 0600 and exclusive writes.
Raw returned response status, headers and bodies, exact new SQL and settings,
elapsed times, terminal errors, context receipt and SHA-256 fingerprints are
retained. Credentials and the outgoing Authorization header are not recorded.
Do not publish this raw directory; review a separate redacted projection first.

Profile counters aggregate query threads. Missing keys remain unknown; they are
never filled with zeros or divided by wall time. The query log's Settings map is
not a complete effective-default snapshot; same-request getSetting results are
the effective settings check. Host/VM clock differences and asynchronous logging
can make metadata unavailable. A hard kill can lose bytes still held in memory
or leave partial files; a sealed capture is not proof of a complete wire trace.

Scheduling wait on unrelated work supports shared delay in the **new window**.
A fast control cannot distinguish transient historical contention from
query-specific delay. Neither outcome identifies a named interferer, establishes
a fix for the failed query, or qualifies Phase 2. There is no original query
replay, benchmark score, comparison, historical rescoring or held-out evaluation.

## Validation and review

The offline tests exercise exclusive reservation, missing-window refusal,
partial-header retention, cumulative limits, exact scoped metadata SQL, missing
counter handling, zero-retry stopping, a two-response scripted HTTP exchange,
unchanged wire limits, credential omission, default CLI and parent timeout/seal.
Tests use scripted transports; they cannot establish actual server acceptance,
query-log availability, OS deadline enforcement, safe capacity or timeout repair.
See `validation/revision1/receipt.json` and the preserved logs for exact source hashes and
Python versions. The full repository suite is not rerun: it includes existing
benchmark-SQL SQLite characterizations and statistical simulation paths, which
would duplicate completed evidence or cross this continuation's execution limits.
Focused SQL-security and existing diagnostic-header regressions are included.

Independent Work coordinator acceptance review follows the exact published
commit. Any reviewer findings are engineering corrections only; the coordinator
cannot grant research-method changes, phase acceptance or a new experiment.

## Proposed invocation — not executed

A sealed delivery record supplies the exact checkout commit and protocol hash.
The invocation is:

```text
python3.11 -B proposals/phase2-scheduling-control-v1/observer.py --run \
  --expected-commit <published immutable commit> \
  --protocol-sha256 <published protocol SHA256> \
  --context <private prospectively verified window receipt> \
  --out <new private output path outside the checkout>
```

Existing local read-only credentials must already be inherited in the environment;
the collector does not discover credentials or change access. Missing prerequisites
consume no observation launch. After reservation, all failures consume the one
launch, including unavailable credentials or a failed child launch. Do not run
`--worker` directly; it is the parent's internal process entry and uses an
exclusive worker marker. No automatic retry or replacement is provided.

## Independent review corrections, revision1

The initial reviewed commit532703e remains preserved with its original validation logs. R119-01 independently specifies the preserved effective setting string `false`, while request encoding remains `0`; no parser coercion or general response normalization is added. Happy-path fixtures now use PR112 evidence rather than copying the request dictionary. True, missing and malformed settings stop before metadata. R119-02 seals a credential-free launch record before the worker, binding source/protocol/helper/contract/config/context/invocation and UTC. Offline success, launch failure, timeout and pin-refusal cases verify this under the existing32KiB cap. No live settings probe or experiment was needed.
