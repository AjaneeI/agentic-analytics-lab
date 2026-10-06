# M0.5 Capability Reliability results

Execution state: completed once from `m0-5-capability-reliability-v1` at
`33b6fe2aa5b484b87efc9321077471c568ebaf88`. No case was retried or repaired.

## Study A — PASS (4/4; threshold 4/4)

All four frozen Qwen attempts produced exactly one `query_clickhouse` call.
Every SQL statement used the fully qualified
`agentic_analytics.delivery_work_items` table, passed the unchanged validator,
executed successfully, and returned the exact preregistered rows.

This evidence distinguishes the unqualified-table failure in #84 from a
systematic failure across these four basic SQL shapes. It does not establish
general SQL reliability or explain why the #84 prompt failed.

## Study B — FAIL (2/3; threshold 3/3)

- `B1_LITERAL`: accepted; one delegation, one successful child, exact marker.
- `B2_EXTRACT`: accepted; one delegation, one successful child, exact marker.
- `B3_COMPARE`: rejected by the strict orchestration contract. Hermes launched
  one child successfully and produced the exact marker, then attempted the
  identical delegation a second time. The existing budget blocked the second
  attempt before another child launched.

Across Study B, all three requested final markers were correct, all three
processes exited zero, and three legitimate workers completed. One extra
delegation was attempted; it generated two enforcement events (blocked pre and
post), launched no second worker, and performed no parent evidence work.

Supported classification for `B3_COMPARE`:

- `orchestration_decomposition`: the parent repeated an already completed
  delegation instead of proceeding directly to its final response;
- `enforcement_intervention`: the hard delegate budget blocked the repeated
  attempt and prevented a second worker.

There is no observed infrastructure/runtime failure. Because hidden reasoning
is not inspected, the evidence does not establish why the parent repeated the
call.

## Decision

M0.5 does not support readiness for M0.6 because both preregistered gates did
not pass. The current M0.5 study is closed and must not be rerun or tuned.

Smallest testable intervention: after the first successful delegate completion,
remove `delegate_task` from the parent model-visible tools for the remaining
turns. Change no prompt or result text. Keep the model, three Study B cases,
child goals, one-worker enforcement, temperature, context, retry policy, and
3/3 threshold unchanged.

Next experiment: preregister a B-only successor that applies only this
post-success capability retirement and compares its results descriptively with
the frozen M0.5 Study B baseline. Before live execution, deterministic tests
must prove that the capability is visible before the first delegation, absent
after one successful completion, and that a duplicate attempt still fails
closed without launching a child. The live gate remains 3/3 with exactly one
attempted delegation, one child, exact final marker, zero parent work, and zero
enforcement intervention. Define and freeze that experiment separately; do not
execute it as part of M0.5.

## Interpretation boundary

Study A characterizes four frozen SQL shapes. Study B characterizes three
trivial bounded delegation requests. The results do not establish general model
reliability, general Hermes reliability, architecture superiority, or M0.6
readiness.
