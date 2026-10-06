# M0.5 Capability Reliability Study

Status: preregistration design; no M0.5 model invocation is permitted until
this directory is committed, tagged, published, and recorded in a successor
GitHub issue.

This study characterizes the two behavioral failures preserved in issue #84.
It does not reinterpret issues #73, #82, or #84 and does not modify the model,
validator, tool contracts, Hermes architecture, benchmark prompts, or scoring.

## Common controls

- incremental paid spend: `$0`
- model: `hermes-local:qwen3.5-9b`
- Ollama context: `65,536`
- sampling temperature: `0`
- one scheduled attempt per frozen case
- no retry after failure
- no normalization, repair, validator relaxation, or prompt change after freeze
- every raw request, response, event, stdout, stderr, usage record, and
  deterministic decision is preserved
- the runner refuses an existing evidence directory

The exact runtime identities, file hashes, cases, prompts, thresholds, and
evidence paths are machine-readable in `frozen-state.json`.

## Study A — Qwen SQL-contract robustness

Hypothesis: the current frozen Qwen setup can translate realistic questions
about the approved delivery dataset into one `query_clickhouse` call whose SQL
passes the unchanged read-only validator and returns the preregistered rows.

Sample size: four distinct cases. This is the smallest useful set that covers
four materially different SQL shapes: whole-table aggregation, grouped ranking,
conditional aggregation, and grouped enumeration. Repeating one prompt would
measure repetition rather than realistic task variation; more cases would add
local inference cost before these four basic shapes are known to be reliable.

Threshold: 4/4 cases accepted. With only four cases, a weaker threshold would
label a known basic-shape failure as readiness. This is an engineering gate,
not an estimate of population accuracy.

Frozen cases:

1. `A1_TOTAL_COUNT`: ask for the total item count, returned as `row_count`.
2. `A2_LARGEST_TEAM`: ask which team owns the most items and its count,
   returned as `team` and `item_count`.
3. `A3_CRITICAL_COUNT`: ask for the critical-priority item count, returned as
   `critical_count`.
4. `A4_STATUS_COUNTS`: ask for counts by status sorted by status, returned as
   `status` and `item_count`.

Each task requires the approved dataset but does not provide SQL. Acceptance
requires exactly one model response of type `tool_call`, tool name
`query_clickhouse`, a non-empty `sql` argument, acceptance by the existing
`validate_read_only`, successful execution, and exact equality with the frozen
expected rows. No second model turn is allowed.

Allowed tool: the existing `query_clickhouse` specification only.

## Study B — Hermes single-task delegation robustness

Hypothesis: Hermes can translate each bounded request into exactly one
`delegate_task` spawn containing exactly one child, receive its result, and
complete with the exact requested marker without parent tool work or an
enforcement intervention.

Sample size: three distinct cases. This is the smallest useful set that varies
the child task across literal return, inline-field extraction, and a tiny
comparison while keeping child work trivial enough that the measured behavior
is delegation rather than domain performance.

Threshold: 3/3 cases accepted. A weaker threshold would accept an observed
single-task orchestration failure in this small gate. This is an engineering
gate, not a population reliability estimate.

Frozen cases:

1. `B1_LITERAL`: one child returns `M05_ALPHA_OK`.
2. `B2_EXTRACT`: one child reads an inline record and returns
   `M05_OWNER_DATA`.
3. `B3_COMPARE`: one child compares two inline integers and returns
   `M05_MAX_7`.

Acceptance per case requires exactly one attempted delegation, a valid
single-task spawn, exactly one successful delegate completion, zero extra
delegations, zero parent evidence-tool attempts, zero enforcement
interventions, process exit zero, and stdout equal to the frozen marker after
outer whitespace removal. The existing hard one-worker/no-concurrency plugin
and profile remain unchanged. No hidden reasoning is inspected.

Allowed parent-visible tools remain exactly `delegate_task`,
`query_clickhouse`, and `retrieve_policy`; the latter two remain forbidden in
the parent by the existing enforcement. The prompt directs the parent to use
only `delegate_task`.

## Classification and interpretation

Deterministic reason codes map to supported categories:

- missing/wrong tool, malformed arguments, or final-marker mismatch:
  `model_instruction_following`
- validator rejection: `tool_contract_understanding`
- malformed/multiple delegation or observable parent work:
  `orchestration_decomposition`
- blocked tool/delegation events: `enforcement_intervention`
- model, process, query, or missing-artifact errors:
  `infrastructure_runtime`

Multiple categories may be recorded when the raw evidence supports them.
Passing both gates permits only a recommendation for M0.6; M0.6 will not run
here. Any failed gate instead produces the smallest evidence-supported next
experiment. This study will not tune and rerun itself.

## Execution

After the authoritative freeze tag and GitHub preregistration exist:

```sh
set -a
source .env
set +a
python3 experiments/m0-5-capability-reliability/run_studies.py \
  --output-dir experiments/results/m0-5-capability-reliability-2026-10-05
```
