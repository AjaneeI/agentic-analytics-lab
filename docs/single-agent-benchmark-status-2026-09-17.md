# Single-Agent Benchmark Status — 2026-09-17

## Scope

This checkpoint stabilizes the current Python + Ollama single-agent baseline. It does not implement or evaluate routed agents.

## Verified in this pass

- The frozen evaluation set contains six cases, Q1–Q6.
- The deterministic seed-42 dataset regenerates the checked-in team metrics exactly.
- The original 24-test suite reproduces cleanly.
- The evaluation harness previously treated any non-exception answer as `success=True`, so historical raw benchmark output cannot be interpreted as correctness without re-scoring.
- The benchmark harness now separates execution success from task correctness, checks required values against captured ClickHouse evidence, records model/tool-call counts, and captures Ollama token/timing metadata when supplied by the local API.
- The expanded unit suite passes with 29 tests.

## Ground-truth reference

| Case | Expected result |
|---|---|
| Q1 | Data, blocker rate 20.9% |
| Q2 | AI, average actual-to-planned effort ratio 1.16 |
| Q3 | Yes. Data has 29 blocked items and a 20.9% blocker rate. |
| Q4 | Data 20.9%, AI 15.0%, Product 14.7%, Platform 11.4% |
| Q5 | Platform, blocker rate 11.4% and average effort ratio 1.10 |
| Q6 | Do not claim causality; distinguish association from causation and request stronger evidence/design. |

The numeric values above are evaluation ground truth and are not included in the agent system prompt.

## Reproduction

```bash
python3 scripts/generate_delivery_data.py
python3 scripts/verify_ground_truth.py
python3 -m unittest discover -s tests
python3 scripts/run_single_agent_eval.py
```

The final command requires the current local runtime: ClickHouse loaded with the synthetic dataset and Ollama serving `qwen2.5:7b`.

## Publication status

A fresh Qwen/ClickHouse benchmark JSON was not produced in the environment used for this stabilization pass because that environment does not provide the local Ollama or ClickHouse runtimes. Existing raw JSON remains intentionally ignored because it predates the corrected correctness/evidence scoring and may contain stale latency or failure data.

Do not publish or compare a raw benchmark JSON until it is re-run through the corrected evaluator and manually reviewed for unsupported claims or anomalous tool behavior.

## Comparison integrity

The future routed-agent run should reuse the same dataset seed, six questions, expected-answer contract, read-only ClickHouse tool, semantic definitions, deterministic scorer, and measurement fields. Any later change to those shared components should be recorded as a benchmark-version change and applied to both architectures before comparison.
