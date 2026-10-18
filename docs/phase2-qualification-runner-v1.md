# Inactive Phase 2 qualification runner v1

`scripts/qualify_phase2_once.py` wires the existing `BoundedLocalExecutor`,
`run_trial`, pinned SB-D01 task and reference to passive capture v2. This is
offline engineering preparation. The existing combined scope configuration
remains a pending proposal; no owner-approval field or runtime validity gate
is changed. No live model/database call or Treatment A was made here.

The CLI defaults to **source preflight only**: it checks the immutable clean
HEAD, configuration SHA, complete existing contract fingerprint, approved query
tool JSON hash and loaded-source identity. It makes no service requests, model
constructor calls, evidence folders or worker entries. It reports unresolved
owner/scope/validity blockers and exits 2 while they remain pending.

The explicit execution path additionally requires a run flag, an approval
reference, configuration ID `phase2-runtime-schema-v1-scope-observation-v1`,
scope version `runtime-sql-scope-v1`, `owner_observation_approval=approved` and
`runtime_offline_validity_gate=passed`. The task loaded from the pinned fixture
must be SB-D01 with oracle metadata, deterministic route, multi-source
capability, exactly the two safe tools and the existing two-call budget. The
user request is passed unchanged from that fixture; reference/expected values
are never added to model input. Current pending configuration cannot enter
this path. Owner approval and the final immutable execution/configuration pin
remain separate from this runner implementation.

Only after these guards, fresh read-only service setup checks the approved local
model name/digest through `/api/tags`, and the 13 delivery columns/types plus
500-row count through the unchanged constrained ClickHouse tool. Only the
approved model's name, digest, size and details are retained. These **two setup
SQL calls are separate from the two benchmark evidence calls**. They do not
warm up inference, unload/change the model or tune any setting. Count/schema
checks do not independently attest every dataset cell.

The existing model client retains temperature 0, `num_predict=512`,
`num_ctx=65536`, timeout 120 seconds and the exact pinned source hash. Session
wrapping checks its actual name/base URL/timeout and actual delivered query
tool hash. The existing six model steps and two evidence calls are unchanged.
Fresh service setup happens inside the eventual guarded invocation; an older
preflight report cannot substitute for it.

Capture creates one new exclusive evidence folder outside the source checkout.
It rechecks source/config pins immediately before the durable invocation marker
and exactly one worker-entry boundary. An existing folder/marker refuses reuse.
There is no retry, reprompt, fallback model, alternate worker, SQL rewrite or
extra evidence query. Before/after snapshots combine OS host observations with
`/api/ps` rows for the approved model only. These shared-service snapshots are
not per-request CPU/GPU/VRAM or peak model-memory measurements.

The setup event records runner/capture source SHA, Python version/executable and
platform, without an environment dump. Service records include fresh UTC times.
The ordinary capture manifest retains configuration/contract/source pins,
partial model/tool metrics, collector errors, resource/timing boundaries and
source postflight. Instrumentation overhead remains part of observed timings.
Loaded-source checks compare every declared contract file, including corpus,
tasks and references, with the pinned checkout; equal Python code alone cannot
qualify another checkout whose retriever corpus differs.

`execution.json` and `raw-result.json` preserve unedited public JSON copies of
the actual existing executor/runner return objects. They do not change returned
objects or scoring. On an exception, no score is manufactured and the identical
original exception is rethrown. `error.json` retains error class/message and
structured HTTP/server identifiers through the existing public error projection;
full tracebacks and HTTP response bodies are not retained. Public boundary events
and pre-query SQL remain available for partial failures. Failed secondary evidence
writes mark collection incomplete without replacing the delegate outcome.
The JSON-envelope privacy fix filters named private fields in trace copies;
ordinary/opaque text remains unparsed. This is not full raw transport capture.
The CLI reports qualification blocked and exits 2 if final collection is
incomplete, source postflight is invalid/missing or one worker entry is not
established. It leaves the raw result and its task-success field unchanged.

Offline verification uses injected models, query/service transports and resource
samplers in temporary Git repositories. Those fixtures explicitly approve their
own temporary test configurations; they do not edit the real pending proposal.

```sh
python3 -m unittest tests.test_qualify_phase2_once tests.test_passive_capture -v
python3 -m unittest discover -s tests
python3 scripts/check_project_context.py
```

The preserved independent capture review applies to source commit `1a232f4`.
The integrated collector, collector tests, capture documentation and privacy
verification JSON are checked against its exact hashes. `STATUS.md` necessarily
differs because this branch also retains scope-observation context. The original
review report remains unchanged; it does not independently review this new runner.
Independent runner review and owner authorization are required before any actual
Treatment A. No later phase or comparative configuration is accepted here.
