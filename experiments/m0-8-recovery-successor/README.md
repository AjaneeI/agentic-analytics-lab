# M0.8 Final Recovery Successor

Status: preregistration design. No successor Hermes invocation is permitted
until the failed M0.8 evidence, this design, the one-line behavioral prompt
intervention, and tests are committed, tagged, pushed, and recorded on issue
#89.

## Evidence-supported blocker

M0.8 proved the parent boundary works: one delegation, one child, no parent
evidence calls, no second worker, and post-success `delegate_task` retirement.
The child failed because its first response batched two SQL calls before policy.
The two-call evidence budget was exhausted, policy retrieval was blocked, and
the child then repeated SQL five more times.

## Single intervention

Change only the existing child worker instruction to require:

1. call `retrieve_policy` exactly once first;
2. wait for its result;
3. call `query_clickhouse` exactly once;
4. do not batch the two calls or repeat either tool.

The validated tool descriptions, model, context, temperature, parent prompt,
validator, dataset, evidence budget, one-worker enforcement, retirement patch,
task, scorer, reference, and paid-fallback policy remain unchanged.

## Acceptance and stop rule

Acceptance is identical to M0.8: one parent delegation, one child, one
successful policy retrieval followed by one successful query, no failed or
extra calls, no intervention, deterministic score acceptance, independent raw
verification, zero retry, zero Ajanee intervention, and `$0` paid spend.

This is the final M0 recovery in this run. If it fails, M0 remains incomplete
and M1-M11 implementation stops. If it passes, M0 is sufficient for bounded
use and M1 may begin.

## Execution after freeze

```sh
set -a
source /Users/ajaneeigharo/Projects/agentic-analytics-lab/.env
set +a
python3 experiments/m0-8-recovery-successor/run_validation.py \
  --output-dir experiments/results/m0-8-recovery-successor-2026-10-06
```
