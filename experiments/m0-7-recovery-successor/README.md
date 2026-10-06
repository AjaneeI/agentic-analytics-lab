# M0.7 Bounded Recovery Successor

Status: preregistration design. No successor model invocation is permitted
until the design, runner, clarified tool description, original M0.7 evidence,
and tests are committed, tagged, pushed, and recorded on issue #89.

## Why this successor exists

The original M0.7 run is immutable and failed 0/3. Both SQL-bearing responses
used the newly required fully qualified table name, but both treated
`blocked_pct` as a source column. The schema has `blocked`, not `blocked_pct`.
The run also exposed an execution-path defect: the shell sourced a nonexistent
environment file, producing HTTP 401 from ClickHouse, and one Ollama call
returned HTTP 500.

This is not a retry of the original run. It is one bounded successor with the
smallest supported model intervention and an infrastructure guard.

## One model-visible intervention

The `query_clickhouse` description now additionally says:

> For blocker percentage, compute `100 * SUM(blocked) / COUNT(*)` (or an
> equivalent expression) and use `blocked_pct` only as the result alias.

The model, context, temperature, validator, dataset, SQL execution, task
prompts, expected rows, qualification wording, normalization policy, retry
policy, and security boundaries remain unchanged.

## Infrastructure guard

Before the first model call, the runner requires the existing ClickHouse
environment variables and executes one read-only count query. It must return
`row_count=500`. Failure stops the successor before model invocation; it does
not consume or retry a case.

## Frozen gate

- cases: the same three highest/lowest/all blocker-rate requests from M0.7;
- sample size: 3;
- threshold: 3/3 accepted;
- one first-response model call per case;
- allowed tool: `query_clickhouse` only;
- zero retries, SQL repair, normalization, or validator relaxation;
- incremental paid spend: `$0`.

Passing authorizes one M0.8 bounded Hermes validation. Failing stops further
M0/M1 execution in this run and records the remaining blocker without another
model-tuning loop.

## Execution after freeze

```sh
set -a
source /Users/ajaneeigharo/Projects/agentic-analytics-lab/.env
set +a
python3 experiments/m0-7-recovery-successor/run_study.py --preflight-only
python3 experiments/m0-7-recovery-successor/run_study.py \
  --output-dir experiments/results/m0-7-recovery-successor-2026-10-06
```
