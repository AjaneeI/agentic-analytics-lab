# ASSERT bounded evaluation slice: Q3

**Status:** prepared, not executed  
**Date:** 2026-09-23  
**Parent:** GitHub issue #40

This slice turns the first-week ASSERT experiment into a reproducible, bounded target without changing the frozen Agentic Analytics benchmark.

## Why Q3

Q3 is a stable failure in the accepted GitHub-hosted single-agent baseline. Across three unchanged runs, the system failed the task each time. The observed signature was not a database or evaluator failure: the run performed extra model/tool work but still stopped short of the complete comparison required by the question.

That makes Q3 useful for asking a narrow question:

> Does a trace-aware behavioral requirement layer add diagnostic or regression evidence beyond the existing deterministic scorer?

## Frozen target

Question:

> Is the team with the most blocked items also the team with the highest blocker rate? Explain using the underlying values.

Expected benchmark evidence:

- answer: yes
- team: Data
- blocked items: 29
- blocker rate: 20.9%
- required tool use: yes
- maximum tool calls: 1

The machine-readable requirements for this slice live in `evals/assert_q3_requirements.json`.

## Requirements

The slice evaluates five behaviors:

1. The comparison is grounded in tool evidence.
2. The answer identifies Data with 29 blocked items.
3. The answer identifies Data with a 20.9% blocker rate.
4. The answer explicitly concludes that the same team leads both measures.
5. The explanation connects both values instead of stopping after only one side of the comparison.

These are framework-agnostic requirements. They should be mapped into ASSERT only after the official quickstart is running. This repository should not invent an ASSERT-specific contract.

## Execution protocol

1. Run the existing frozen Q3 path unchanged and retain the deterministic scorer result.
2. Run the official ASSERT quickstart separately and record setup friction.
3. Map the five requirements above into the smallest supported ASSERT representation.
4. Capture the ASSERT evaluation and any trace evidence without changing the benchmark prompt, data, model, scorer, or tool boundary.
5. Compare ASSERT evidence with the existing deterministic evidence.
6. Record disagreements explicitly. Do not resolve disagreements in favor of either system by default.
7. Repeat enough times to distinguish a stable signal from a one-off trace.
8. Stop the experiment if integration work begins to interfere with the matched routed-vs-single benchmark.

## Evidence to capture

For the bounded slice, record:

- deterministic task-success result
- requirement pass/fail results
- scoring agreement or disagreement
- trace information that materially explains the failure
- false-positive / false-negative review burden
- reproducibility across repeated runs
- integration complexity
- latency and cost overhead, if measurable
- whether the result looks suitable for CI regression use

## Decision boundary

This document is **not** evidence that ASSERT improves the lab. It only defines the test.

Continue to a fuller pilot only if the bounded slice produces evidence that is both reproducible and materially more useful than the existing deterministic evaluator. A clean negative result is a valid outcome.
