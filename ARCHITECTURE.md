# Architecture

Agentic Analytics Lab keeps three evaluation questions separate so the project does not confuse execution improvements with routing accuracy.

## 1. Single-agent baseline

```text
User question
    |
    v
Single analytics agent
    |
    | decides whether a tool is needed
    v
Dataset-scoped read-only ClickHouse tool
    |
    v
Validated tool result
    |
    v
Final answer
```

The baseline is the simplest credible comparison anchor. One agent decides whether to query the dataset and returns an evidence-backed answer.

The baseline is evaluated for:

- task correctness
- execution success
- evidence and tool grounding
- latency
- tool-call count
- model usage and cost
- failure behavior

## 2. Oracle-metadata routed execution

```text
Frozen benchmark case
    |
    | category + requires_tool metadata
    v
Routed control plane
    |
    +----------------------+
    |                      |
    v                      v
Deterministic handler   Existing local worker
    |                      |
    +----------+-----------+
               |
               v
Dataset-scoped read-only ClickHouse tool
               |
               v
Validated answer
```

`oracle_metadata_routed_v0` tests whether specialized execution is useful when the correct route is already known from frozen benchmark metadata.

This experiment isolates execution-layer value from route-inference error. It does **not** show that the system can infer the correct route from natural-language requests.

The routed experiment is evaluated under matched benchmark conditions against the single-agent baseline.

## 3. Natural-language routing evaluation

```text
Free-text user prompt
    |
    v
Route classifier
    |
    v
Route decision
    |
    v
Evaluation against expected route
```

Natural-language routing is a separate evaluation lane.

It measures whether the system can infer the intended route from the user's words, including:

- route accuracy
- false-cheap routes
- unnecessary escalations
- route mismatches
- regression behavior across the development set

The current development set is a regression fixture. It is not evidence that routing will generalize to arbitrary real-world requests.

## 4. System Benchmark v1

This is a separate, staged evidence program, not a replacement for frozen Q1–Q6.
The source snapshot audited on October 5, 2026 includes:

| Layer | Current implementation | Boundary |
| --- | --- | --- |
| Task and response contracts | [contracts](src/evals/system_benchmark/contracts.py), [loader](src/evals/system_benchmark/loader.py), [references](src/evals/system_benchmark/references.py) | Seven development cases; no held-out performance claim |
| Policy evidence | [repository-local retrieval](src/tools/policy_retrieval.py), [versioned corpus](evals/system_benchmark/corpus/manifest.json) | Read-only, explicit source/version/section identities |
| Routing | [routing adapters and metrics](src/evals/system_benchmark/routing.py) | Oracle, free-text, and simple-heuristic decisions are evaluated separately from worker results |
| Worker capabilities | [worker adapters](src/evals/system_benchmark/workers.py) | Predicted tools are intersected with task allowlists; unsupported-source and handoff rules remain explicit |
| Execution and artifacts | [trial runner](src/evals/system_benchmark/runner.py), [bounded local executor](src/evals/system_benchmark/local_worker.py) | Recorded observations come from approved evidence tools, not a general filesystem/shell interface |
| Evaluation | [deterministic scoring](src/evals/system_benchmark/scoring.py), [trajectory checks](src/evals/trajectory_quality.py), [failure taxonomy](src/evals/failure_taxonomy.py) | Observable outputs, evidence, tools, and declared contracts; no hidden-reasoning or LLM judge |
| Comparison | [statistical evidence](src/evals/statistical_evidence.py), [Pareto frontier](src/evals/complexity_frontier.py) | Interpretation requires matched artifacts and declared metric directions; implementation alone proves no architecture advantage |

The implementation path is task/reference validation → independent route/capability
selection → bounded worker invocation → captured response/evidence → deterministic
scoring → provenance-bearing artifact bundle. Oracle routing supplies an upper-bound
control, not a deployable inference result.

The [development guide](evals/system_benchmark/README.md) describes the contracts.
[STATUS.md](STATUS.md) distinguishes merged work from the separate draft rehearsal
in [PR #72](https://github.com/AjaneeI/agentic-analytics-lab/pull/72) and records the
next permitted experiment. Do not attribute that draft's controls or test count to
`main`, or jump from implementation tests to held-out claims.

## Shared analytical boundary

Structured-data execution uses the constrained ClickHouse boundary below. System Benchmark document-capable workers additionally use the separate read-only policy retriever listed above:

```text
Agent or routed worker
        |
        v
Dataset-scoped read-only ClickHouse
        |
        +-- semantic metric guards
        +-- scope validation
        +-- transport safeguards
        +-- resource safeguards
```

This keeps architecture comparisons focused on agent behavior rather than giving one lane broader data access than another.

## Observability and evaluation

The project records the evidence needed to compare system behavior, including:

- model and tool activity
- routing decisions
- validation outcomes
- latency
- usage and cost signals
- task correctness
- unsupported claims
- failure modes

The benchmark and reporting layers are designed so public claims can be traced back to stored evaluation artifacts.

## Claim boundaries

The current architecture supports three distinct statements:

1. **Single-agent baseline:** the project has a measurable baseline with constrained tool access and deterministic evaluation where ground truth exists.
2. **Oracle-metadata routed execution:** the project can test specialized execution when the intended route is supplied by frozen benchmark metadata.
3. **Natural-language routing:** route inference is evaluated separately and should not be treated as proven generalization.

Keeping these lanes separate is intentional. The project only adds orchestration when measured evidence justifies the added complexity.

## Design principles

- Start with a strong single-agent baseline before adding orchestration.
- Measure routing inference separately from routed execution.
- Route only when specialization measurably improves outcome quality or efficiency.
- Keep tool access least-privilege and read-only by default.
- Use schema discovery and semantic guards before analytical queries.
- Capture correctness, latency, usage, tool count, and failure modes for each experiment.
- Prefer synthetic or public data for the publishable portfolio version.
