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

## Shared analytical boundary

All analytical execution paths use the same constrained data boundary:

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
