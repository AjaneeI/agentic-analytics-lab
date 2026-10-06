# M0.6 Fresh Hermes-vs-Direct SB-D01 Result

## Outcome

M0.6 did not produce an accepted result in either treatment. The evidence does
not support transition to M1 and does not support a Hermes-superiority claim.
No treatment was retried, no output was repaired, fixed-state checks passed
before A, before B, and after B, and incremental paid spend remained $0.
Repository request-dump copies redact only `request.headers.Authorization`;
the untouched local originals and both original/sanitized SHA-256 values are
recorded in `redaction-manifest.json`. Model messages, tool arrays, tool
results, and benchmark outputs are otherwise unchanged.

## Treatment A — direct bounded local path

- result: failed before a score-eligible response;
- deterministic score: not assigned;
- failure: Qwen called `query_clickhouse` with unqualified
  `delivery_work_items`; the unchanged validator required
  `agentic_analytics.delivery_work_items`;
- elapsed: 43.936 seconds;
- observable model calls: 1;
- evidence-tool attempts: 1;
- retries: 0;
- Ajanee intervention: 0.

This is a model instruction-following/tool-contract-understanding failure, not
an infrastructure failure or a scoring failure.

## Treatment B — repaired Hermes path

- result: process exited 0 but returned `disposition=incomplete`; it was not
  score-eligible under the frozen treatment contract;
- deterministic score: not assigned;
- elapsed: 762.717 seconds;
- parent model calls: 7;
- child model calls: 6;
- one valid delegation, one successful child, zero extra delegations, and zero
  second-worker launches;
- evidence-tool attempts: 13 total;
- retries: 0;
- Ajanee intervention: 0;
- incremental paid spend: $0.

The child reproduced Treatment A's unqualified-table SQL failure, successfully
retrieved the KPI policy, then exhausted the two-call evidence budget. Five
later child evidence attempts were blocked. After the child returned an
incomplete response, the parent attempted six forbidden evidence calls; all
were blocked. This is a combined tool-contract, model instruction-following,
orchestration, and enforcement-intervention failure. It is not an
infrastructure/runtime failure.

## Delegation-retirement finding

Post-success `delegate_task` retirement held under the real benchmark. The
first raw parent request exposed `delegate_task`; all six later parent requests
exposed only `query_clickhouse` and `retrieve_policy`. No second delegation was
attempted and no duplicate-delegation intervention was required.

The original generated `treatment-b-orchestration.json` inherited the M0.5B
simple-case rule that exactly two parent requests must exist, so it labels
retirement false when the real benchmark produced seven parent turns. It also
mislabels five child budget-blocked attempts as parent work because those event
rows omit `delegated_child`. `analysis.json` records the deterministic
event-order correction. Benchmark payloads remain unchanged apart from the
documented Authorization-header redaction in repository copies; the benchmark
was not rerun, and the overall failing result and M1 verdict are unaffected.

## Comparison and M1 decision

Neither treatment was accepted, so Ajanee hands-on minutes per accepted result
is undefined. Each treatment required zero Ajanee intervention during its one
scheduled run. Hermes did preserve one-child delegation and retirement, but it
did not produce a valid answer and required twelve validator/enforcement
interventions: one rejected child query, five child budget blocks, and six
blocked parent evidence calls.

Verdict: **M0.6 does not support transition to M1.**

## Next experiment

The smallest shared blocker is Qwen's omission of the fully qualified table
name on the realistic blocker-rate aggregate. The next experiment should be a
preregistered three-case blocker-rate SQL qualification micro-study. Change
only the model-visible `query_clickhouse` wording to say explicitly that SQL
must reference the exact fully qualified table
`agentic_analytics.delivery_work_items`; keep the validator, model, context,
temperature, data, scorer boundaries, and no-normalization rule unchanged.

Use one attempt per case, no retries or repair, and require 3/3 first calls to
pass the unchanged validator and return exact expected rows. Do not rerun M0.6.
Only after that focused intervention passes should a fresh successor A/B be
defined.
