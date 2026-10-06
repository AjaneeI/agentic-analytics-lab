# M0.5B Post-success Delegation Retirement

Status: preregistration design. No M0.5B Hermes invocation is permitted until
this directory and the exact runtime patch are committed, tagged, pushed, and
recorded on a GitHub successor issue cross-linked to issue #85.

## Prior evidence boundary

Issue #85 and draft PR #83 remain authoritative for M0.5. Study A's 4/4 pass
is frozen and out of scope. The original Study B result remains 2/3: B3's
first child completed successfully and returned the correct marker, after
which the parent attempted the identical delegation again; the unchanged hard
enforcement blocked it and no second child launched. This successor does not
reinterpret or overwrite that result.

## Hypothesis and intervention

Hypothesis: after one synchronous child completes successfully in a one-shot
parent whose existing delegation budget is one, removing `delegate_task` from
that parent's model-visible tools for the rest of the run prevents redundant
post-success delegation while preserving the child result and final answer.

The only behavioral change is the exact patch in
`hermes-runtime-post-success-retirement.patch`. It applies at the synchronous
`delegate_task` return boundary. A single completed child retires the tool from
`parent_agent.tools` and `parent_agent.valid_tool_names`; failed children,
background dispatch handles, interactive sessions, and budgets above one do
not. The returned child result is unchanged. The repository-owned plugin's
independent one-worker/no-concurrency enforcement is unchanged and remains the
hard backstop.

## Frozen design

- sample: the same three original M0.5 Study B cases, in the same order
- threshold: 3/3 accepted
- prompts, child goals, and markers: byte-equivalent outputs of the unchanged
  `build_delegation_prompt` contract
- model: `hermes-local:qwen3.5-9b`, Q4_K_M, temperature 0
- context: 65,536
- initial parent-visible tools: exactly `delegate_task`, `query_clickhouse`,
  and `retrieve_policy`
- allowed parent action: one `delegate_task` call with exactly one child
- retries: one scheduled attempt per case; zero reruns after any observed result
- incremental paid spend: `$0`

Cases:

1. `B1_LITERAL`: child returns `M05_ALPHA_OK`.
2. `B2_EXTRACT`: child extracts the owner and returns `M05_OWNER_DATA`.
3. `B3_COMPARE`: child compares 7 and 3 and returns `M05_MAX_7`.

The three-case 3/3 gate is retained because this successor tests one variable
against the exact failure-exposing set. A larger sample would spend local
compute before establishing whether that intervention repairs the observed
mechanism; a weaker threshold would accept a repeated failure in the only
active gate.

## Deterministic acceptance

Each case requires all of the following:

- exactly one attempted valid delegation;
- exactly one successful worker completion and no second worker;
- zero parent evidence-tool work;
- zero enforcement interventions;
- the first parent request exposes `delegate_task`;
- the only follow-up parent request omits `delegate_task`;
- process exit zero and stdout equal to the frozen marker after outer
  whitespace removal.

Every redacted raw request payload, benchmark event, command, prompt, stdout,
stderr, usage record, timing, evaluation, and SHA-256 index is preserved. A
missing or ambiguous parent request stream fails deterministically. No prompt
repair, retry-until-success, result normalization, model change, or tuning is
allowed.

## Interpretation boundary

A 3/3 pass demonstrates only that this bounded runtime intervention repaired
the observed post-success duplicate-delegation failure on these three frozen
cases while the external enforcement remained active. It does not establish
general Hermes reliability, model superiority, broader delegation quality, or
readiness for unrestricted autonomy. A pass supports recommending the next M0
evidence gate, not executing it in this run. A failure is preserved and used
to define the smallest next experiment; this study is never rerun to obtain a
pass.

## Evidence destination

`experiments/results/m0-5b-delegation-retirement-2026-10-05`

After the freeze tag and GitHub preregistration exist:

```sh
python3 experiments/m0-5b-delegation-retirement/run_study.py \
  --output-dir experiments/results/m0-5b-delegation-retirement-2026-10-05
```
