# Agentic Analytics Lab

[![Python tests](https://github.com/AjaneeI/agentic-analytics-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/AjaneeI/agentic-analytics-lab/actions/workflows/tests.yml)
[![CodeQL](https://github.com/AjaneeI/agentic-analytics-lab/actions/workflows/codeql.yml/badge.svg)](https://github.com/AjaneeI/agentic-analytics-lab/actions/workflows/codeql.yml)

Agentic Analytics Lab is an applied AI engineering work sample that tests a practical architecture question:

> **When does routing or agentic control improve an analytics workflow enough to justify the added complexity, latency, failure surface, and maintenance?**

The project uses a synthetic delivery-operations dataset so architecture decisions can be evaluated against frozen ground truth instead of judged from a convincing demo.

[Live case study](https://ajaneeigharo.com/work/agentic-analytics-lab) · [Accepted results](docs/portfolio-results.md) · [Architecture](ARCHITECTURE.md) · [Reproducibility](docs/REPRODUCIBILITY.md)

## 90-second read

| What an evaluator should know | Evidence |
| --- | --- |
| **Research question** | Compare a strong single-agent baseline with bounded routing strategies and require complexity to earn its place through measured outcomes. |
| **Baseline** | A Python analytics agent using `qwen2.5:7b` via Ollama and a dataset-scoped read-only ClickHouse tool. |
| **Benchmark** | Frozen Q1-Q6 cases on deterministic seed-42 synthetic data, scored with deterministic correctness, grounding, factual-consistency, and epistemic checks. |
| **Accepted baseline result** | 4/6 task success in each of three runs: 66.7% mean with 0.0 percentage-point run-to-run task-success variance. |
| **Bounded routed result** | 5/6, 6/6, and 6/6 task success using oracle benchmark metadata to choose the execution path. This is an execution-layer experiment, not a natural-language routing claim. |
| **What I built** | The Python agent baseline, hardened ClickHouse boundary, deterministic evaluation and repeatability harness, benchmark provenance and diagnostics, typed control plane, validation/telemetry, deterministic handlers, and separate natural-language routing evaluation lane. |
| **Enterprise relevance** | Least-privilege tool use, measurable launch criteria, failure diagnosis, auditability, cost/latency tradeoffs, escalation boundaries, and evidence-based architecture decisions. |
| **Current frontier** | System Benchmark v1 is broadening the evaluation beyond six analytics cases before stronger end-to-end routing claims are made. |

## Accepted evidence

![Accepted benchmark comparison](docs/portfolio/benchmark-comparison.svg)

| Measure | Single-agent baseline | Oracle-metadata routed |
| --- | ---: | ---: |
| Three task-success runs | 4/6, 4/6, 4/6 | 5/6, 6/6, 6/6 |
| Mean task success | 66.7% | 94.4% |
| Tool calls per run | 5 | 5 |
| Model calls per run | 11 | 1 |
| Mean end-to-end latency | 217.0 s | 33.9 s |

Evidence links and claim boundaries are documented in [Portfolio Results](docs/portfolio-results.md).

The routed condition receives frozen case metadata that identifies route-relevant facts. It therefore tests **execution value when the route is known**. It does not establish reliable free-text routing, a general multi-agent advantage, or production performance.

## Why test agentic complexity?

Agentic architecture is not the goal of this project. Reliable work is.

A single agent is easier to understand and operate. Routing adds components, decision logic, new failure modes, and more code to maintain. The project advances complexity only when a controlled experiment produces enough value to justify those costs.

The current evidence ladder is:

1. **Single-agent baseline:** accepted comparison anchor.
2. **Oracle-metadata routed execution:** accepted bounded experiment.
3. **Natural-language route inference:** implemented as a separate development regression lane so route-classification error is not confused with worker error.
4. **System Benchmark v1:** active next evaluation layer with heterogeneous task families, held-out cases, clarification, unsupported-source handling, and human handoff boundaries.

The v1 design intentionally does **not** add specialist model agents. A simpler architecture is allowed to win.

## Architecture

![Agentic Analytics Lab architecture overview](docs/portfolio/architecture-overview.svg)

The repository separates execution, safety, and evaluation rather than hiding them inside one orchestration framework.

- **Single-agent path:** model → read-only evidence tool → evidence-backed answer.
- **Routed path:** typed control plane → deterministic, local, or escalation disposition → validation → telemetry.
- **Safety boundary:** dataset scope, read-only SQL validation, table-function rejection, transport safeguards, query resource caps, and semantic checks for known metric hazards.
- **Evaluation boundary:** frozen cases, deterministic scoring, provenance fingerprints, repeatability checks, and observable failure-stage diagnostics.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the component-level design and claim boundaries.

## What I personally built

The project began after a ClickHouse Agentic Data Stack workshop, but the portfolio work is the engineering layer built around and beyond that workshop reproduction.

My original project work includes:

- a provider-agnostic Python single-agent loop and Ollama adapter;
- a ClickHouse query tool constrained to `agentic_analytics.delivery_work_items`;
- statement, table-scope, transport, resource, and blocker-rate semantic guards;
- deterministic scoring that separates execution from task correctness, grounding, factual consistency, completeness, and epistemic discipline;
- a three-run repeatability harness with compatibility checks;
- benchmark provenance that fingerprints the code and files defining the evaluation contract;
- post-hoc failure diagnostics based only on observable run evidence;
- a typed routing control plane with deterministic, local, and escalation routes;
- deterministic handlers, validation outcomes, route telemetry, and an oracle-metadata comparison adapter;
- a separate free-text routing regression lane so route inference can be measured independently;
- GitHub Actions evidence lanes, Python 3.11/3.12 CI, and CodeQL security analysis.

The upstream workshop tools are credited below. Reproducing LibreChat, ClickHouse MCP, Langfuse, and the original workshop stack is not presented as original work.

## How success is measured

A benchmark case is not successful just because the model produced text.

The evaluation layer records and checks:

- execution success
- task correctness
- completeness
- tool grounding
- factual consistency with captured evidence rows
- epistemic discipline
- model calls
- tool-call attempts and completed calls
- input and output tokens when reported by the local runtime
- end-to-end latency
- failure behavior

The architecture decision uses these measurements together. A quality improvement that requires substantially more operational complexity is not automatically a win.

## Enterprise AI relevance

| Lab mechanism | Enterprise analogue |
| --- | --- |
| Dataset-scoped read-only ClickHouse access | Least-privilege access to systems of record |
| Semantic metric guards | Business-rule and policy enforcement beyond syntax validation |
| Deterministic evals and regression cases | Pre-launch quality gates and change validation |
| Provenance fingerprints | Auditable evidence for which code, prompt, data, and scorer produced a result |
| Route telemetry and failure diagnostics | Operational debugging and incident analysis |
| Deterministic / local / escalate routes | Cost-aware automation plus human or higher-authority handoff |
| Token, call, and latency accounting | Reliability and unit-economics tradeoff analysis |
| Explicit non-claims | Governance discipline around what an experiment actually proves |

This is the part of the project most directly aligned with real enterprise Applied AI work: turning model behavior into a bounded system with measurable success criteria and operational constraints.

## Reproduce and inspect

Fast code-level verification:

    python -m compileall -q src
    python -m unittest discover -s tests -v

The CI workflow runs those checks on Python 3.11 and 3.12 without a Python package-install step.

The end-to-end benchmark additionally requires the model and data services used by the evidence lane. The canonical hosted workflow pins the environment, regenerates seed-42 data, creates a SELECT-only ClickHouse user, runs the unchanged benchmark three times, and preserves artifacts.

Start with [REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) and [Benchmark Repeatability](docs/benchmark-repeatability.md).

## Repository map

    .
    ├── src/
    │   ├── agents/       # single-agent loop and local model adapter
    │   ├── routing/      # control plane, handlers, validation, telemetry
    │   ├── evals/        # scoring, repeatability, provenance, diagnostics
    │   └── tools/        # hardened read-only ClickHouse boundary
    ├── evals/            # frozen benchmark and routing fixtures
    ├── scripts/          # data generation, benchmark runners, reporting
    ├── experiments/      # experiment history and reviewed-result boundary
    ├── docs/             # reproducibility, evidence, designs, portfolio results
    ├── tests/            # regression coverage across tool, agent, eval, routing
    └── .github/workflows # CI, CodeQL, benchmark evidence lanes

## Current project status

**Completed and reviewable**

- accepted three-run single-agent benchmark;
- matched oracle-metadata routed execution comparison;
- read-only and dataset-scope safety controls;
- deterministic evaluation, repeatability, provenance, and failure diagnostics;
- typed control-plane execution and route telemetry;
- free-text routing development regression lane.

**Active evaluation work**

System Benchmark v1 broadens the task distribution before the project makes stronger routing claims. The approved design includes structured analytics, policy retrieval, multi-source synthesis, ambiguity and clarification, causal discipline, unsupported-source handling, and human handoff.

Implementation is tracked in [issue #49](https://github.com/AjaneeI/agentic-analytics-lab/issues/49). The first contract-foundation implementation slice is [PR #55](https://github.com/AjaneeI/agentic-analytics-lab/pull/55).

## Limits and non-claims

- The current accepted comparison uses a synthetic dataset and only six frozen cases.
- Oracle-metadata routing does not measure natural-language route inference.
- The free-text routing development fixtures are regression evidence, not held-out generalization evidence.
- The repository is an engineering and evaluation lab, not a production SaaS service.
- Recorded latency is environment-dependent and should only be compared within matched execution conditions.
- Local Ollama inference has no per-request API charge, but local compute is not treated as literally free.
- No specialist-agent architecture is assumed to be better merely because it is more agentic.

## Upstream references

This repository is an original extension of concepts practiced in the ClickHouse workshop. It does not claim the upstream stack as original work.

- [ClickHouse Agentic Data Stack](https://github.com/ClickHouse/agentic-data-stack)
- [ClickHouse MCP server](https://github.com/ClickHouse/mcp-clickhouse)
- [ClickHouse Agent Skills](https://github.com/ClickHouse/agent-skills)
- [LibreChat](https://github.com/danny-avila/LibreChat)
- [Langfuse](https://github.com/langfuse/langfuse)
