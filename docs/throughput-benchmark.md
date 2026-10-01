# Bounded throughput experiment

This lane measures **useful validated work per unit time** without changing the
official Q1-Q6 evidentiary benchmark.

## Metric

The primary metric is:

`validated_tasks_per_minute = task-successful requests / suite wall-clock minutes`

Raw requests per minute is reported separately so faster failures cannot look
like better system performance.

## Isolation

Each concurrent request receives a fresh agent instance. Mutable run state such
as `last_run_metrics`, tool traces, and token accounting is not shared between
workers.

The same deterministic `run_case` scorer validates every request before it can
count as useful throughput.

## Timing

The artifact separates:

- suite wall-clock duration
- per-request service latency
- queue wait before a worker starts

It reports median and P95 service latency and queue wait.

## Bounded sweep

The default sweep is concurrency 1, 2, 4, and 6. The runner stops increasing
concurrency when any of these are observed relative to the previous level:

- validated tasks per minute does not improve
- task-success rate falls
- execution errors increase

The best observed concurrency is the completed level with the highest validated
tasks per minute, with lower concurrency preferred on an exact tie.

## Claim boundary

This is a load/systems experiment. Reusing Q1-Q6 here does not create additional
official benchmark runs and does not alter the accepted exactly-three-run
methodology for evidentiary architecture comparison.

The first live sweep should be reviewed before any concurrency recommendation is
published. Hardware and Ollama server configuration are part of the throughput
environment and must be recorded alongside results.
