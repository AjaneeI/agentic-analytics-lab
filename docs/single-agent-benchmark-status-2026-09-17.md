# Single-Agent Benchmark Status — 2026-09-17

## Scope

This checkpoint stabilizes the current Python + Ollama single-agent baseline. It does not implement or evaluate routed agents.

## Verified in this pass

- The frozen evaluation set contains six cases, Q1–Q6.
- The deterministic seed-42 dataset regenerates the checked-in team metrics exactly.
- The original 24-test suite reproduces cleanly.
- The evaluation harness previously treated any non-exception answer as `success=True`, so historical raw benchmark output cannot be interpreted as correctness without re-scoring.
- The benchmark harness now separates execution success from task correctness, checks required values against captured ClickHouse evidence, records model/tool-call counts, saves reviewed local tool-evidence rows in the ignored raw JSON, and captures Ollama token/timing metadata when supplied by the local API.
- The expanded unit suite passes with 32 tests.

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

A fresh local Qwen/ClickHouse benchmark was produced on 2026-09-17 with `qwen2.5:7b`, the seed-42 synthetic dataset, ClickHouse reachable at `127.0.0.1:8123`, and the corrected evaluator. The ignored raw JSON is saved at `experiments/results/single_agent_qwen2.5_7b.json` for local review.

Summary:

| Metric | Result |
|---|---:|
| Questions | 6 |
| Execution successful | 6 |
| Task successful | 4 |
| Correct | 4 |
| Failed | 2 |
| Tool calls | 5 |
| Model calls | 11 |
| Input tokens | 8,038 |
| Output tokens | 824 |
| Total latency | 347.718629 seconds |

Case results:

| Case | Execution | Correct | Task success | Evidence | Notes |
|---|---|---|---|---|---|
| Q1 | yes | yes | yes | grounded single query | Data blocker rate returned as `AVG(blocked)` fraction and reported as 20.86%. |
| Q2 | yes | yes | yes | grounded single query | AI average actual-to-planned ratio reported as approximately 1.16. |
| Q3 | yes | no | no | ungrounded/inconsistent | The model stopped after describing intended queries and made no tool call. |
| Q4 | yes | yes | yes | grounded single query | Ranking was Data, AI, Product, Platform. |
| Q5 | yes | no | no | ungrounded/inconsistent | The model used two tool calls and substituted raw hour overage for average effort ratio. |
| Q6 | yes | yes | yes | no tool required | The model avoided a causal claim and requested stronger evidence/design. |

The current single-agent baseline is therefore frozen as `6/6` execution success and `4/6` task success. The two failures are model-answer failures, not ClickHouse or evaluator runtime failures.

Keep raw benchmark JSON ignored by default. Publish a reviewed summary or sanitized artifact rather than committing local raw result files.

## Comparison integrity

The future routed-agent run should reuse the same dataset seed, six questions, expected-answer contract, read-only ClickHouse tool, semantic definitions, deterministic scorer, and measurement fields. Any later change to those shared components should be recorded as a benchmark-version change and applied to both architectures before comparison.
