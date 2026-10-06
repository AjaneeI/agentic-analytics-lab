# Hermes Personal Ops roadmap — morning status

Date: 2026-10-06

Roadmap branch: `hermes-personal-ops-roadmap`

Tracking issue: [#89](https://github.com/AjaneeI/agentic-analytics-lab/issues/89)

Draft evidence PR: [#90](https://github.com/AjaneeI/agentic-analytics-lab/pull/90), stacked on the M0.6 branch

Historical evidence preserved: issues #73, #82, #84, #85, #86, #87 and draft PRs #83/#88

Incremental paid spend: **$0**

## Diagnostic-gate addendum

The authorized model-free diagnostic found that the prior delegated-child 404
was ClickHouse code 47 for nonexistent `team_id`, not evidence of different
endpoint, auth, profile, or request-adapter behavior. A bounded error-reporting
fix now preserves the server code and detail; it does not repair SQL, add a
retry, or change the tool contract. RED→GREEN verification passed, including
349/349 repository tests.

One new unchanged-controls validation was frozen at `f92f709` / tag
`m0-final-runtime-validation-v1` and executed exactly once. It failed: the
child again used `team_id`; its first query timed out after the successful
parent preflight; four further child evidence attempts were budget-blocked;
and the final response was incomplete fenced JSON. One delegation/one child
and post-child delegation retirement held. Runtime was 628.646 seconds, with
zero retries, intervention, or paid spend.

M0 therefore remains incomplete and M1 remains unauthorized. Per the frozen
stop rule, no new M0.x experiment or M1 planning is started in this run. Raw
evidence is under
`experiments/results/m0-final-runtime-validation-2026-10-06` and the durable
decision is recorded on issue #89.

## Outcome

The roadmap stopped at the M0 reliability gate. M0.7 proved that local Qwen
can produce compliant ClickHouse calls after the smallest tool-contract
clarification, but two realistic M0.8 Hermes workflows failed. The final
preregistered recovery exposed a delegated-child ClickHouse HTTP 404 plus
instruction-following and parent-orchestration failures. The stop rule was
applied; no downstream product work was represented as ready.

Hermes Desktop is therefore **not yet verified as Ajanee's primary local
interface**.

## Milestone status

| Milestone | Status | Evidence / reason |
| --- | --- | --- |
| M0 — reliable foundation | **Failed** | M0.7 recovery passed 3/3, but the final M0.8 workflow failed the end-to-end exit criterion. Evidence commits: `13397fd`, `4d5ec3f`, `8cd4cef`, `4da9586`, `294efa2`. |
| M1 — Desktop Personal Ops | **Deferred because evidence does not justify it** | M0 did not authorize M1. No Desktop UX, context layer, policy layer, `ask_user`, or ACS pilot was added. |
| M2 — Engineering Operator | **Deferred because evidence does not justify it** | Depends on verified M1 behavior. No ASSERT pilot was run. |
| M3 — Evidence & Research Operator | **Deferred because evidence does not justify it** | Depends on the reliable foundation and product contracts. |
| M4 — Phone + Voice | **Deferred because evidence does not justify it** | No networking, public exposure, Tailscale setup, OAuth, or OS-permission change was attempted. |
| M5 — Async Execution | **Deferred because evidence does not justify it** | The synchronous bounded workflow is not yet reliable. |
| M6 — Useful Integrations | **Deferred because evidence does not justify it** | No new OAuth, permissions, or integrations were added. |
| M7 — Broader Personal Operations | **Deferred because evidence does not justify it** | Depends on M1-M6 contracts and reliability. |
| M8 — Durable Memory | **Deferred because evidence does not justify it** | No repeated product-usage memory failure has been established. |
| M9 — Intelligent Routing | **Deferred because evidence does not justify it** | Current evidence is insufficient to define reliable production routing. |
| M10 — Multi-Agent Capability | **Deferred because evidence does not justify it** | The one-child path is not yet reliable; expanding beyond it would be unsafe. |
| M11 — Proactive Hermes | **Deferred because evidence does not justify it** | Open-ended/proactive behavior remains disabled. |

## What is currently operational

- Local Qwen3.5-9B generated three of three validator-compliant, fully
  qualified, formula-correct ClickHouse calls in the frozen M0.7 recovery.
- Hermes enforced exactly one delegation and one child in both M0.8 runs.
- No second worker or extra delegation launched.
- `delegate_task` was absent from every post-child parent request in the final
  run.
- Read-only SQL validation, the two-call evidence budget, and the parent
  evidence boundary failed closed.
- Raw evidence is preserved with only Authorization fields redacted from
  repository copies; original request dumps remain untouched.

These are bounded components, not proof that the Desktop workflow is ready.

## Final M0.8 recovery evidence

- Frozen design: commit `4da9586`, tag `m0-8-recovery-successor-v1`.
- Result evidence: commit `294efa2`.
- One execution, 416.246 seconds, zero retries, zero human intervention.
- Fixed-state and live-environment preflight passed; fixed-state postflight
  passed.
- Child sequence: policy success; one qualified/formula-correct SQL call
  failed HTTP 404; four repeat SQL calls were budget-blocked.
- Parent sequence: exactly one delegation; then two forbidden SQL attempts,
  both blocked.
- Deterministic scoring: ineligible/unscored because the trajectory did not
  contain exactly two evidence-tool calls.
- Failure classes: infrastructure/runtime, model instruction-following,
  orchestration/decomposition, and enforcement intervention.

The generated orchestration summary overattributes blocked child events to the
parent because those events omit `delegated_child`. Raw request session IDs
establish six child evidence attempts and two parent attempts and are the
authoritative attribution source.

## Verification

- Baseline at `abe516e`: 339/339 repository tests passed.
- After M0.7 recovery: 343/343 passed.
- Before first M0.8 execution: 346/346 passed.
- Before final recovery: 348/348 passed.
- Final recovery preflight/postflight hash and profile checks: passed.
- All frozen model runs were executed once with no retry-until-pass behavior.

## ACS and ASSERT

- ACS pilot: **deferred**. M1 was not authorized, so no governance layer was
  added or evaluated.
- ASSERT pilot: **deferred**. M2 was not reached, so no evaluation machinery
  was added speculatively.

## Security and authorization

No paid service, credential change, public exposure, port opening, external
message, production deployment, new broad permission, or destructive action
occurred. No Ajanee authorization is currently blocking the recorded M0
result.

Notion current-state retrieval could not be completed because the connector's
required access-discovery prerequisite was unavailable in this session. The
explicit roadmap brief, GitHub lineage, and verified repository state were
used instead; no Notion state was overwritten or inferred.

## Remaining blocker and next experiment

The immediate blocker is the mismatch between a successful parent-process live
ClickHouse preflight and the delegated child's HTTP 404 for valid SQL.

The next experiment should be model-free: compare ClickHouse environment and
request construction in the parent preflight and delegated-child subprocess,
then add a deterministic regression test for the observed discrepancy. Do not
invoke Hermes again until that layer is explained. Only after the deterministic
path passes should a new, separately preregistered bounded Hermes validation be
considered.

## What Ajanee should do tomorrow morning

1. Open [issue #89](https://github.com/AjaneeI/agentic-analytics-lab/issues/89)
   or draft [PR #90](https://github.com/AjaneeI/agentic-analytics-lab/pull/90)
   and review the terminal M0 result. No Terminal work is needed.
2. If you want to continue, authorize the next work session to perform only the
   model-free ClickHouse parent/child runtime diagnostic described above.
3. Do **not** use the two planned Hermes Desktop prompts as acceptance tests
   yet. The current evidence says they are premature:
   - “Good morning. Tell me what you accomplished overnight, what needs me, and
     what you recommend we do today.”
   - “Check Agentic Analytics Lab, tell me the highest-value safe next step,
     and move it forward as far as you safely can.”

Those become the correct first two user tests only after M0 passes and the M1
Desktop path is implemented and independently verified.
