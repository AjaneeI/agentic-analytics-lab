# M0 Final Runtime Validation

Status: preregistered design. No Qwen or Hermes invocation is permitted until
this design and the deterministic diagnostic repair are committed, tagged,
pushed, and recorded on issue #89.

## Purpose

Run exactly one fresh bounded Hermes validation after repairing the error
classification defect identified by the model-free ClickHouse diagnostic.
This is a validation of the existing M0 foundation, not a new M0.x tuning
chain.

Hermes receives the unchanged SB-D01 request:

> Identify the highest blocker-rate team and interpret it using the KPI
> definition without claiming causality.

## Frozen controls

- same local `hermes-local:qwen3.5-9b` model and 65,536-token context;
- same temperature 0 runtime configuration;
- same parent and child prompts from the M0.8 recovery successor;
- same `query_clickhouse` and `retrieve_policy` model-visible contracts;
- same unchanged read-only validator and SQL semantics;
- same one-worker/no-concurrency enforcement;
- same post-success `delegate_task` retirement;
- same deterministic scorer, reference, dataset, and response contract;
- zero retries, zero prompt repair, and $0 paid spend.

The only implementation change since the failed run is that ClickHouse HTTP
errors retain bounded server error detail. The wrapper does not repair SQL or
retry a failed query.

## Acceptance and stop rule

The one run passes only if the existing deterministic score passes, exactly
one delegation produces exactly one child, exactly one policy call followed by
exactly one query succeeds, no extra/parent evidence calls or enforcement
interventions occur, post-success delegation retirement is proven from raw
parent requests, independent verification passes, and paid spend remains $0.

If accepted, M0 is sufficient for bounded use and M1 planning may begin; this
does not establish general reliability or unrestricted autonomy. If it fails,
the raw failure is preserved and work stops with the blocker classified from
the new evidence. No retry is authorized.

## Frozen execution command

```sh
set -a
source /Users/ajaneeigharo/Projects/agentic-analytics-lab/.env
set +a
python3 experiments/m0-8-recovery-successor/run_validation.py \
  --manifest experiments/m0-final-runtime-validation/frozen-state.json \
  --output-dir experiments/results/m0-final-runtime-validation-2026-10-06
```
