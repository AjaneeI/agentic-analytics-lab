# M0.8 final recovery successor — result

Verdict: **FAIL**. M0 is not sufficient for bounded use, and M1 is not
authorized by this evidence.

The preregistered successor ran once from commit `4da9586`, tag
`m0-8-recovery-successor-v1`, with zero retries, zero human intervention, and
zero incremental paid spend. Frozen-state and live-environment checks passed
before execution, and the frozen state passed again afterward.

## What held

- Hermes made exactly one delegation and created exactly one child.
- No second worker or extra delegation occurred.
- `delegate_task` was removed from all three post-child parent requests.
- The child retrieved the blocker-rate policy first, as instructed.
- The child's SQL used the exact fully qualified approved table and the correct
  blocker-rate formula.

## What failed

The child's first SQL call returned `HTTP Error 404: Not Found`, despite the
parent-process live preflight succeeding. The child then made four additional
SQL attempts despite the exactly-once instruction; enforcement blocked all
four. After the child returned, the parent made two forbidden SQL attempts;
enforcement blocked both. Only the policy call succeeded.

The final response was incomplete and the deterministic scorer rejected the
run before scoring because there were not exactly two evidence-tool calls.

`orchestration.json` reports seven enforcement interventions and six parent
evidence calls. The semantic breakdown from raw events is one infrastructure
tool error plus six enforcement blocks. Raw request session IDs establish six
child evidence attempts and two parent evidence attempts; blocked child events
omit `delegated_child`, so the generated parent-attribution field is not
authoritative.

## Failure classes

- Infrastructure/runtime: delegated-child ClickHouse HTTP 404 while the live
  parent preflight passed.
- Model instruction-following: four child retries after the exactly-once call.
- Orchestration/decomposition: two parent evidence attempts after child return.
- Enforcement intervention: four child budget blocks and two parent-boundary
  blocks.

## Decision

The preregistered stop rule applies. Do not implement M1-M11 in this run and
do not invoke Hermes again to seek a pass. The smallest next experiment is a
model-free subprocess probe comparing ClickHouse configuration and request
construction in the successful parent preflight and delegated-child runtime,
followed by a deterministic regression test before any new model call.

This result does not prove that Qwen or Hermes is generally incapable. It
shows that the current frozen end-to-end path is not yet reliable enough to be
Ajanee's primary local interface.
