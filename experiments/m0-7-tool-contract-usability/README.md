# M0.7 Tool-Contract Usability

Status: preregistration design. No M0.7 model invocation is permitted until
this directory, the two model-visible tool descriptions, and the deterministic
test are committed, tagged, pushed, and recorded on the roadmap GitHub issue.

## Purpose

Test the smallest intervention supported by M0.6: make the existing
`query_clickhouse` description explicitly state both that the only approved
table is `agentic_analytics.delivery_work_items` and that SQL passed to the
tool must reference that exact fully qualified name.

Only the model-visible description changes. The Qwen model, context,
temperature, validator, dataset, SQL execution, prompt behavior, and security
boundaries remain unchanged. There is no SQL normalization, repair, retry, or
validator relaxation.

## Design

Hypothesis: with the clarified tool description, the frozen local Qwen setup
will produce a first-response `query_clickhouse` call whose unedited SQL passes
the existing validator and returns the exact expected rows for each of three
realistic blocker-rate requests.

Sample size: three distinct cases. This is the smallest set that tests the
known qualification failure across a highest-rate ranking, a lowest-rate
ranking, and a complete ordered team breakdown without spending local compute
on repeated equivalent prompts.

Threshold: 3/3 accepted. This is an engineering gate, not a population
reliability estimate. A single first-call qualification failure means the
wording is not yet reliable enough for M0.8.

Frozen cases:

1. `M07_HIGHEST_RATE`: highest blocker-rate team and percentage.
2. `M07_LOWEST_RATE`: lowest blocker-rate team and percentage.
3. `M07_ALL_RATES`: every team's blocker percentage in descending order.

The prompts require the approved dataset but do not contain SQL, the fully
qualified table name, or expected answers. Each case receives one model call
and exposes only `query_clickhouse`.

Acceptance requires:

- response type `tool_call`;
- tool name `query_clickhouse`;
- non-empty SQL;
- unchanged `validate_read_only` acceptance;
- successful execution against the existing dataset;
- exact equality with the preregistered result rows.

Every raw response, request message, exposed tool schema, validated SQL,
result row, timing, deterministic classification, and evidence hash is
preserved. Failures are not repaired or rerun.

Passing M0.7 supports proceeding to one M0.8 bounded Hermes workflow with the
same validated description. It does not establish general SQL reliability,
Hermes reliability, architecture superiority, or M1 readiness by itself.

## Execution after freeze

```sh
set -a
source .env
set +a
python3 experiments/m0-7-tool-contract-usability/run_study.py \
  --output-dir experiments/results/m0-7-tool-contract-usability-2026-10-06
```
