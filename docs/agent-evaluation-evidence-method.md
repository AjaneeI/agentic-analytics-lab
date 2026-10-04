# Agent Evaluation Evidence Method

This note documents the evidence method used to extend Agentic Analytics Lab
without changing the frozen Q1-Q6 scorer or System Benchmark v1 task semantics.

## Design principle

The lab should earn added orchestration with evidence. That means architecture
comparisons need to preserve three distinctions:

1. task success vs. execution success;
2. final-answer quality vs. tool-use trajectory quality;
3. quality gains vs. latency, calls, tokens, and operational complexity.

The additions in this branch are deliberately model-free and use only observable
benchmark artifacts.

## 1. Repeated-run uncertainty

Repeated executions of the same benchmark task are not treated as new,
independent benchmark items.

For a matched baseline/candidate comparison:

1. validate that each architecture's repeated runs are internally compatible;
2. require matched benchmark metadata and identical task IDs/order across
   architectures;
3. compute each task's success rate across repeats;
4. compute the candidate-minus-baseline delta for each matched task;
5. bootstrap by resampling task-level deltas, not individual repeated
   observations.

This produces a descriptive 95% bootstrap interval over the frozen benchmark
task set while avoiding the strongest form of pseudoreplication.

The interval is intentionally bounded: it does **not** establish performance on
unseen tasks. A larger held-out System Benchmark set is still required for
generalization claims.

Relevant research:

- Robert E. Blackwell, Jon Barry, and Anthony G. Cohn, *Towards Reproducible
  LLM Evaluation: Quantifying Uncertainty in LLM Benchmark Scores*,
  arXiv:2410.03492.
- Evan Miller, *Adding Error Bars to Evals: A Statistical Approach to Language
  Model Evaluations*, arXiv:2411.00640.
- Jesús M. Fraile-Hernández and Anselmo Peñas, *On Measuring Large Language
  Models Performance with Inferential Statistics*, Information 16(9), 2025,
  DOI: 10.3390/info16090817.

With substantially more repeats and a larger task set, the lab should consider
mixed-effects or hierarchical models and reliability statistics rather than
claiming that three repeats are sufficient for precise inference.

## 2. Trajectory quality

Final-answer correctness can hide operationally different behavior. The
trajectory evaluator therefore records observable tool-use behavior separately:

- required tool selection;
- forbidden and unexpected tool use;
- dependency/order satisfaction;
- malformed tool-call records;
- repeated identical calls;
- calls above an explicit budget.

This follows the direction of trajectory-aware agent evaluation research such as
*TRAJECT-Bench: A Trajectory-Aware Benchmark for Evaluating Agentic Tool Use*
(arXiv:2510.04550), which evaluates tool-use behavior in addition to final
accuracy.

Trajectory quality is **not yet a gating System Benchmark v1 scoring dimension**.
The current task contracts do not encode dependency order or call budgets.
Adding those fields should be a separate contract change so evaluation rules
remain explicit.

## 3. Failure taxonomy

Raw scorer reason codes and diagnostic stages remain the source evidence. A
hierarchical taxonomy is added only as a reporting layer so failures can be
aggregated across benchmark lanes without discarding their original evidence.

Current top-level categories are:

- grounding;
- tool_use;
- reasoning;
- routing;
- authority;
- execution;
- recovery;
- unknown.

Unknown future reason codes remain explicitly unclassified rather than being
guessed into a category.

## 4. Complexity/value frontier

The project does not compute one opaque "agent score."

Architecture comparisons use Pareto dominance:

- quality/reliability metrics are maximized;
- latency, tool calls, model calls, tokens, cost, and other declared burden
  metrics are minimized.

An architecture is dominated only if another observed architecture is at least
as good on every declared metric and strictly better on at least one. Tradeoffs
remain visible on the frontier.

This preserves the research question: added agentic complexity is useful only
when it moves the quality-cost frontier outward.

## 5. Wolfram as an independent verifier

Wolfram is an optional independent verification path, not a runtime dependency
of the agent or benchmark.

The Python implementation remains dependency-light and reproducible in CI.
Reviewed comparison artifacts can be independently checked in Wolfram Language.

For example, given task-level candidate-minus-baseline deltas:

```wl
deltas = {0., 1/3, 2/3, 0., -1/3, 1/3};
Mean[deltas]

SeedRandom[42];
boot = Mean /@ RandomChoice[deltas, {10000, Length[deltas]}];
Quantile[boot, {0.025, 0.975}]
```

Wolfram can also independently verify derived rates, ranks, distributions,
confidence/credible intervals, and other numerical claims before benchmark
evidence is published.

The verifier is intentionally outside the agent execution path so the benchmark
does not validate itself with the same implementation that produced the answer.

## Current code

- `src/evals/statistical_evidence.py` — matched repeated-run comparison and
  task-level bootstrap;
- `src/evals/trajectory_quality.py` — model-free tool trajectory diagnostics;
- `src/evals/failure_taxonomy.py` — hierarchical reporting taxonomy;
- `src/evals/complexity_frontier.py` — Pareto frontier analysis;
- `scripts/compare_architecture_evidence.py` — artifact comparison CLI.

All four layers are designed to operate without paid model or API calls.
