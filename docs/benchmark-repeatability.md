# Benchmark Repeatability

The next gate for Agentic Analytics Lab is to characterize how the unchanged
single-agent baseline behaves across repeated local runs before tuning prompts or
adding routing.

This layer is intentionally descriptive. It does not change the agent, prompt,
question set, evaluator, ClickHouse tool, or scorer.

## Run the frozen benchmark repeatedly

Run the commands below from the repository root with the benchmark environment
already loaded into the shell.

Recommended one-command path (runs preflight first, executes the unchanged
single-agent benchmark three times, preserves run1/run2/run3 JSON, and then
builds the repeatability summary):

```bash
python3 scripts/run_repeatability_pass.py
```

If preserved run files already exist, the command fails instead of overwriting
them silently. Use the explicit override only when you intentionally want to
replace the preserved runs:

```bash
python3 scripts/run_repeatability_pass.py --force
```

### Manual fallback/reference

If you need to run the same workflow step-by-step, use:

```bash
python3 scripts/preflight_benchmark_env.py

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


## GitHub-hosted reproducibility lane

The repository also includes a manual GitHub Actions lane for reproducing the
same frozen three-run benchmark on a fresh Ubuntu runner:

```text
.github/workflows/repeatability-benchmark.yml
```

That workflow provisions an ephemeral pinned ClickHouse server, regenerates and
loads the existing seed-42 / 500-row synthetic dataset, installs pinned Ollama,
pulls `qwen2.5:7b`, runs the existing benchmark preflight, and then calls the
same `scripts/run_repeatability_pass.py` orchestration used locally.

Successful runs upload a GitHub Actions artifact containing the three raw JSON
runs, the repeatability Markdown summary, an environment manifest, and
non-secret diagnostics. Raw benchmark JSON remains uncommitted.

The workflow is intended primarily for `workflow_dispatch`. A pull-request
trigger scoped only to changes to the workflow file allows the workflow itself
to be validated when it is introduced or deliberately edited without running
the expensive benchmark on ordinary pull requests.

### Environment comparability

Treat GitHub-hosted and local Apple Silicon runs as separate execution
environments. Hardware-dependent latency should only be compared within the
same environment. Correctness, tool grounding, failure recurrence, model/tool
call counts, and other hardware-insensitive fields remain useful when the
benchmark configuration is otherwise matched.

The GitHub lane must not substitute another model if the default runner cannot
practically execute `qwen2.5:7b`. A measured resource blocker is evidence and
should be documented rather than hidden.

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
