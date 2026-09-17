# Single-Agent Benchmark Status — 2026-09-17

## Current baseline state

The current `main` branch has the stabilized single-agent evaluation layer integrated on top of the hardened ClickHouse tool boundary.

Current automated evidence:

- 42 unit tests pass on Python 3.11 and Python 3.12.
- The evaluator separates execution success from answer correctness and task success.
- Deterministic scoring checks expected values, factual consistency, and tool grounding without an LLM judge.
- Tool evidence rows, model-call counts, tool-call attempts, token counts, and Ollama timing metadata are captured for benchmark analysis.
- The ClickHouse tool is restricted to `agentic_analytics.delivery_work_items`, rejects table functions and out-of-scope tables, requires HTTPS for non-loopback connections, and applies query resource caps.
- CodeQL runs the Python `security-extended` query suite.

The routed-agent architecture is still intentionally unimplemented.

## Historical local benchmark

A local Qwen/ClickHouse run was completed earlier on September 17, 2026 using `qwen2.5:7b`, the seed-42 synthetic dataset, and the corrected evaluator.

That run produced:

| Metric | Historical result |
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

Case-level outcome:

| Case | Historical outcome | Note |
|---|---|---|
| Q1 | pass | Data blocker rate was grounded in one query. |
| Q2 | pass | AI had the expected average actual-to-planned effort ratio. |
| Q3 | fail | The model described intended queries but made no tool call. |
| Q4 | pass | The four-team blocker-rate ranking matched ground truth. |
| Q5 | fail | The answer substituted raw hour overage for average effort ratio. |
| Q6 | pass | The answer avoided a causal claim and requested stronger evidence/design. |

## Important provenance note

The historical 4/6 task-success result is **not the current post-hardening benchmark**.

After that run, the model-facing ClickHouse contract was tightened to explicitly restrict the tool to the approved dataset and reject other tables and table functions. Security controls and evaluation instrumentation were also integrated onto `main`. Because the prompt/tool contract changed, the old run remains useful failure evidence but should not be used as the comparison anchor for the future routed-agent architecture.

## Next benchmark gate

Before changing the prompt or building routed agents:

1. Use the current `main` branch.
2. Regenerate and verify the seed-42 synthetic ground truth.
3. Use the frozen Q1-Q6 question set and current deterministic scorer.
4. Run `qwen2.5:7b` against the same local ClickHouse dataset with the current single-agent configuration.
5. Preserve the raw JSON locally and keep it ignored by default.
6. Repeat the unchanged benchmark to measure run-to-run consistency in correctness, grounding, tool calls, model calls, tokens, and latency.
7. Publish a reviewed summary, not unreviewed raw benchmark output.

Reproduction commands:

```bash
python3 scripts/generate_delivery_data.py
python3 scripts/verify_ground_truth.py
python3 -m unittest discover -s tests -v
python3 scripts/run_single_agent_eval.py
```

The benchmark command requires the local runtime with ClickHouse loaded with the synthetic dataset and Ollama serving `qwen2.5:7b`.

## Comparison integrity

The future routed-agent comparison must reuse the same dataset seed, Q1-Q6 evaluation set, expected-answer contract, read-only ClickHouse tool, semantic definitions, scorer, and measurement fields. If a shared component changes, record a benchmark-version change and apply it to both architectures before comparing results.
