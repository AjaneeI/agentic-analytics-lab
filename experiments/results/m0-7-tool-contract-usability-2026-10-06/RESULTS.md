# M0.7 Tool-Contract Usability Result

M0.7 failed its preregistered 3/3 threshold: 0/3 attempts were accepted. The
run is preserved without repair or retry.

## What changed

Only the model-visible `query_clickhouse` description was changed to state
that `agentic_analytics.delivery_work_items` is the only approved table and
that SQL must use that exact fully qualified name. The model, context,
temperature, validator, dataset, and retry policy were unchanged.

## Observed behavior

- `M07_HIGHEST_RATE`: Qwen produced one tool call using the exact fully
  qualified table. The unchanged validator accepted it, but the SQL treated
  `blocked_pct` as a source column rather than computing the rate. Tool
  execution also returned HTTP 401 because the execution shell referenced a
  nonexistent environment file.
- `M07_LOWEST_RATE`: the local Ollama request returned HTTP 500 and produced no
  model response.
- `M07_ALL_RATES`: Qwen again used the exact fully qualified table and passed
  validation, but again treated `blocked_pct` as a source column. Execution
  returned the same credential-related HTTP 401.

The qualification intervention therefore improved the observable table-name
behavior in both SQL-bearing attempts (2/2), but it did not establish the
preregistered end-to-end capability. The schema contains `blocked`, not
`blocked_pct`; both preserved SQL statements are semantically invalid for the
requested calculation.

## Decision

M0.8 is not authorized by this evidence. The smallest successor will change
only the model-visible blocker-rate instruction to require
`100 * SUM(blocked) / COUNT(*)` (or an equivalent expression) and reserve
`blocked_pct` for the result alias. It will also fail closed before model
invocation unless the existing local ClickHouse environment and a live
read-only preflight are valid. The original M0.7 run will not be rerun.

Incremental paid spend remained `$0`; retries and Ajanee intervention were
zero.
