# Architecture

Agentic Analytics Lab is designed around a simple engineering rule:

> Add architectural complexity only when measured evidence shows that it earns
> its cost, latency, maintenance burden, or reliability benefit.

The project therefore separates three things that are often blurred together in
agent demos:

1. the **execution architecture** that answers a question
2. the **evaluation architecture** that decides whether the answer was good
3. the **experiment architecture** that determines which evidence must exist
   before the next design decision is valid

See the
[Experiment Dependency Graph](docs/experiment-dependency-graph.md)
for the third layer.

## Workshop origin

The project began by reproducing the ClickHouse Agentic Data Stack workshop:

```text
User
  ↓
LibreChat
  ↓
Claude
  ↓
ClickHouse MCP
  ↓
ClickHouse Local
  ↓
Tool result
  ↓
Final answer

Langfuse records model calls, tool calls, latency, tokens, and cost.
```

That environment was the starting point, not the final portfolio architecture.

The current repository extends the workshop into an original evaluation system
with a Python execution path, a frozen benchmark, deterministic scoring,
dataset-scoped tool access, CI, routing experiments, validation, telemetry, and
bounded evaluation research.

## Current single-agent baseline

```text
Frozen benchmark question
        │
        ▼
   SingleAgent
        │
        ▼
 qwen2.5:7b
        │
        ▼
query_clickhouse
        │
        ▼
dataset-scoped read-only ClickHouse
        │
        ▼
evidence-backed answer
        │
        ▼
deterministic evaluator
        │
        ├── task correctness
        ├── factual consistency
        ├── tool grounding
        ├── model/tool-call accounting
        └── latency/token evidence
```

The baseline matters because routed or specialist designs need a stable
comparison target. Without a baseline, extra orchestration can look impressive
without proving that it improves the system.

## Implemented routed experiment

The first routed architecture is deliberately narrower than a general-purpose
multi-agent system.

```text
Frozen benchmark question
        +
frozen routing metadata
        │
        ▼
deterministic control plane
        │
        ├───────────────┐
        ▼               ▼
deterministic        local worker
handler              qwen2.5:7b
        │               │
        └───────┬───────┘
                ▼
dataset-scoped read-only ClickHouse
                │
                ▼
deterministic validation
                │
                ▼
route + execution telemetry
                │
                ▼
existing benchmark scorer
```

The implemented comparison architecture is
`oracle_metadata_routed_v0`.

It uses frozen benchmark metadata to isolate the value of execution-layer
routing. It does **not** claim to solve natural-language route inference.

That boundary is important. A router should not receive credit for a capability
that was supplied by the benchmark contract.

## Control-plane responsibilities

The control plane is designed as a measurable subsystem rather than a lead agent
with unconstrained authority.

Its responsibilities include:

- selecting the cheapest adequate execution path from allowed routes
- invoking deterministic handlers when a task does not require open-ended model
  reasoning
- reusing the existing local worker when model reasoning is appropriate
- keeping validation outside the worker
- emitting machine-readable route reasons
- recording route, validation, escalation, latency, cost, and tool evidence
- failing closed on unsupported or invalid routes

The control plane does not authorize new permissions.

Routing cannot weaken the ClickHouse security boundary, change credentials, or
expand the dataset scope.

## Deterministic analytics handlers

Several frozen benchmark semantics can be answered by fixed analytical
operations rather than additional model reasoning.

The deterministic handler layer is intentionally constrained:

```text
approved handler
      │
      ▼
fixed analytical operation
      │
      ▼
query_clickhouse()
      │
      ▼
existing SQL validation + resource limits
      │
      ▼
read-only dataset evidence
```

Handlers do not receive arbitrary database authority. They reuse the existing
tool boundary.

This makes routing an execution optimization rather than a permission system.

## Validation and escalation

The worker cannot declare itself successful.

Validation can produce explicit outcomes such as:

```text
accept
retry
escalate
fail closed
```

The architecture records the reason for the disposition so recovery behavior
can be measured rather than hidden inside an agent loop.

Automatic stronger-worker escalation is intentionally bounded. The project
first measures how often escalation would be needed and why.

## Evaluation architecture

The deterministic scorer remains the benchmark source of truth.

A separate bounded ASSERT experiment is evaluating whether behavioral
requirements and trace-aware judging add useful diagnostic or regression
evidence beyond that scorer.

```text
preserved benchmark evidence
        │
        ├───────────────┐
        ▼               ▼
deterministic        ASSERT behavioral
scorer               evaluation
        │               │
        └───────┬───────┘
                ▼
manual comparison
                │
                ▼
agreement / disagreement /
diagnostic-value analysis
```

ASSERT is therefore an additional evaluation lens, not a replacement for the
deterministic benchmark contract.

The experiment can produce a useful negative result. Adoption is not the
assumed outcome.

## Experiment architecture

The repository also treats experiment scheduling as an engineering problem.

Independent work can run concurrently, but evidence-changing work remains
serialized behind explicit gates.

The full dependency model is documented in
[docs/experiment-dependency-graph.md](docs/experiment-dependency-graph.md).

The core operating rule is:

> **Parallelize independent branches. Serialize evidence-changing merges.**

This lets the project increase engineering throughput without making benchmark
results harder to reproduce or attribute.

## Security boundary

The ClickHouse tool remains dataset-scoped and read-only regardless of route.

The boundary rejects or constrains:

- mutating or administrative SQL
- multiple statements
- access to physical tables outside
  `agentic_analytics.delivery_work_items`
- joins to out-of-scope tables
- table functions
- broad metadata discovery outside the allowed dataset
- unsafe non-loopback plain-HTTP transport
- known blocker-rate semantic inversions
- excessive query resource use

Security enforcement stays deterministic and downstream of routing.

## Evidence boundaries

Architecture claims are valid only within the environment that produced them.

Matched comparisons should preserve:

- benchmark questions and expected values
- dataset and seed
- scorer semantics
- model and prompt contract
- tool behavior and permissions
- run count and methodology
- execution environment when latency or cost is compared

Do not compare hardware-sensitive latency across mismatched environments and
present the result as an architecture effect.

## Design principles

- Start with the simplest measurable system.
- Freeze the comparison contract before changing architecture.
- Prefer deterministic operations for deterministic tasks.
- Keep authorization and safety boundaries outside model judgment.
- Let validators, not workers, determine success.
- Record enough telemetry to explain route and failure behavior.
- Separate execution-quality experiments from router-quality experiments.
- Treat observability and tracing as evidence, not decoration.
- Parallelize work according to dependencies, not according to available agent
  count.
- Adopt new evaluation or orchestration layers only when evidence justifies
  their maintenance cost.
- Preserve negative results when they reduce uncertainty.
- Prefer synthetic or public data for the publishable portfolio system.

## Future architecture

A broader natural-language router, stronger-worker escalation, or specialist
agent architecture remains possible, but none is the default next step.

A future system might eventually include:

```text
request
  ↓
deterministic feature extraction
  ↓
router
  ├── deterministic operation
  ├── local reasoning worker
  └── bounded escalation
  ↓
validator
  ↓
telemetry + evidence
```

Specialist or multi-agent orchestration should be added only after a narrower
design fails a measurable requirement that specialization can plausibly solve.

That constraint is part of the portfolio thesis: the goal is not to maximize
the number of agents. The goal is to build the **smallest system that produces
reliable, explainable, economically defensible results**.
