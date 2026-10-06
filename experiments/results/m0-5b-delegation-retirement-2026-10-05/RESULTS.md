# M0.5B Results — Post-success Delegation Retirement

## Outcome

The preregistered B-only successor passed its 3/3 threshold. Study A was not
rerun; its issue #85 result remains frozen at 4/4. The original M0.5 Study B
result remains 2/3 and is not overwritten.

| Case | Delegations | Children | Extra attempts | Interventions | Parent work | Parent tools, request 1 → 2 | Final |
|---|---:|---:|---:|---:|---:|---|---|
| B1_LITERAL | 1 | 1 | 0 | 0 | 0 | 3 tools with `delegate_task` → 2 tools without it | `M05_ALPHA_OK` |
| B2_EXTRACT | 1 | 1 | 0 | 0 | 0 | 3 tools with `delegate_task` → 2 tools without it | `M05_OWNER_DATA` |
| B3_COMPARE | 1 | 1 | 0 | 0 | 0 | 3 tools with `delegate_task` → 2 tools without it | `M05_MAX_7` |

All three processes exited zero. Deterministic acceptance was true for every
case. Total measured case time was 770.742 seconds. Nine redacted raw request
payloads were preserved: for each case, two parent requests and one child
request. Recorded estimated paid cost was `$0.00`.

## Failure-pattern analysis

No successor case produced a model-instruction-following, tool-contract,
orchestration/decomposition, enforcement-intervention, infrastructure/runtime,
or other supported failure. In particular, B3 did not reproduce the original
post-success duplicate delegation. This does not erase the original B3 failure;
it supports the preregistered mechanism: the parent could not select
`delegate_task` after the completed child because the tool was absent from the
second parent request.

The unchanged plugin hard guard remained installed and hash-verified. It did
not need to intervene in the successor, but it still deterministically blocks
a directly attempted second delegation and therefore remains the independent
no-second-worker backstop.

## What this demonstrates

The smallest tested runtime intervention repaired the observed duplicate-
delegation failure on B1, B2, and B3 under the frozen local Qwen/Hermes profile.
It preserved the child result, exact final marker, one-worker constraint, and
zero-paid-spend boundary.

## What this does not demonstrate

It does not establish general Hermes reliability, model superiority, broader
task-delegation quality, population-level rates, or readiness for unrestricted
autonomy. It also does not modify or re-evaluate Study A, SQL contracts,
validators, prompts, model configuration, or Hermes architecture beyond the
bounded parent tool-surface change.

## Decision

The preregistered M0.5B gate passes and supports recommending progression to
the next M0 evidence gate. That next gate is not executed in this run.

Reproducibility anchors:

- preregistration commit: `22bc26bd4e36b9e063514f47a4494532deace4a0`
- freeze tag: `m0-5b-delegation-retirement-v1`
- frozen local Hermes source commit: `2ec7703012e5e356b8df383026397160ed9b0bed`
- patched runtime SHA-256: `df65f6506c03d8533ee695a1266cc23739b4d0ad43715d0408e79fb8a2e35405`
- summary SHA-256: `86d2a8e2bc0362a4504439d15e953a371b5f91f24b91b83432a75f09984374f9`
