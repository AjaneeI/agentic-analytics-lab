# Benchmark Repeatability

The next gate for Agentic Analytics Lab is to characterize how the unchanged
single-agent baseline behaves across repeated local runs before tuning prompts or
adding routing.

This layer is intentionally descriptive. It does not change the agent, prompt,
question set, evaluator, ClickHouse tool, or scorer.

## Preflight the local benchmark environment

The ClickHouse tool reads `CLICKHOUSE_URL`, `CLICKHOUSE_USER`, and
`CLICKHOUSE_PASSWORD` from the process environment. It does not automatically
load values from `.env`.

If those variables are stored in a local, git-ignored `.env`, export them into
the current shell before running the benchmark:

```bash
set -a
source .env
set +a
```

Then verify authenticated access to the frozen benchmark table:

```bash
python3 -m src.tools.clickhouse_readonly \
  "SELECT count() AS n FROM agentic_analytics.delivery_work_items"
```

The preflight should return `500`. Treat authentication failures or an unexpected
row count as an environment/setup failure, not model-performance evidence. Do not
start the repeatability pass until this preflight succeeds.

## Run the frozen benchmark repeatedly

Keep the local configuration fixed and save each raw JSON result separately.

Example:

```bash
python3 scripts/run_single_agent_eval.py
cp experiments/results/single_agent_qwen2.5_7b.json \
  experiments/results/single_agent_qwen2.5_7b_run1.json

python3 scripts/run_single_agent_eval.py
cp experiments/results/single_agent_qwen2.5_7b.json \
  experiments/results/single_agent_qwen2.5_7b_run2.json

python3 scripts/run_single_agent_eval.py
cp experiments/results/single_agent_qwen2.5_7b.json \
  experiments/results/single_agent_qwen2.5_7b_run3.json
```

Raw benchmark JSON remains ignored by git.

## Summarize repeatability

```bash
python3 scripts/summarize_repeatability.py \
  experiments/results/single_agent_qwen2.5_7b_run1.json \
  experiments/results/single_agent_qwen2.5_7b_run2.json \
  experiments/results/single_agent_qwen2.5_7b_run3.json
```

The default output is:

```text
docs/generated/single-agent-repeatability-summary.md
```

The summary includes:

- per-run execution, correctness, and task-success counts
- tool calls, model calls, tokens, and latency
- mean/range/stdev for observed task-success rate
- per-question recurrence across runs
- recurring failure-type counts
- a compatibility gate that rejects mismatched benchmark metadata or case order

## Comparison integrity

The repeatability summary requires matching:

- benchmark schema version
- architecture
- model
- provider
- dataset
- frozen question-set path
- question IDs and order

Fields that should vary between runs, such as run timestamp and measured latency,
are not part of the compatibility signature.

Do not tune Q3 or Q5 merely to improve the score before this repeatability pass.
If their failure behavior changes across unchanged runs, record that as evidence.

## Interpretation

A small repeatability pass can reveal whether failures appear stable or variable,
but it is not a statistical-significance claim. The first purpose is to avoid
building a routed architecture around a one-off failure pattern.

Only after repeatability is characterized should the project implement the
smallest routed/control-plane prototype and compare it under matched conditions.
