# Project Contract

## Project
Agentic Analytics Lab

## Purpose
Build and evaluate applied-AI analytics architectures to answer a bounded question:

> When does a routed or specialist-agent design outperform a strong single-agent baseline enough to justify the added tool calls, latency, model cost, maintenance, and operational complexity?

The project treats agentic analytics as an engineering system to be measured, not a demo to be embellished.

## Scope
In scope:
- single-agent analytics baseline;
- oracle-metadata routed execution;
- natural-language routing evaluation;
- deterministic evaluation where ground truth exists;
- read-only, dataset-scoped ClickHouse tooling;
- failure attribution, provenance, observability, repeatability, efficiency, and system-benchmark work;
- evidence-backed comparison of added orchestration against simpler baselines.

Out of scope unless explicitly approved:
- production deployment;
- unrestricted database access;
- unsupported real-world business conclusions from the synthetic dataset;
- replacing deterministic benchmark checks with subjective LLM judging;
- changing the frozen benchmark merely to improve results;
- architecture expansion without a measurable justification.

## Canonical evidence
GitHub is the technical source of truth for code, tests, commits, PRs, workflow runs, and stored project evidence.

Key repository evidence surfaces include:
- `README.md` for public claim boundaries;
- `ARCHITECTURE.md` for current architecture;
- `evals/` for evaluation contracts and fixtures;
- `experiments/` for experiment records and reviewed results;
- `.github/workflows/` for automated verification;
- `docs/` for benchmark, provenance, routing, and project-health documentation.

## Current architecture questions
1. What can the simplest credible single-agent worker do?
2. If the correct route is already known, does specialized execution improve outcomes enough to justify complexity?
3. Can a router infer the correct route from natural language?
4. Under realistic heterogeneous tasks, when does a more complex system earn its complexity?

These questions must remain separable so routing error, worker error, tool error, and evaluation error do not collapse into one score.

## Success criteria
The project is successful when it can make bounded, reproducible claims about:
- task correctness;
- tool/evidence grounding;
- routing behavior;
- failure stages;
- latency and usage;
- tool/model call overhead;
- repeatability;
- operational complexity;
- when added orchestration is and is not justified.

## Definition of done
There is no single permanent "done" state for the lab. A project phase is done only when:
- its implementation is complete;
- the relevant deterministic checks pass;
- evidence artifacts are preserved;
- claim boundaries are documented;
- the result can be reproduced or independently inspected;
- the next architectural decision is supported by evidence rather than intuition.

## Design principles
- Earn complexity with evidence.
- Keep a strong baseline.
- Separate routing inference from routed execution.
- Prefer deterministic evaluation where possible.
- Preserve least-privilege tool boundaries.
- Keep failures attributable.
- Keep public claims narrower than the evidence, never broader.
- Treat increased throughput as useful only when validated goodput and evidence quality are preserved.
