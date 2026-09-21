# Benchmark Reporting Layer

The single-agent evaluator already writes structured JSON with correctness,
grounding, tool-use, model-call, token, and latency metrics.

This reporting layer converts that JSON into a deterministic Markdown summary
that can be reviewed before it is published as portfolio evidence.

## Usage

Run the benchmark in the local environment that has ClickHouse and Ollama:

```bash
python3 scripts/run_single_agent_eval.py
```

Then render a Markdown report:

```bash
python3 scripts/render_benchmark_report.py \
  experiments/results/single_agent_qwen2.5_7b.json
```

By default, the report is written to:

```text
docs/generated/single-agent-benchmark-report.md
```

You can override the destination:

```bash
python3 scripts/render_benchmark_report.py \
  experiments/results/single_agent_qwen2.5_7b.json \
  --output docs/generated/run-2026-09-17.md
```

## Publishing rule

Generating a report does not make a run a current benchmark.

Before publishing a report, verify that the run used the intended dataset,
frozen Q1-Q6 question set, deterministic evaluator, read-only ClickHouse tool,
metric definitions, and benchmark schema version. Review failed cases and any
unsupported claims manually.

The routed-agent architecture remains out of scope until the single-agent
baseline is stable and repeatable.
