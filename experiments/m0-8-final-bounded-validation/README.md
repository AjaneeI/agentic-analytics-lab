# M0.8 Final Bounded Hermes Validation

Status: frozen design. No M0.8 Hermes invocation is permitted until this
directory, the passing M0.7 recovery evidence, and the validated plugin source
are committed, tagged, pushed, recorded on issue #89, and installed into the
isolated `localbenchmark` profile with a verified hash.

## Workflow

Hermes receives the existing SB-D01 request:

> Identify the highest blocker-rate team and interpret it using the KPI
> definition without claiming causality.

The parent must make exactly one delegation containing one child. Only the
child may call `query_clickhouse` and `retrieve_policy`; each must succeed on
its first attempt. The parent may not perform evidence work. Existing
one-worker/no-concurrency enforcement and post-success `delegate_task`
retirement remain active.

The child receives the existing bounded System Benchmark worker prompt and
the validated model-visible tool descriptions. The local Qwen model, context,
temperature, dataset, validator, scorer, reference, and security boundaries
remain unchanged. There is no paid or cloud fallback.

## Acceptance

M0.8 passes only if all of the following hold in one run with zero retries:

- process exit zero;
- exactly one valid delegation and one successful child;
- no extra delegation, second worker, concurrency, parent evidence call, or
  enforcement intervention;
- `delegate_task` is present in the first parent request and absent from every
  later parent request;
- exactly one successful child `query_clickhouse` call and one successful
  child `retrieve_policy` call;
- the unchanged `SystemBenchmarkResponse` scorer accepts the response;
- independent reconstruction from raw tool events matches the scorer;
- Ajanee intervention is zero;
- incremental paid spend is `$0`.

Repository request copies redact only `request.headers.Authorization`. Local
originals remain untouched; original and sanitized hashes are preserved.

Passing marks **M0 foundation sufficient for bounded use** and permits M1.
Failing preserves the new blocker and stops dependent M1 work in this run.

## Execution after freeze and installed-state verification

```sh
set -a
source /Users/ajaneeigharo/Projects/agentic-analytics-lab/.env
set +a
python3 experiments/m0-8-final-bounded-validation/run_validation.py \
  --output-dir experiments/results/m0-8-final-bounded-validation-2026-10-06
```
