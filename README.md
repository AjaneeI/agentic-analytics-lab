# Agentic Analytics Lab

Agentic Analytics Lab is a portfolio project for testing when an AI analytics
agent should stay simple and when a routed or specialist-agent design is worth
the added cost, latency, and complexity.

The project started from the ClickHouse Agentic Data Stack workshop and extends
it into an original, measurable applied-AI system: a delivery-intelligence agent
that queries structured operational data, returns evidence-backed answers, and
records enough execution detail to compare design choices.

## Why This Project Exists

Agent demos often look convincing before they are measured. This project treats
the agent as an operational system that needs guardrails, evaluation criteria,
and observable behavior.

The central question is:

> When does a routed or multi-agent design outperform a single-agent design
> enough to justify extra tool calls, latency, model cost, and maintenance?

That question matters for practical AI adoption because organizations do not
only need impressive answers. They need systems that are correct, explainable,
safe to operate, and worth their complexity.

## Current Status

- Reproduced a workshop baseline with LibreChat, Claude, ClickHouse Local MCP,
  Docker Compose, and Langfuse tracing.
- Built a Python single-agent baseline that can query a synthetic delivery
  operations dataset through a read-only ClickHouse tool.
- Added semantic grounding for delivery metrics, including blocker-rate
  definitions and a low-latency blocker-rate SQL guard.
- Froze a six-question evaluation set with deterministic seed-42 ground truth.
- Stabilized the evaluation harness so execution success is no longer treated as
  answer correctness.
- Added deterministic answer/evidence scoring, model/tool-call accounting, and
  native Ollama token/timing capture.
- The routed-agent architecture is still planned and has not been implemented or
  benchmarked.

Current stabilization notes:

- [Single-agent benchmark status - 2026-09-17](docs/single-agent-benchmark-status-2026-09-17.md)
- [Test suite proof - 2026-09-17](docs/test-suite-proof-2026-09-17.md)

A fresh end-to-end Qwen + ClickHouse benchmark JSON still needs to be run in a
local environment that has both runtimes available. Pre-correction raw benchmark
JSON should not be interpreted as correctness evidence.

## What The Agent Can Answer

The current dataset models delivery work items with fields such as team,
priority, status, planned effort, actual effort, lateness, blockers, rework,
and customer impact.

Example analytical questions:

- Which team has the highest blocker rate?
- Which priorities are most likely to finish late?
- Which teams have the highest rework burden?
- Where do blockers and customer impact appear together?

The agent is expected to answer with database-backed evidence, not unsupported
generalizations.

## Design Principles

- Start with a trustworthy single-agent baseline before adding orchestration.
- Keep database access read-only by default.
- Treat SQL safety, metric semantics, and answer correctness as separate
  requirements.
- Prefer one correct query over multiple unnecessary tool calls.
- Capture task correctness, factual consistency, model/tool calls, latency,
  tokens, cost signals, and failure behavior.
- Add routed agents only when evaluation results justify the complexity.

## Architecture

Current controlled benchmark:

```text
Frozen evaluation question
  |
  v
Python single-agent baseline
  |
  v
Ollama qwen2.5:7b
  |
  v
Read-only ClickHouse tool
  |
  v
Synthetic delivery operations data
  |
  v
Captured query evidence + final answer
  |
  v
Deterministic evaluator
```

Planned comparison:

```text
User question
  |
  v
Router / lead agent
  |
  +--> Delivery analyst
  +--> Workstream specialist
  +--> Executive synthesizer
  |
  v
Same read-only tool layer and evaluator
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the fuller design notes and the
comparison invariants.

## Safety And Evaluation

The ClickHouse tool rejects:

- mutating or administrative SQL keywords
- multiple SQL statements
- attempts to label the complement of blocked work as `blocker_rate`

The frozen benchmark contains six cases covering retrieval, comparison,
reasoning, ranking, multi-metric analysis, and epistemic discipline. The
evaluator now distinguishes:

- execution success
- answer correctness
- factual consistency with captured ClickHouse rows
- tool grounding / evidence quality
- extra or repeated tool calls
- model-call count
- end-to-end latency
- Ollama input/output token counts when available
- failure type

The deterministic seed-42 ground truth can be checked without a model:

```bash
python3 scripts/generate_delivery_data.py
python3 scripts/verify_ground_truth.py
```

Run the unit test suite:

```bash
python3 -m unittest discover -s tests
```

Run the local single-agent benchmark after ClickHouse is loaded with the
synthetic dataset and Ollama is serving `qwen2.5:7b`:

```bash
python3 scripts/run_single_agent_eval.py
```

Raw JSON remains ignored by default. Review it before publishing or overriding
`.gitignore`.

Evidence screenshot:

![Docker service health screenshot](docs/screenshots/docker-service-health.png)

## Limitations

- The current dataset is synthetic, so findings are useful for evaluating agent
  behavior but should not be treated as real operational conclusions.
- The routed-agent design is planned but has not yet been evaluated against the
  single-agent baseline.
- A fresh end-to-end Qwen + ClickHouse benchmark has not yet been produced with
  the corrected evaluator. Historical raw output may be stale or use the older
  execution-only success semantics.
- Automatic unsupported-claim detection is intentionally conservative. A human
  review is still required before a benchmark artifact is published.
- Local benchmark JSON files are kept out of the public repository until they
  are reviewed and labeled as current benchmark results or historical failure
  cases.
- The project is not production-ready. It is a portfolio lab for testing tool
  safety, metric semantics, and agent-design tradeoffs.
- Ollama has no per-request API charge, but this benchmark does not estimate
  local hardware or electricity cost.
- Cost and latency claims should be refreshed after each model, prompt, or
  tool-layer change.

## Repository Map

```text
.
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
├── docs/
│   ├── evidence-plan.md
│   ├── publishing-plan.md
│   ├── screenshots/
│   ├── single-agent-benchmark-status-2026-09-17.md
│   ├── social-posting-kit.md
│   └── workshop-notes.md
├── evals/
│   ├── questions.json
│   └── rubric.md
├── experiments/
│   ├── experiment-log.md
│   ├── ground-truth/
│   └── results/
├── scripts/
├── sql/
├── src/
│   ├── agents/
│   ├── evals/
│   └── tools/
└── tests/
```

## Portfolio Signal

This project is evidence for applied AI operations and product-minded AI
implementation work:

- translating an AI workshop into an original evaluation project
- defining measurable success criteria before adding complexity
- building read-only tool access and semantic safety checks
- separating successful execution from correct, evidence-backed answers
- documenting failures and debugging decisions
- comparing AI architecture choices with latency, cost, and reliability in mind

It is intentionally framed as a learning-in-public portfolio project, not as a
production system.

## Upstream References

This repository is an original extension of concepts practiced in the ClickHouse
workshop. It does not claim the upstream stack as original work.

- ClickHouse Agentic Data Stack: https://github.com/ClickHouse/agentic-data-stack
- ClickHouse MCP server: https://github.com/ClickHouse/mcp-clickhouse
- ClickHouse Agent Skills: https://github.com/ClickHouse/agent-skills
- LibreChat: https://github.com/danny-avila/LibreChat
- Langfuse: https://github.com/langfuse/langfuse

## Next Steps

- Run a fresh Qwen + ClickHouse benchmark with the corrected evaluator and
  manually review all six cases before publishing the JSON.
- Keep the dataset, questions, answer contract, tool layer, metric definitions,
  evaluator, and measurement methodology fixed for the architecture comparison.
- Build the smallest routed-agent prototype only after that reviewed baseline is
  accepted as the comparison anchor.
- Publish only sanitized evidence and reviewed benchmark outputs.
