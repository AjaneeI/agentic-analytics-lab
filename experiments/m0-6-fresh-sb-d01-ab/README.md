# M0.6 Fresh Hermes-vs-Direct SB-D01 A/B

Status: preregistration design. No M0.6 Qwen or Hermes invocation is permitted
until this directory is committed, tagged, pushed, and recorded in a new GitHub
successor issue.

## Evidence lineage

This is a fresh successor experiment from exact M0.5B evidence head
`655e5891398e1b8d2be2a3eea13df9251a90b232`. Historical results in issues
#73, #82, #84, #85, #86 and draft PR #83 remain unchanged.

M0.5 Study A passed 4/4. Original M0.5 Study B passed 2/3. M0.5B passed 3/3
after retiring `delegate_task` from a one-shot parent's model-visible tools
following its first successful synchronous child. M0.6 carries only that
bounded intervention into the existing real SB-D01 comparison.

## Research question

Can the repaired Hermes orchestration path complete the real frozen bounded
SB-D01 workflow, and does it provide useful bounded orchestration or reliability
value relative to the direct local path?

This one comparison cannot establish general Hermes superiority, general
reliability, unrestricted autonomy readiness, or performance on other tasks.

## Frozen task and contracts

Task:

> Identify the highest blocker-rate team and interpret it using the KPI definition without claiming causality.

- allowed evidence tools: `query_clickhouse`, `retrieve_policy`;
- response: existing `SystemBenchmarkResponse`;
- scorer: existing deterministic `score_response` with `REF-D01`;
- model: `hermes-local:qwen3.5-9b`, Q4_K_M;
- context: 65,536;
- temperature: 0;
- treatment order: direct, then Hermes;
- retry policy: one attempt per treatment, zero retries;
- incremental paid spend: $0.

Treatment A is the existing repository `BoundedLocalExecutor` with the frozen
task, worker prompt, evidence tools, six-step limit, model, and scorer. Hermes
is absent.

Treatment B is the existing isolated `localbenchmark` Hermes path. The parent
must make exactly one valid delegation containing one child, may not perform
evidence work, may not launch concurrently, and may not retry. Only the child
may use the two evidence tools. After a successful synchronous child, the
frozen M0.5B runtime intervention must remove `delegate_task` from the next
parent request's tool array. The unchanged plugin remains the hard one-worker
backstop.

## Deterministic acceptance

Treatment A is accepted only when the existing scorer accepts its unedited raw
response and observed tool evidence.

Treatment B is accepted only when the existing scorer accepts its unedited raw
response and the observed orchestration satisfies all of the following:

- exactly one valid delegation attempt;
- exactly one successful child;
- no parent evidence-tool calls;
- no enforcement intervention;
- the first parent request exposes `delegate_task`;
- the successful child returns;
- the subsequent parent request omits `delegate_task`;
- no second worker launches;
- retries remain zero and paid spend remains $0.

If a successful child is never reached, post-success retirement is recorded as
`not_reached`; it is not inferred or manufactured. Eligible responses are
scored independently even when the overall orchestration contract fails.

## Evidence and decision

Raw direct model traffic, Hermes request dumps, tool events, child evidence,
stdout, stderr, usage, process state, timing, scores, comparison, pre/postflight
checks, and a recursive SHA-256 index are preserved under
`experiments/results/m0-6-fresh-sb-d01-ab-2026-10-06`.

M1 readiness does not require Hermes to beat direct execution on latency. It
does require a valid deterministically accepted result, exact one-child bounded
orchestration, observed post-success retirement, zero enforcement intervention,
zero parent evidence work, zero retries, and $0 incremental spend. A pass
supports only a constrained M1 Personal Ops design recommendation; M1 is not
implemented in this run. A failure is preserved and determines the smallest
next experiment without tuning or rerunning M0.6.

After the freeze tag and GitHub preregistration exist, execute once:

```sh
python3 experiments/m0-6-fresh-sb-d01-ab/run_benchmark.py \
  --output-dir experiments/results/m0-6-fresh-sb-d01-ab-2026-10-06
```
