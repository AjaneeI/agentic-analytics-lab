# Test Suite Proof — 2026-09-17

Command:

```bash
python3 -m unittest discover -s tests -v
```

Result after the baseline-evaluation integrity fixes:

```text
Ran 32 tests in 0.014s

OK
```

The added coverage verifies that:

- a model answer is not marked correct merely because execution completed;
- numeric/categorical ground truth is checked deterministically;
- ranking order is checked for the ranking case;
- the causality case uses a deterministic epistemic-behavior check rather than an LLM judge;
- ClickHouse result rows are retained as evidence for benchmark scoring;
- percentage evidence is matched consistently when ClickHouse returns a canonical rate fraction;
- model-call and tool-call attempts are counted;
- Ollama `prompt_eval_count`, `eval_count`, and `total_duration` metadata are captured when present.

This proof covers unit behavior. The fresh end-to-end Qwen + ClickHouse benchmark is summarized in `docs/single-agent-benchmark-status-2026-09-17.md`.
